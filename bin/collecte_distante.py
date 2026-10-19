#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collecte documentaire distante — exécutée par GitHub Actions, jamais par le moteur.

Pourquoi ce script existe : l'espace de travail de développement ne peut pas
joindre les sites juridiques (seuls les registres de paquets et GitHub sont
ouverts). Les machines de GitHub Actions, elles, ont un accès Internet normal.
Ce script y télécharge les documents déclarés dans
`KNOWLEDGE/collecte/manifeste.json`, mesure leur intégrité, extrait leur texte
(calque texte, puis OCR français si la page est un scan) et ÉCRIT DES CONSTATS.

Ce qu'il NE fait PAS, volontairement :
  * il ne touche pas à la base du corpus (`corpus_juridique.sqlite3`) ;
  * il ne promeut aucune référence, ne crée aucune fiche ;
  * il ne décide pas qu'un texte est officiel : il recopie la catégorie
    déclarée dans le manifeste et ajoute ce qu'il observe (marques d'éditeur
    tiers, pages, polices, densité de texte).
L'intégration se fait ensuite, en local, par `bin/integrer_collecte.py`, avec les
garde-fous habituels (hôte officiel, couverture des articles, contaminants).

Dépendances : bibliothèque standard + outils poppler (pdfinfo, pdffonts,
pdftotext, pdftoppm) + tesseract (langue fra). Aucune clé, aucun service payant.

    python3 bin/collecte_distante.py                    # tout le manifeste
    python3 bin/collecte_distante.py --cle code_penal   # une entrée
    python3 bin/collecte_distante.py --forcer           # ignore les résultats existants
