#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Contrôle local des documents collectés par GitHub Actions, puis inventaire.

Étapes (chacune relançable, aucune ne supprime quoi que ce soit) :

    python3 bin/integrer_collecte.py pdf        # rapatrie les PDF de corpus/archives-pdf
    python3 bin/integrer_collecte.py controler  # contrôles + quarantaine + inventaire
    python3 bin/integrer_collecte.py recouper   # compare officiel / secondaire, article par article

Ce que « contrôler » vérifie pour chaque document téléchargé :
  * l'empreinte du PDF rapatrié est celle mesurée au téléchargement ;
  * le texte (calque ou OCR) est substantiel et se découpe en articles avec une
    couverture suffisante (même seuil que le corpus : 85 %) ;
  * le numéro du texte annoncé figure bien dans le document ;
  * la confiance OCR moyenne n'est pas trop basse ;
  * les marques d'éditeur tiers (Laws.Africa, FAOLEX…) — un document déclaré
    officiel qui en porte n'est pas traité comme officiel ;
  * les doublons (même empreinte sous deux clés).
Un document qui échoue part en QUARANTAINE avec ses motifs. Un document qui
réussit n'est pas « authentifié » pour autant : le statut d'authenticité reste
celui de sa catégorie de source, et aucun texte n'est réputé en vigueur.
"""

import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import corpus, ocr  # noqa: E402

DOSSIER = os.path.join(RACINE, "KNOWLEDGE", "collecte")
MANIFESTE = os.path.join(DOSSIER, "manifeste.json")
DOSSIER_RESULTATS = os.path.join(DOSSIER, "resultats")
DOSSIER_PDF = os.path.join(DOSSIER, "pdf")              # ignoré par git (*.pdf)
INVENTAIRE = os.path.join(DOSSIER, "inventaire_ressources.json")
RECOUPEMENTS = os.path.join(DOSSIER, "recoupements.json")
BRANCHE_ARCHIVE = "corpus/archives-pdf"

CONFIANCE_OCR_MINIMALE = 75.0
DENSITE_MINIMALE = 300      # caractères par page, en moyenne, pour un texte de loi


def lire_json(chemin, defaut=None):
    try:
        with open(chemin, encoding="utf-8") as flux:
            return json.load(flux)
    except FileNotFoundError:
        return defaut


def ecrire_json(chemin, donnees):
    with open(chemin, "w", encoding="utf-8") as flux:
        json.dump(donnees, flux, ensure_ascii=False, indent=1, sort_keys=False)
        flux.write("\n")


def sha256_fichier(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as flux:
        for bloc in iter(lambda: flux.read(1 << 20), b""):
            h.update(bloc)
    return "sha256:" + h.hexdigest()


# ---------------------------------------------------------------------------
# 1. Rapatriement des PDF
# ---------------------------------------------------------------------------
def rapatrier_pdf():
    subprocess.run(["git", "-C", RACINE, "fetch", "-q", "origin",
                    "%s:refs/remotes/origin/%s" % (BRANCHE_ARCHIVE, BRANCHE_ARCHIVE)], check=True)
    ref = "origin/" + BRANCHE_ARCHIVE
    liste = subprocess.run(["git", "-C", RACINE, "ls-tree", "--name-only", ref, "pdf/"],
                           check=True, capture_output=True, text=True).stdout.split()
    os.makedirs(DOSSIER_PDF, exist_ok=True)
    rapatries = 0
    for chemin in liste:
        cible = os.path.join(DOSSIER_PDF, os.path.basename(chemin))
        contenu = subprocess.run(["git", "-C", RACINE, "show", "%s:%s" % (ref, chemin)],
                                 check=True, capture_output=True).stdout
        if os.path.isfile(cible) and open(cible, "rb").read() == contenu:
            continue
        with open(cible, "wb") as flux:
            flux.write(contenu)
        rapatries += 1
    print("PDF dans l'archive : %d ; nouveaux ou modifiés : %d" % (len(liste), rapatries))


# ---------------------------------------------------------------------------
# 2. Contrôles
# ---------------------------------------------------------------------------
def _texte(resultat, cle_fichier):
    relatif = (resultat.get("extraction") or {}).get(cle_fichier)
    if not relatif:
        return None
    chemin = os.path.join(RACINE, relatif)
    return open(chemin, encoding="utf-8").read() if os.path.isfile(chemin) else None


def _variantes_numero(numero):
    """« 2019-574 » -> motifs tolérants (« 2019-574 », « 2019 - 574 », « 2019574 »)."""
    if not numero or not re.match(r"^\d{2,4}-\d{1,4}$", numero):
        return []
    a, b = numero.split("-")
    return [re.compile(r"%s\s*[-‐–—_/]\s*%s(?!\d)" % (a, b)), re.compile(r"(?<!\d)%s%s(?!\d)" % (a, b))]


def indices_ocr_editeur(chemin_pdf):
    """Même détection que la collecte distante, sur le PDF rapatrié."""
    indices = []
    infos = subprocess.run(["pdfinfo", chemin_pdf], capture_output=True, text=True, errors="replace").stdout
    producteur = " ".join(l for l in infos.splitlines() if l.startswith(("Producer", "Creator")))
    for marque in ("Paper Capture", "ABBYY", "FineReader", "OmniPage", "ScanSoft", "Tesseract",
                   "ocrmypdf", "Readiris", "PDF Scanner", "EPSON", "Hewlett-Packard MFP", "Canon"):
        if marque.lower() in producteur.lower():
            indices.append("producteur : " + marque)
    polices = subprocess.run(["pdffonts", chemin_pdf], capture_output=True, text=True, errors="replace").stdout
    if re.search(r"HiddenHorzOCR|GlyphLessFont|OCR", polices):
        indices.append("police d'OCR invisible")
    return indices


def controler_document(source, resultat):
    """Renvoie la fiche d'inventaire d'un document téléchargé."""
    extraction = resultat.get("extraction") or {}
    pages = int(extraction.get("pages") or 0)
    motifs, avertissements = [], []

    # Intégrité du fichier rapatrié.
    chemin_pdf = os.path.join(DOSSIER_PDF, resultat.get("fichier_pdf") or "")
    integrite = "PDF_NON_RAPATRIE"
    if resultat.get("fichier_pdf") and os.path.isfile(chemin_pdf):
        integrite = "OK" if sha256_fichier(chemin_pdf) == resultat.get("sha256") else "EMPREINTE_DIVERGENTE"
        if integrite != "OK":
            motifs.append("empreinte du PDF rapatrié différente de celle du téléchargement")
    qpdf = (resultat.get("pdf") or {}).get("qpdf_check")
    if qpdf == "erreur":
        motifs.append("structure PDF en erreur (qpdf --check)")
    elif qpdf == "avertissements":
        avertissements.append("qpdf signale des avertissements de structure")

    # Un calque texte produit par un logiciel d'OCR n'est pas une lecture.
    indices = (resultat.get("pdf") or {}).get("indices_ocr_editeur")
    if indices is None and integrite == "OK":
        indices = indices_ocr_editeur(chemin_pdf)

    # Texte : calque si dense, sinon texte mixte avec OCR.
    natif = _texte(resultat, "fichier_texte") or ""
    mixte = _texte(resultat, "fichier_ocr")
    densite_native = len(natif) / float(max(1, pages))
    if mixte and extraction.get("pages_sans_texte", 0) > 0:
        texte, methode = mixte, ("OCR_TESSERACT_PARTIEL" if extraction.get("pages_sans_texte") < pages
                                 else "OCR_TESSERACT")
    elif indices:
        texte, methode = natif, "OCR_EDITEUR"
    else:
        texte, methode = natif, "CALQUE_TEXTE"
    confiance = extraction.get("confiance_ocr_moyenne")
    if methode.startswith("OCR_TESSERACT"):
        if confiance is None:
            motifs.append("OCR sans mesure de confiance")
        elif confiance < CONFIANCE_OCR_MINIMALE:
            motifs.append("confiance OCR moyenne %.1f < %.0f" % (confiance, CONFIANCE_OCR_MINIMALE))
        faibles = extraction.get("pages_ocr_faibles") or []
        if faibles:
            avertissements.append("%d page(s) OCR de confiance < 70 : %s"
                                  % (len(faibles), faibles[:15]))
        if extraction.get("ocr_tronque"):
            motifs.append("OCR tronqué : " + extraction["ocr_tronque"])
    densite = len(texte) / float(max(1, pages))
    if densite < DENSITE_MINIMALE:
        motifs.append("texte trop peu dense (%.0f car./page)" % densite)

    # Articles.
    articles = corpus.extraire_articles(texte) if texte else {}
    taux, maximum = corpus.taux_couverture(articles)
    if source.get("type_texte") not in ("page", "inconnu"):
        if not articles:
            motifs.append("aucun article détecté")
        elif taux < corpus.COUVERTURE_MINIMALE:
            motifs.append("découpage en articles incomplet : %.0f%% des articles 1..%d"
                          % (100 * taux, maximum))
    # Identité : le numéro annoncé figure-t-il dans le document ?
    variantes = _variantes_numero(source.get("numero_texte"))
    numero_trouve = None
    if variantes:
        numero_trouve = any(v.search(texte or "") for v in variantes)
        if not numero_trouve:
            motifs.append("le numéro %s n'apparaît pas dans le texte extrait" % source["numero_texte"])
    if source.get("type_texte") == "inconnu":
        motifs.append("contenu non identifié")

    # Provenance observée.
    contaminants = sorted(set(corpus.textes_contaminants(texte or "")) |
                          set(resultat.get("marques_tierces_observees") or []))
    categorie = source.get("categorie_source") or ""
    if categorie.startswith("OFFICIEL") and contaminants:
        motifs.append("déclaré officiel mais porte des marques d'éditeur tiers : %s"
                      % ", ".join(contaminants))

    officiel = categorie.startswith("OFFICIEL")
    if motifs:
        statut = "QUARANTAINE"
    elif officiel:
        statut = "EXPLOITABLE_OFFICIEL"
    else:
        statut = "EXPLOITABLE_RECOUPEMENT_SEULEMENT"

    return {
        "cle": source["cle"],
        "titre": source.get("titre"),
        "numero_texte": source.get("numero_texte"),
        "date_texte": source.get("date_texte"),
        "type_texte": source.get("type_texte"),
        "autorite": source.get("autorite"),
        "domaines": source.get("domaines") or [],
        "url": source["url"],
        "url_finale": resultat.get("url_finale"),
        "date_recuperation": resultat.get("date_recuperation"),
        "categorie_source": categorie,
        "authenticite": ("source officielle déclarée — non authentifiée, vigueur non vérifiée"
                         if officiel else "reproduction secondaire — jamais source de référence"),
        "format": "PDF %s" % ((resultat.get("pdf") or {}).get("PDF version") or "?"),
        "octets": resultat.get("octets"),
        "sha256": resultat.get("sha256"),
        "pages": pages,
        "polices": (resultat.get("pdf") or {}).get("polices"),
        "integrite_pdf": integrite,
        "methode_extraction": methode,
        "indices_ocr_editeur": indices or [],
        "seconde_lecture_tesseract": bool(extraction.get("ocr_force") and extraction.get("fichier_ocr")),
        "densite_native_car_par_page": round(densite_native),
        "confiance_ocr_moyenne": confiance,
        "articles_detectes": len(articles),
        "article_max": maximum,
        "couverture_articles": round(taux, 4),
        "numero_present_dans_le_texte": numero_trouve,
        "marques_tierces": contaminants,
        "statut_controle": statut,
        "motifs_quarantaine": motifs,
        "avertissements": avertissements,
        "notes": source.get("notes"),
    }


def controler():
    manifeste = lire_json(MANIFESTE)
    sources = {s["cle"]: s for s in manifeste["sources"]}
    documents, decouvertes, echecs, non_collectes = [], [], [], []
    for cle, source in sources.items():
        resultat = lire_json(os.path.join(DOSSIER_RESULTATS, cle + ".json"))
        if resultat is None or resultat.get("url") != source["url"]:
            non_collectes.append({"cle": cle, "url": source["url"]})
            continue
        statut = resultat.get("statut")
        if statut == "TELECHARGE":
            documents.append(controler_document(source, resultat))
        elif statut == "DECOUVERTE":
            decouvertes.append({"cle": cle, "url": source["url"], "titre_page": resultat.get("titre_page"),
                                "liens": len(resultat.get("liens") or [])})
        else:
            echecs.append({"cle": cle, "url": source["url"], "categorie_source": source.get("categorie_source"),
                           "statut": statut, "http": resultat.get("http"),
                           "erreur": resultat.get("erreur"), "debut": (resultat.get("debut") or "")[:80],
                           "date_recuperation": resultat.get("date_recuperation")})

    par_empreinte = collections.defaultdict(list)
    for d in documents:
        par_empreinte[d["sha256"]].append(d["cle"])
    for d in documents:
        jumeaux = [c for c in par_empreinte[d["sha256"]] if c != d["cle"]]
        d["doublon_de"] = jumeaux
        if jumeaux:
            d["avertissements"].append("même fichier que : %s" % ", ".join(jumeaux))

    compte = collections.Counter(d["statut_controle"] for d in documents)
    execution = lire_json(os.path.join(DOSSIER, "derniere_execution.json"), {})
    inventaire = {
        "objet": ("Inventaire des ressources collectées — produit par bin/integrer_collecte.py "
                  "à partir des constats réels (resultats/*.json). Aucun chiffre saisi à la main."),
        "genere_le": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
        "outils_collecte": execution.get("outils"),
        "totaux": {
            "entrees_manifeste": len(sources),
            "documents_telecharges": len(documents),
            "pages_de_decouverte_lues": len(decouvertes),
            "echecs": len(echecs),
            "non_encore_collectes": len(non_collectes),
            "par_statut_controle": dict(sorted(compte.items())),
            "par_categorie": dict(sorted(collections.Counter(
                d["categorie_source"] for d in documents).items())),
            "par_methode_extraction": dict(sorted(collections.Counter(
                d["methode_extraction"] for d in documents).items())),
            "pdf_rapatries_et_verifies": sum(1 for d in documents if d["integrite_pdf"] == "OK"),
        },
        "documents": sorted(documents, key=lambda d: d["cle"]),
        "echecs": echecs,
        "decouvertes": decouvertes,
        "non_encore_collectes": non_collectes,
    }
    ecrire_json(INVENTAIRE, inventaire)
    print(json.dumps(inventaire["totaux"], ensure_ascii=False, indent=1))
    for d in inventaire["documents"]:
        print("%-44s %-34s art=%-4s couv=%-5s %s" % (
            d["cle"][:44], d["statut_controle"], d["articles_detectes"], d["couverture_articles"],
            "; ".join(d["motifs_quarantaine"])[:120]))
    return inventaire


# ---------------------------------------------------------------------------
# 3. Recoupements officiel / secondaire
# ---------------------------------------------------------------------------
def articles_de(cle):
    resultat = lire_json(os.path.join(DOSSIER_RESULTATS, cle + ".json")) or {}
    extraction = resultat.get("extraction") or {}
    texte = _texte(resultat, "fichier_ocr") if extraction.get("pages_sans_texte") else None
    texte = texte or _texte(resultat, "fichier_texte") or ""
    return corpus.extraire_articles(texte)


def articles_du_corpus(numero_texte):
    """Articles déjà indexés dans la base pour ce numéro (documents citables seulement)."""
    trouves = {}
    with corpus.connexion() as conn:
        for ligne in conn.execute(
                "SELECT a.numero, a.texte, d.doc_id FROM articles_corpus a JOIN documents d"
                " ON d.doc_id = a.doc_id WHERE d.numero_texte = ? AND d.articles_fiables = 1",
                (numero_texte,)):
            trouves.setdefault(ligne["doc_id"], {})[ligne["numero"]] = ligne["texte"]
    return trouves


def recouper():
    inventaire = lire_json(INVENTAIRE)
    if not inventaire:
        raise SystemExit("lancer d'abord : controler")
    par_numero = collections.defaultdict(list)
    for d in inventaire["documents"]:
        if d["numero_texte"]:
            par_numero[d["numero_texte"]].append(d)
    resultats = []
    for numero, docs in sorted(par_numero.items()):
        lectures = {d["cle"]: articles_de(d["cle"]) for d in docs}
        for doc_id, articles in articles_du_corpus(numero).items():
            lectures["corpus:" + doc_id] = articles
        cles = sorted(lectures)
        for i, a in enumerate(cles):
            for b in cles[i + 1:]:
                if not lectures[a] or not lectures[b]:
                    continue
                evaluation = ocr.evaluer_articles_ocr(lectures[a], lectures[b])
                communs = sorted(set(lectures[a]) & set(lectures[b]), key=ocr._tri_numero)
                divergents = [e for e in evaluation["ecartes"]]
                resultats.append({
                    "numero_texte": numero, "lecture_a": a, "lecture_b": b,
                    "articles_a": len(lectures[a]), "articles_b": len(lectures[b]),
                    "articles_communs": len(communs),
                    "seulement_dans_a": sorted(set(lectures[a]) - set(lectures[b]), key=ocr._tri_numero)[:60],
                    "seulement_dans_b": sorted(set(lectures[b]) - set(lectures[a]), key=ocr._tri_numero)[:60],
                    "statistiques": evaluation.get("statistiques"),
                    "articles_divergents": [{"numero": e["numero"], "similarite": e["similarite"]}
                                            for e in divergents][:80],
                })
    ecrire_json(RECOUPEMENTS, {
        "objet": ("Comparaison article par article entre lectures d'un même texte (officielle, "
                  "secondaire, corpus). Une divergence signale une erreur de lecture OU une "
                  "modification du texte : elle se tranche à la lecture humaine."),
        "genere_le": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
        "comparaisons": resultats})
    for r in resultats:
        s = r["statistiques"] or {}
        print("%-12s %-40s ~ %-40s communs=%-4s moy=%s div=%d" % (
            r["numero_texte"], r["lecture_a"][:40], r["lecture_b"][:40], r["articles_communs"],
            s.get("similarite_moyenne"), len(r["articles_divergents"])))


# ---------------------------------------------------------------------------
# 4. Intégration des documents OFFICIELS contrôlés (calque texte seulement)
# ---------------------------------------------------------------------------
# Domaine du moteur et dossier de rangement, déduits du premier domaine déclaré.
DOMAINE_MOTEUR = {2: "famille_mariage_filiation", 22: "famille_mariage_filiation",
                  5: "penal_procedure_penale", 4: "travail", 23: "contrats_dettes_commerce",
                  10: "administratif_voies_de_recours"}


def officialiser(cles=None):
    """Range les documents EXPLOITABLE_OFFICIEL lus par calque texte et les fait passer
    par le collecteur du corpus (bin/collecter_domaine.py) et ses garde-fous : hôte
    officiel, empreinte recalculée, couverture des articles, marques d'éditeur tiers.
    Un document OCR n'est PAS intégré ici : il exige un recoupement (étape distincte)."""
    import shutil
    sys.path.insert(0, os.path.join(RACINE, "bin"))
    import collecter_domaine
    inventaire = lire_json(INVENTAIRE)
    manifeste = {s["cle"]: s for s in lire_json(MANIFESTE)["sources"]}
    a_collecter = collections.defaultdict(list)
    for d in inventaire["documents"]:
        if cles and d["cle"] not in cles:
            continue
        if d["statut_controle"] != "EXPLOITABLE_OFFICIEL" or d["methode_extraction"] != "CALQUE_TEXTE":
            continue
        if d["integrite_pdf"] != "OK":
            print("ignoré (PDF non rapatrié ou divergent) : %s" % d["cle"])
            continue
        domaine = DOMAINE_MOTEUR.get((d["domaines"] or [None])[0])
        if not domaine:
            print("ignoré (aucun domaine du moteur) : %s" % d["cle"])
            continue
        dossier, chemin_manifeste = collecter_domaine.chemin_manifeste(domaine)
        os.makedirs(dossier, exist_ok=True)
        shutil.copyfile(os.path.join(DOSSIER_PDF, d["cle"] + ".pdf"), os.path.join(dossier, d["cle"] + ".pdf"))
        resultat = lire_json(os.path.join(DOSSIER_RESULTATS, d["cle"] + ".json"))
        shutil.copyfile(os.path.join(RACINE, resultat["extraction"]["fichier_texte"]),
                        os.path.join(dossier, d["cle"] + ".txt"))
        local = lire_json(chemin_manifeste, {"domaine": domaine, "dossier": os.path.basename(dossier),
                                             "sources": []})
        source = manifeste[d["cle"]]
        entree = {"cle": d["cle"], "titre": source["titre"], "type_texte": source["type_texte"],
                  "numero_texte": source.get("numero_texte"), "date_texte": source.get("date_texte"),
                  "autorite": source["autorite"], "url": source["url"], "fichier": d["cle"] + ".pdf",
                  "pages": d["pages"],
                  "limites": ("%s Collecté le %s par GitHub Actions (KNOWLEDGE/collecte/resultats/%s.json)."
                              % (source.get("notes") or "", d["date_recuperation"][:10], d["cle"])).strip()}
        local["sources"] = [e for e in local["sources"] if e["cle"] != d["cle"]] + [entree]
        ecrire_json(chemin_manifeste, local)
        a_collecter[domaine].append(d["cle"])
    for domaine, liste in sorted(a_collecter.items()):
        print("== %s : %s" % (domaine, ", ".join(liste)))
        rapport = collecter_domaine.collecter(domaine, telecharger_si_absent=False)
        for doc in rapport["documents"]:
            if doc["cle"] in liste:
                print("   %-34s %s art=%s %s" % (doc["cle"], doc.get("etat_verification"),
                                                  doc.get("articles_indexes"), doc.get("motif_non_indexe") or ""))