"""

import argparse
import concurrent.futures
import datetime
import hashlib
import html
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "KNOWLEDGE", "collecte")
MANIFESTE = os.path.join(DOSSIER, "manifeste.json")
DOSSIER_RESULTATS = os.path.join(DOSSIER, "resultats")
DOSSIER_TEXTES = os.path.join(DOSSIER, "textes")
# Les PDF ne sont pas versionnés sur la branche de travail : le workflow les
# pousse sur une branche d'archive séparée (corpus/archives-pdf).
DOSSIER_PDF = os.environ.get("COLLECTE_DOSSIER_PDF", os.path.join(DOSSIER, "pdf"))

AGENT_HTTP = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/124 Safari/537.36 MonRecoursCI-collecte-documentaire")
TAILLE_MAX = 95 * 1024 * 1024          # limite GitHub : 100 Mo par fichier
DENSITE_SCAN = 200                      # car./page en dessous : la page est traitée en OCR
PAGES_OCR_MAX = int(os.environ.get("COLLECTE_PAGES_OCR_MAX", "400"))
MARQUES_TIERCES = ("laws.africa", "creative commons", "faolex", "ivoire-juriste",
                   "lexterra", "droitci.info", "scribd", "loidici", "juricaf")


def journal(message):
    print(message, flush=True)


def maintenant():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def sha256(octets):
    return "sha256:" + hashlib.sha256(octets).hexdigest()


def telecharger(url, timeout=120, essais=3):
    """Renvoie (statut_http, type_contenu, url_finale, octets). Lève après `essais` échecs."""
    derniere = None
    for essai in range(essais):
        try:
            requete = urllib.request.Request(url, headers={
                "User-Agent": AGENT_HTTP, "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.5",
                "Accept-Language": "fr-FR,fr;q=0.9"})
            with urllib.request.urlopen(requete, timeout=timeout) as reponse:
                octets = reponse.read(TAILLE_MAX + 1)
                return (reponse.status, reponse.headers.get("Content-Type", ""),
                        reponse.geturl(), octets)
        except urllib.error.HTTPError as erreur:
            # Un 4xx est une réponse définitive : inutile d'insister.
            if 400 <= erreur.code < 500:
                return erreur.code, erreur.headers.get("Content-Type", ""), url, b""
            derniere = erreur
        except Exception as erreur:  # noqa: BLE001 — réseau : on consigne et on réessaie
            derniere = erreur
        time.sleep(3 * (essai + 1))
    raise RuntimeError("échec après %d essais : %s" % (essais, derniere))


def outil(*commande, entree=None, timeout=600):
    resultat = subprocess.run(commande, input=entree, capture_output=True, timeout=timeout)
    return resultat.returncode, resultat.stdout, resultat.stderr


def version_outils():
    versions = {}
    for nom, commande in (("pdftotext", ("pdftotext", "-v")), ("tesseract", ("tesseract", "--version")),
                          ("qpdf", ("qpdf", "--version"))):
        if not shutil.which(commande[0]):
            versions[nom] = None
            continue
        _, sortie, erreur = outil(*commande)
        texte = (sortie + erreur).decode("utf-8", "replace").strip().splitlines()
        versions[nom] = texte[0] if texte else "?"
    if shutil.which("tesseract"):
        _, sortie, _ = outil("tesseract", "--list-langs")
        versions["tesseract_langues"] = [l for l in sortie.decode().split()[1:] if l]
    return versions


def infos_pdf(chemin):
    infos = {}
    code, sortie, _ = outil("pdfinfo", chemin)
    if code == 0:
        for ligne in sortie.decode("utf-8", "replace").splitlines():
            if ":" in ligne:
                cle, valeur = ligne.split(":", 1)
                infos[cle.strip()] = valeur.strip()
    code, sortie, _ = outil("pdffonts", chemin)
    infos["polices"] = max(0, len(sortie.decode("utf-8", "replace").splitlines()) - 2) if code == 0 else None
    code, _, erreur = outil("qpdf", "--check", chemin)
    infos["qpdf_check"] = "ok" if code == 0 else ("avertissements" if code == 3 else "erreur")
    if code not in (0, 3):
        infos["qpdf_erreur"] = erreur.decode("utf-8", "replace")[-400:]
    return infos


def texte_page(chemin, numero):
    code, sortie, _ = outil("pdftotext", "-f", str(numero), "-l", str(numero), "-enc", "UTF-8",
                            chemin, "-")
    return sortie.decode("utf-8", "replace") if code == 0 else ""


def ocr_page(chemin, numero, dossier_tmp):
    """OCR d'une page : rendu 300 dpi en niveaux de gris, tesseract fra. Renvoie (texte, confiance)."""
    base = os.path.join(dossier_tmp, "p%04d" % numero)
    code, _, _ = outil("pdftoppm", "-f", str(numero), "-l", str(numero), "-r", "300", "-gray",
                       "-png", "-singlefile", chemin, base)
    image = base + ".png"
    if code != 0 or not os.path.isfile(image):
        return "", None
    code, sortie, _ = outil("tesseract", image, "-", "-l", "fra", "--psm", "3",
                                "-c", "tessedit_create_tsv=1", timeout=300)
    os.remove(image)
    if code != 0:
        return "", None
    lignes, confiances, cle_ligne, courant = [], [], None, []
    for rang, brut in enumerate(sortie.decode("utf-8", "replace").splitlines()):
        champs = brut.split("\t")
        if rang == 0 or len(champs) < 12:
            continue
        niveau, bloc, para, ligne, conf, mot = champs[0], champs[2], champs[3], champs[4], champs[10], champs[11]
        if niveau != "5":
            continue
        identifiant = (bloc, para, ligne)
        if identifiant != cle_ligne and courant:
            lignes.append(" ".join(courant))
            courant = []
        cle_ligne = identifiant
        if mot.strip():
            courant.append(mot)
            try:
                if float(conf) >= 0:
                    confiances.append(float(conf))
            except ValueError:
                pass
    if courant:
        lignes.append(" ".join(courant))
    confiance = round(sum(confiances) / len(confiances), 1) if confiances else None
    return "\n".join(lignes), confiance


def extraire(chemin, pages, cle):
    """Texte natif page par page ; OCR des pages sans texte. Renvoie un dict de constats."""
    natif, a_ocr = [], []
    for numero in range(1, pages + 1):
        texte = texte_page(chemin, numero)
        natif.append(texte)
        if len(texte.strip()) < DENSITE_SCAN:
            a_ocr.append(numero)
    constats = {"pages": pages, "caracteres_natifs": sum(len(t) for t in natif),
                "pages_sans_texte": len(a_ocr)}
    ocr = {}
    if a_ocr and shutil.which("tesseract"):
        if len(a_ocr) > PAGES_OCR_MAX:
            constats["ocr_tronque"] = "%d pages à reconnaître, limite %d" % (len(a_ocr), PAGES_OCR_MAX)
            a_ocr = a_ocr[:PAGES_OCR_MAX]
        dossier_tmp = os.path.join(os.environ.get("RUNNER_TEMP", "/tmp"), "ocr_" + cle)
        os.makedirs(dossier_tmp, exist_ok=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count() or 2) as executeur:
            futurs = {executeur.submit(ocr_page, chemin, n, dossier_tmp): n for n in a_ocr}
            for futur in concurrent.futures.as_completed(futurs):
                ocr[futurs[futur]] = futur.result()
        shutil.rmtree(dossier_tmp, ignore_errors=True)
    elif a_ocr:
        constats["ocr_impossible"] = "tesseract absent"

    # Fichier natif : les pages séparées par un saut de page, comme pypdf.
    os.makedirs(DOSSIER_TEXTES, exist_ok=True)
    chemin_natif = os.path.join(DOSSIER_TEXTES, cle + ".txt")
    with open(chemin_natif, "w", encoding="utf-8") as flux:
        flux.write("\n\f\n".join(natif))
    constats["fichier_texte"] = os.path.relpath(chemin_natif, RACINE)
    constats["sha256_texte"] = sha256(open(chemin_natif, "rb").read())
    if ocr:
        # Fichier mixte : texte natif quand il existe, OCR sinon, avec les
        # marqueurs « --- PAGE n --- » déjà reconnus et retirés par le parseur.
        morceaux, confiances = [], []
        for numero in range(1, pages + 1):
            if numero in ocr:
                texte, confiance = ocr[numero]
                morceaux.append("--- PAGE %d --- [OCR conf=%s]\n%s" % (numero, confiance, texte))
                if confiance is not None:
                    confiances.append(confiance)
            else:
                morceaux.append("--- PAGE %d ---\n%s" % (numero, natif[numero - 1]))
        chemin_ocr = os.path.join(DOSSIER_TEXTES, cle + ".ocr.txt")
        with open(chemin_ocr, "w", encoding="utf-8") as flux:
            flux.write("\n".join(morceaux))
        constats["fichier_ocr"] = os.path.relpath(chemin_ocr, RACINE)
        constats["sha256_ocr"] = sha256(open(chemin_ocr, "rb").read())
        constats["pages_ocr"] = len(ocr)
        constats["confiance_ocr_moyenne"] = (round(sum(confiances) / len(confiances), 1)
                                             if confiances else None)
        constats["pages_ocr_faibles"] = sorted(n for n, (_, c) in ocr.items() if c is None or c < 70)
    return constats


def liens_pdf(page_html, url_base, filtre):
    liens = set()
    for brut in re.findall(r"""href\s*=\s*["']([^"']+)["']""", page_html, re.I):
        lien = urllib.parse.urljoin(url_base, html.unescape(brut))
        if re.search(filtre, lien, re.I):
            liens.add(lien)
    return sorted(liens)