def officialiser_ocr(cles=None):
    """Intègre les documents officiels dont le texte vient d'un OCR.

    Lecture principale : le calque de l'éditeur (OCR_EDITEUR) ou tesseract.
    Quand deux lectures indépendantes du MÊME scan existent (calque de l'éditeur
    et tesseract), chaque article reçoit leur similarité comme confiance et
    seuls ceux qui atteignent le seuil du corpus (0,80) sont indexés. Deux OCR
    d'un même scan ne sont pas deux exemplaires officiels : `recoupe` reste à 0,
    la référence reste PARTIELLEMENT_VERIFIE, et toute réponse qui s'y appuie
    déclare l'incertitude (garde-fou existant du moteur).
    """
    import datetime as _dt
    import shutil
    sys.path.insert(0, os.path.join(RACINE, "bin"))
    import collecter_domaine
    from core import base
    inventaire = lire_json(INVENTAIRE)
    manifeste = {s["cle"]: s for s in lire_json(MANIFESTE)["sources"]}
    bilan = []
    for d in inventaire["documents"]:
        if cles and d["cle"] not in cles:
            continue
        if not d["categorie_source"].startswith("OFFICIEL") or not d["methode_extraction"].startswith("OCR"):
            continue
        motifs_bloquants = [m for m in d["motifs_quarantaine"] if not m.startswith("découpage en articles")]
        if motifs_bloquants or d["integrite_pdf"] != "OK":
            bilan.append((d["cle"], "IGNORE", "; ".join(motifs_bloquants) or d["integrite_pdf"]))
            continue
        domaine = DOMAINE_MOTEUR.get((d["domaines"] or [None])[0])
        if not domaine:
            bilan.append((d["cle"], "IGNORE", "aucun domaine du moteur"))
            continue
        resultat = lire_json(os.path.join(DOSSIER_RESULTATS, d["cle"] + ".json"))
        extraction = resultat["extraction"]
        principal = _texte(resultat, "fichier_texte") if d["methode_extraction"] == "OCR_EDITEUR" \
            else _texte(resultat, "fichier_ocr")
        second = _texte(resultat, "fichier_ocr") if d["methode_extraction"] == "OCR_EDITEUR" \
            and extraction.get("ocr_force") else None
        articles = corpus.extraire_articles(principal or "")
        confiance, ecartes = None, []
        comparateur = "LECTURE_INDEPENDANTE_TESSERACT:" + d["cle"] if second else None
        if not second:
            # Sans seconde lecture du même scan : une reproduction secondaire du MÊME
            # texte sert d'étalon pour MESURER l'OCR. Elle ne fournit aucun mot du
            # texte indexé, et `recoupe` reste à 0 (ce n'est pas un exemplaire officiel).
            for autre in inventaire["documents"]:
                if (autre["numero_texte"] == d["numero_texte"] and autre["numero_texte"]
                        and autre["statut_controle"] == "EXPLOITABLE_RECOUPEMENT_SEULEMENT"
                        and autre["methode_extraction"] == "CALQUE_TEXTE"):
                    second = _texte(lire_json(os.path.join(DOSSIER_RESULTATS, autre["cle"] + ".json")),
                                    "fichier_texte")
                    comparateur = "SECONDAIRE:" + autre["cle"]
                    break
        if second:
            articles_second = corpus.extraire_articles(second)
            confiance, retenus = {}, {}
            for numero, texte in articles.items():
                if numero not in articles_second:
                    ecartes.append((numero, None))
                    continue
                valeur = round(ocr.similarite(texte, articles_second[numero]), 4)
                if valeur >= ocr.QUALITE_MINIMALE:
                    retenus[numero], confiance[numero] = texte, valeur
                else:
                    ecartes.append((numero, valeur))
            articles = retenus
        dossier, _ = collecter_domaine.chemin_manifeste(domaine)
        os.makedirs(dossier, exist_ok=True)
        chemin_pdf = os.path.join(dossier, d["cle"] + ".pdf")
        shutil.copyfile(os.path.join(DOSSIER_PDF, d["cle"] + ".pdf"), chemin_pdf)
        chemin_ocr = os.path.join(dossier, d["cle"] + ".ocr.txt")
        with open(chemin_ocr, "w", encoding="utf-8") as flux:
            flux.write(principal or "")
        source = manifeste[d["cle"]]
        aujourd_hui = _dt.date.today().isoformat()
        lecture = ("calque texte produit par un logiciel d'OCR (%s)" % ", ".join(d["indices_ocr_editeur"])
                   if d["methode_extraction"] == "OCR_EDITEUR" else
                   "OCR tesseract (fra), confiance moyenne %s" % d["confiance_ocr_moyenne"])
        ref_id = base.ajouter_reference(
            titre_officiel=source["titre"], type_texte=source["type_texte"],
            numero_texte=source.get("numero_texte"), date_publication=source.get("date_texte"),
            domaine=domaine, source_nom=source["autorite"], source_url=source["url"],
            date_consultation=aujourd_hui, texte_complet_present=False,
            limites_interpretation=("Exemplaire officiel numérisé ; texte lu par %s. %s"
                                    % (lecture, source.get("notes") or "")).strip())
        base.promouvoir_verification(
            ref_id, "PARTIELLEMENT_VERIFIE", preuve_url=source["url"], preuve_empreinte=d["sha256"],
            date_consultation=aujourd_hui,
            motif="exemplaire officiel téléchargé (empreinte recalculée) ; texte issu d'un OCR, non recoupé "
                  "avec un autre exemplaire officiel")
        doc_id = corpus.importer_document(
            ref_id=ref_id, titre=source["titre"], type_texte=source["type_texte"],
            numero_texte=source.get("numero_texte"), date_texte=source.get("date_texte"), domaine=domaine,
            autorite=source["autorite"], url_source=source["url"], chemin_local=chemin_pdf,
            licence_conditions=collecter_domaine.CONDITIONS_ACCES, pages=d["pages"], calque_texte=False,
            sha256_declare=d["sha256"], note_qualite="scan du Journal officiel ; " + lecture,
            date_collecte=d["date_recuperation"][:10], actualiser=True)
        try:
            indexation = corpus.enregistrer_articles(
                ref_id, doc_id, articles, origine_texte="OCR_AUTO", confiance_ocr=confiance, recoupe=False,
                doc_reference=comparateur,
                remplacer=True)
        except ValueError as erreur:
            corpus.noter_refus_ocr(doc_id, "OCR intégré le %s — REFUSÉ à l'indexation : %s"
                                   % (corpus.horodatage(), erreur), fichier_ocr=chemin_ocr)
            bilan.append((d["cle"], "REFUSE", str(erreur)))
            continue
        moyenne = round(sum(confiance.values()) / len(confiance), 4) if confiance else None
        corpus.enregistrer_ocr_document(
            doc_id, chemin_ocr, recoupe_avec=None, qualite_ocr=moyenne, methode=d["methode_extraction"],
            note=("%s ; %s ; %d article(s) écarté(s) faute d'accord entre les deux lectures"
                  % (lecture, "accord moyen avec %s : %s" % (comparateur, moyenne) if second
                     else "une seule lecture : qualité contrôlée structurellement seulement", len(ecartes))))
        bilan.append((d["cle"], "INTEGRE", "%d articles (couverture %.0f %%), %d écartés%s" % (
            indexation["articles_indexes"], 100 * indexation["couverture"], len(ecartes),
            ", accord moyen %s" % moyenne if moyenne else "")))
    for ligne in bilan:
        print("%-46s %-8s %s" % ligne)
    return bilan


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("etape", choices=("pdf", "controler", "recouper", "officialiser", "officialiser_ocr"))
    analyseur.add_argument("--cle", action="append")
    arguments = analyseur.parse_args(argv)
    if arguments.etape == "officialiser":
        officialiser(arguments.cle)
    elif arguments.etape == "officialiser_ocr":
        officialiser_ocr(arguments.cle)
    else:
        {"pdf": rapatrier_pdf, "controler": controler, "recouper": recouper}[arguments.etape]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