def traiter(source):
    cle = source["cle"]
    resultat = {"cle": cle, "url": source["url"], "date_recuperation": maintenant(),
                "categorie_source": source.get("categorie_source")}
    try:
        statut, type_contenu, url_finale, octets = telecharger(source["url"])
    except Exception as erreur:  # noqa: BLE001
        resultat.update(statut="ECHEC_RESEAU", erreur=str(erreur)[:300])
        return resultat
    resultat.update(http=statut, type_contenu=type_contenu, url_finale=url_finale, octets=len(octets))
    if statut != 200 or not octets:
        resultat["statut"] = "ECHEC_HTTP"
        return resultat

    if source.get("mode") == "decouverte":
        texte = octets.decode("utf-8", "replace")
        resultat["liens"] = liens_pdf(texte, url_finale, source.get("filtre_liens", r"\.pdf(\?|$)"))
        titre = re.search(r"<title>(.*?)</title>", texte, re.I | re.S)
        resultat["titre_page"] = html.unescape(titre.group(1)).strip()[:200] if titre else None
        resultat["statut"] = "DECOUVERTE"
        return resultat

    if len(octets) > TAILLE_MAX:
        resultat["statut"] = "TROP_VOLUMINEUX"
        return resultat
    if not octets.startswith(b"%PDF"):
        resultat["statut"] = "NON_PDF"
        resultat["debut"] = octets[:160].decode("utf-8", "replace")
        if b"<html" in octets[:2000].lower():
            resultat["liens"] = liens_pdf(octets.decode("utf-8", "replace"), url_finale,
                                          r"\.pdf(\?|$)|m=pdf")
        return resultat

    resultat["sha256"] = sha256(octets)
    os.makedirs(DOSSIER_PDF, exist_ok=True)
    chemin = os.path.join(DOSSIER_PDF, cle + ".pdf")
    with open(chemin, "wb") as flux:
        flux.write(octets)
    resultat["fichier_pdf"] = cle + ".pdf"
    infos = infos_pdf(chemin)
    resultat["pdf"] = {k: infos.get(k) for k in ("Pages", "Title", "Producer", "Creator",
                                                    "CreationDate", "ModDate", "PDF version",
                                                    "polices", "qpdf_check", "qpdf_erreur")
                       if infos.get(k) is not None}
    try:
        pages = int(infos.get("Pages") or 0)
    except ValueError:
        pages = 0
    if pages <= 0:
        resultat["statut"] = "PDF_ILLISIBLE"
        return resultat
    resultat["extraction"] = extraire(chemin, pages, cle)
    texte_complet = open(os.path.join(RACINE, resultat["extraction"]["fichier_texte"]),
                         encoding="utf-8").read()
    if resultat["extraction"].get("fichier_ocr"):
        texte_complet += open(os.path.join(RACINE, resultat["extraction"]["fichier_ocr"]),
                              encoding="utf-8").read()
    resultat["marques_tierces_observees"] = sorted(
        m for m in MARQUES_TIERCES if m in texte_complet.lower())
    resultat["statut"] = "TELECHARGE"
    return resultat


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--cle", action="append", help="ne traiter que ces entrées")
    analyseur.add_argument("--forcer", action="store_true", help="retraiter même si un résultat existe")
    arguments = analyseur.parse_args(argv)

    manifeste = json.load(open(MANIFESTE, encoding="utf-8"))
    os.makedirs(DOSSIER_RESULTATS, exist_ok=True)
    sources = manifeste["sources"]
    if arguments.cle:
        sources = [s for s in sources if s["cle"] in arguments.cle]
    cles = [s["cle"] for s in manifeste["sources"]]
    doublons = sorted({c for c in cles if cles.count(c) > 1})
    if doublons:
        raise SystemExit("clés en double dans le manifeste : %s" % doublons)

    synthese = {"execution": maintenant(), "outils": version_outils(), "traites": [], "ignores": []}
    for source in sources:
        chemin_resultat = os.path.join(DOSSIER_RESULTATS, source["cle"] + ".json")
        if os.path.isfile(chemin_resultat) and not arguments.forcer:
            precedent = json.load(open(chemin_resultat, encoding="utf-8"))
            if precedent.get("url") == source["url"] and precedent.get("statut") in (
                    "TELECHARGE", "DECOUVERTE"):
                synthese["ignores"].append(source["cle"])
                continue
        journal("== %s  %s" % (source["cle"], source["url"]))
        debut = time.time()
        resultat = traiter(source)
        resultat["duree_s"] = round(time.time() - debut, 1)
        journal("   -> %s %s" % (resultat.get("statut"), {k: resultat.get(k) for k in
                                                         ("http", "octets", "sha256")}))
        with open(chemin_resultat, "w", encoding="utf-8") as flux:
            json.dump(resultat, flux, ensure_ascii=False, indent=1, sort_keys=True)
        synthese["traites"].append({"cle": source["cle"], "statut": resultat.get("statut")})
    with open(os.path.join(DOSSIER, "derniere_execution.json"), "w", encoding="utf-8") as flux:
        json.dump(synthese, flux, ensure_ascii=False, indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
