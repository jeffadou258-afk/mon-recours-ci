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
JOURNAL_OCR = os.environ.get("MONRECOURS_JOURNAL_OCR") or os.path.join(DOSSIER, "integrations_ocr.json")
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


MOTIF_ACTE = re.compile(r"(?im)^[ \t\-—]*(?:LO ?I|D[ÉE]CRET|ORDONNANCE)\s+n\s*[°o]\s*(\d{4})\s*[-–]\s*(\d{1,4})")


def autres_actes_du_document(texte, numero):
    """Numéros d'actes, autres que `numero`, qui ouvrent une ligne du document."""
    trouves = []
    for annee, rang in MOTIF_ACTE.findall(texte or ""):
        acte = "%s-%s" % (annee, rang)
        if acte != numero and acte not in trouves:
            trouves.append(acte)
    return trouves


def segmenter(texte, segment):
    """Ne garde que le texte compris entre deux motifs déclarés dans le manifeste."""
    if not segment:
        return texte
    debut = re.search(segment["debut"], texte or "")
    if not debut:
        raise ValueError("début de segment introuvable : %r" % segment["debut"])
    fin = re.search(segment["fin"], texte[debut.end():]) if segment.get("fin") else None
    return texte[debut.start(): debut.end() + fin.start()] if fin else texte[debut.start():]


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
    locale = resultat.get("extraction_locale") or {}
    if not mixte and locale.get("fichier_ocr") and os.path.isfile(os.path.join(RACINE, locale["fichier_ocr"])) \
            and len(natif) / float(max(1, pages)) < DENSITE_MINIMALE:
        # Scan sans OCR distant (COLLECTE_OCR=0) : la lecture locale tessdata_best fait foi pour le contrôle.
        mixte = open(os.path.join(RACINE, locale["fichier_ocr"]), encoding="utf-8").read()
        extraction = dict(extraction, pages_sans_texte=pages, confiance_ocr_moyenne=locale.get("confiance_ocr_moyenne"),
                          pages_ocr_faibles=locale.get("pages_ocr_faibles"))
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
    corrections_en_tetes = []
    if methode.startswith("OCR"):
        texte, corrections_en_tetes = ocr.normaliser_en_tetes_jo(texte)
    if source.get("segment"):
        try:
            texte = segmenter(texte, source["segment"])
        except ValueError as erreur:
            motifs.append(str(erreur))
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
    # Un numéro du Journal officiel publie souvent plusieurs actes : indexé d'un
    # bloc, leurs articles se mélangent (cas réel : mariage et filiation, JO du
    # 12 juillet 2019). Sans segment déclaré dans le manifeste, quarantaine.
    autres_actes = [a for a in autres_actes_du_document(texte, source.get("numero_texte"))
                    if a not in (source.get("actes_ocr_ignores") or {})]
    if autres_actes and not source.get("segment"):
        motifs.append("le document contient d'autres actes (%s) : segmentation requise"
                      % ", ".join(autres_actes[:6]))

    # Provenance observée.
    contaminants = sorted(set(corpus.textes_contaminants(texte or "")) |
                          set(resultat.get("marques_tierces_observees") or []))
    categorie = source.get("categorie_source") or ""
    if categorie.startswith("OFFICIEL") and contaminants:
        motifs.append("déclaré officiel mais porte des marques d'éditeur tiers : %s"
                      % ", ".join(contaminants))

    officiel = categorie.startswith("OFFICIEL")
    if source.get("version_abrogee"):
        statut = "VERSION_ABROGEE"
    elif motifs:
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
        "en_tetes_ocr_corriges": len(corrections_en_tetes),
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
        "version_abrogee": source.get("version_abrogee"),
    }


def controler():
    manifeste = lire_json(MANIFESTE)
    sources = {s["cle"]: s for s in manifeste["sources"]}
    documents, decouvertes, echecs, non_collectes, abandonnees = [], [], [], [], []
    for cle, source in sources.items():
        resultat = lire_json(os.path.join(DOSSIER_RESULTATS, cle + ".json"))
        if source.get("desactivee"):
            abandonnees.append({"cle": cle, "url": source["url"], **source["desactivee"],
                                "tentatives": len((resultat or {}).get("historique") or []) or (1 if resultat else 0)})
            continue
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
            "entrees_desactivees": len(abandonnees),
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
        "desactivees": abandonnees,
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
def articles_de(cle, source=None):
    resultat = lire_json(os.path.join(DOSSIER_RESULTATS, cle + ".json")) or {}
    extraction = resultat.get("extraction") or {}
    texte = _texte(resultat, "fichier_ocr") if extraction.get("pages_sans_texte") else None
    texte = texte or _texte(resultat, "fichier_texte") or ""
    texte, _ = ocr.normaliser_en_tetes_jo(texte)   # sans effet sur un calque texte conforme
    if source and source.get("segment"):
        try:
            texte = segmenter(texte, source["segment"])
        except ValueError:
            return {}
    return corpus.extraire_articles(nettoyer_lecture(texte)[0])


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


# En-têtes et pieds de page du Journal officiel : ils tombent au milieu des
# articles à chaque changement de page. Ils sont retirés de la LECTURE (jamais
# du fichier brut, conservé dans KNOWLEDGE/collecte/textes/) et comptés.
_MOIS = r"(?:janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)"
MOTIFS_EN_TETES = (
    re.compile(r"(?m)^(--- PAGE \d+ ---)[ \t]*\[OCR conf=[^\]]*\][ \t]*$"),   # marqueur de page : conservé nu
    re.compile(r"(?im)^[^\n]*Journal officiel OHADA 2023 Az[^\n]*$"),
    re.compile(r"(?im)^[ \t]*ACTE UNIFORME PORTANT ORGANISATION DES PROC[ÉE]DURES SIMPLIFI[ÉE]ES DE"
               r"(?:[ \t]*\n?[ \t]*RECOUVREMENT ET DES VOIES D.EX[ÉE]CUTION)?[ \t]*$"),
    re.compile(r"(?im)^[ \t]*JOURNAL OFFICIEL DE LA R[ÉE]PUBLIQUE DE C[ÔO]TE D.IVOIRE[ \t]*$"),
    re.compile(r"(?im)^[ \t]*[0-9IlO]{1,2}[ \t]+" + _MOIS + r"[ \t]+\d{4}[ \t]*$"),
    re.compile(r"(?m)^[ \t]*\d{1,4}[ \t]*$"),
)


def nettoyer_lecture(texte):
    """Retire en-têtes, pieds et numéros de page ; renvoie (texte, nombre de retraits)."""
    retraits = 0
    texte, n = MOTIFS_EN_TETES[0].subn(r"\1", texte or "")
    for motif in MOTIFS_EN_TETES[1:]:
        texte, n = motif.subn("", texte)
        retraits += n
    return texte, retraits


# ---------------------------------------------------------------------------
# 4. Intégration des documents OFFICIELS contrôlés (calque texte seulement)
# ---------------------------------------------------------------------------
# Domaine du moteur et dossier de rangement, déduits du premier domaine déclaré.
_DOMAINES_FIXES = {2: "famille_mariage_filiation", 22: "famille_mariage_filiation",
                   5: "penal_procedure_penale", 4: "travail", 23: "contrats_dettes_commerce",
                   10: "administratif_voies_de_recours"}


def _domaines_moteur():
    """Domaine du moteur pour chaque domaine de la vision : la table historique, puis
    le premier `cles_moteur` déclaré dans KNOWLEDGE/domaines_24.json."""
    table = dict(_DOMAINES_FIXES)
    registre = lire_json(os.path.join(RACINE, "KNOWLEDGE", "domaines_24.json"), {"domaines": []})
    for d in registre["domaines"]:
        if d["code"] not in table and d.get("cles_moteur"):
            table[d["code"]] = d["cles_moteur"][0]
    return table


DOMAINE_MOTEUR = _domaines_moteur()


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


_NOMBRE = re.compile(r"\d+")

# ---------------------------------------------------------------------------
# Lisibilité d'un article OCR (20/10/2026)
# ---------------------------------------------------------------------------
# Deux lectures tesseract d'une page très dégradée peuvent CONCORDER dans
# l'erreur (cas réel : page 2 de l'exemplaire mffe.ci de la loi 2018-862,
# « [Les aotes sont imeonits aur Les nepistnes »). Un modèle de trigrammes de
# caractères, appris sur les textes NATIFS du corpus (aucun OCR), mesure la
# vraisemblance du texte : seuils réglés sur des cas vérifiés à l'image.
SEUIL_LISIBILITE = -2.35
SEUIL_LISIBILITE_DOUTEUSE = -2.2
SEUIL_VOCABULAIRE = 0.75
_MODELE_LISIBILITE = None


def _modele_lisibilite():
    global _MODELE_LISIBILITE
    if _MODELE_LISIBILITE is None:
        import glob
        import math  # noqa: F401
        textes = []
        inventaire = lire_json(INVENTAIRE, {"documents": []})
        for d in inventaire["documents"]:
            if not d.get("indices_ocr_editeur") and (d.get("densite_native_car_par_page") or 0) > 800:
                chemin = os.path.join(DOSSIER, "textes", d["cle"] + ".txt")
                if os.path.isfile(chemin):
                    textes.append(open(chemin, encoding="utf-8").read())
        for chemin in glob.glob(os.path.join(RACINE, "KNOWLEDGE", "CORPUS", "*", "*.txt")):
            if ".ocr" not in chemin:
                textes.append(open(chemin, encoding="utf-8").read())
        tout = re.sub(r"\s+", " ", " ".join(textes).lower())
        tri = collections.Counter(tout[i:i + 3] for i in range(len(tout) - 2))
        bi = collections.Counter(tout[i:i + 2] for i in range(len(tout) - 1))
        mots = collections.Counter(re.findall(r"[a-zàâäçéèêëîïôöùûüÿœæ]{4,}", tout))
        _MODELE_LISIBILITE = (tri, bi, len(set(tout)), {m for m, c in mots.items() if c >= 2})
    return _MODELE_LISIBILITE


def lisibilite(texte):
    """(score trigrammes, part de mots connus) d'un texte ; plus haut = plus lisible."""
    import math
    tri, bi, alphabet, vocabulaire = _modele_lisibilite()
    t = re.sub(r"\s+", " ", (texte or "").lower())
    if len(t) < 10:
        return 0.0, 1.0
    score = sum(math.log((tri[t[i:i + 3]] + 0.1) / (bi[t[i:i + 2]] + 0.1 * alphabet))
                for i in range(len(t) - 2)) / (len(t) - 2)
    mots = re.findall(r"[a-zàâäçéèêëîïôöùûüÿœæ]{4,}", t)
    part = (sum(1 for m in mots if m in vocabulaire) / len(mots)) if mots else 1.0
    return round(score, 3), round(part, 3)


def illisible(texte):
    score, part = lisibilite(texte)
    return score < SEUIL_LISIBILITE or (score < SEUIL_LISIBILITE_DOUTEUSE and part < SEUIL_VOCABULAIRE)


def _nombres(texte):
    """Suite des nombres d'un article (délais, montants, renvois)."""
    return _NOMBRE.findall(texte or "")


def nombres_substitues(a, b):
    """Nombres de `a` remplacés par un AUTRE nombre au même endroit de `b`.

    Alignement mot à mot : un nombre seulement inséré ou omis (numéro de page du
    Journal officiel incrusté dans une colonne, « 1 » parasite) est du bruit de
    mise en page ; un nombre REMPLACÉ (« 43 » lu pour « 45 », « 11 » pour « 1 »)
    change le droit (délai, montant, renvoi) : l'article est alors écarté."""
    import difflib
    a_mots, mots_b = (a or "").split(), (b or "").split()
    paires = []
    comparateur = difflib.SequenceMatcher(None, a_mots, mots_b, autojunk=False)
    for operation, i1, i2, j1, j2 in comparateur.get_opcodes():
        if operation != "replace":
            continue
        gauche = [n for m in a_mots[i1:i2] for n in _NOMBRE.findall(m)]
        droite = [n for m in mots_b[j1:j2] for n in _NOMBRE.findall(m)]
        if gauche and droite and gauche != droite:
            paires.append((" ".join(gauche), " ".join(droite)))
    return paires


def _lecture(texte, segment):
    texte, corrections = ocr.normaliser_en_tetes_jo(texte or "")
    texte, retraits = nettoyer_lecture(segmenter(texte, segment) if segment else texte)
    return texte, corpus.extraire_articles(texte or ""), corrections, retraits


def _textes_bruts(d, resultat):
    """Textes bruts (avec marqueurs de page) des lectures d'un scan, par nom de lecture."""
    extraction = resultat.get("extraction") or {}
    sortie = []
    if d["indices_ocr_editeur"]:
        sortie.append(("CALQUE_EDITEUR:" + ",".join(d["indices_ocr_editeur"]), _texte(resultat, "fichier_texte")))
    if extraction.get("fichier_ocr"):
        sortie.append(("TESSERACT_DISTANT:%s dpi" % extraction.get("dpi_ocr", 200), _texte(resultat, "fichier_ocr")))
    for cle_locale, nom in (("extraction_locale", "TESSERACT_LOCAL_BEST"), ("extraction_locale_fast", "TESSERACT_LOCAL_FAST")):
        locale = resultat.get(cle_locale) or {}
        if locale.get("fichier_ocr") and os.path.isfile(os.path.join(RACINE, locale["fichier_ocr"])):
            sortie.append(("%s:%s dpi" % (nom, locale.get("dpi")),
                           open(os.path.join(RACINE, locale["fichier_ocr"]), encoding="utf-8").read()))
    return sortie


def lectures_du_scan(d, resultat, source):
    """Toutes les lectures d'un même scan : calque d'éditeur (s'il vient d'un OCR),
    tesseract distant, tesseract local (tessdata_best). Renvoie
    [(nom, texte, articles, corrections_en_tetes, retraits)]."""
    extraction = resultat.get("extraction") or {}
    candidates = []
    if d["indices_ocr_editeur"] and len(_texte(resultat, "fichier_texte") or "") > DENSITE_MINIMALE * max(1, d["pages"]) / 2:
        candidates.append(("CALQUE_EDITEUR:" + ",".join(d["indices_ocr_editeur"]), _texte(resultat, "fichier_texte")))
    if extraction.get("fichier_ocr"):
        candidates.append(("TESSERACT_DISTANT:%s dpi" % extraction.get("dpi_ocr", 200), _texte(resultat, "fichier_ocr")))
    for cle_locale, nom in (("extraction_locale", "TESSERACT_LOCAL_BEST"), ("extraction_locale_fast", "TESSERACT_LOCAL_FAST")):
        locale = resultat.get(cle_locale) or {}
        if locale.get("fichier_ocr") and os.path.isfile(os.path.join(RACINE, locale["fichier_ocr"])):
            candidates.append(("%s:%s dpi" % (nom, locale.get("dpi")),
                               open(os.path.join(RACINE, locale["fichier_ocr"]), encoding="utf-8").read()))
    lectures = []
    for nom, texte in candidates:
        try:
            lecture = _lecture(texte, source.get("segment"))
        except ValueError:
            continue   # segment introuvable dans cette lecture : elle n'est pas utilisée
        lectures.append((nom,) + lecture)
    return lectures


def preparer_ocr(d, inventaire, manifeste):
    """Calcule, SANS RIEN ÉCRIRE, les articles qu'une intégration OCR retiendrait.

    Renvoie None (aucune lecture) ou un dict : articles, confiance, ecartes, principal,
    nom_principal, comparateur, copies, corrections_en_tetes, retraits."""
    resultat = lire_json(os.path.join(DOSSIER_RESULTATS, d["cle"] + ".json"))
    source_m = manifeste[d["cle"]]
    extraction = resultat["extraction"]
    # Lectures disponibles du MÊME scan (indépendantes par le moteur ou le modèle) :
    # la principale est celle qui découpe le plus d'articles ; chaque article
    # retenu doit concorder (>= 0,80) avec au moins une AUTRE lecture.
    lectures = lectures_du_scan(d, resultat, source_m)
    if not lectures:
        return None
    lectures = sorted(lectures, key=lambda l: (-len(l[2]), l[0]))
    nom_principal, principal, articles, corrections_en_tetes, retraits = lectures[0]
    # Candidats : chaque numéro d'article pris dans la PREMIÈRE lecture du scan qui le
    # contient (la principale d'abord). Le texte indexé vient donc toujours d'une
    # lecture de CE scan officiel ; il doit concorder avec une autre lecture.
    candidats, provenance = {}, {}
    for nom, _, arts, _, _ in lectures:
        for numero, texte in arts.items():
            if numero not in candidats:
                candidats[numero], provenance[numero] = texte, nom
    etalons = [(nom, arts) for nom, _, arts, _, _ in lectures]
    # Une reproduction secondaire du MÊME texte peut servir d'étalon pour MESURER
    # l'OCR. Elle ne fournit aucun mot du texte indexé, et `recoupe` reste à 0.
    # Autres exemplaires du même texte (autre scan officiel, texte voté, reproduction) :
    # étalons de MESURE seulement. Un document en quarantaine pour une seule raison
    # d'identité ou de découpage peut mesurer : la concordance article par article
    # (>= 0,80) établit elle-même qu'il s'agit du même texte.
    for autre in inventaire["documents"]:
        if autre["cle"] == d["cle"] or not autre["numero_texte"] or autre["numero_texte"] != d["numero_texte"]:
            continue
        motifs = [m for m in autre["motifs_quarantaine"]
                  if not m.startswith(("découpage en articles", "le numéro"))]
        if motifs or autre["integrite_pdf"] != "OK":
            continue
        genre = "OFFICIEL" if autre["categorie_source"].startswith("OFFICIEL") else "SECONDAIRE"
        arts = articles_de(autre["cle"], manifeste.get(autre["cle"]))
        if arts:
            etalons.append(("%s:%s" % (genre, autre["cle"]), arts))
    # Un étalon dont le texte est IDENTIQUE à la lecture principale n'est pas une
    # lecture indépendante : c'est le même calque OCR recopié (cas réel : le PDF
    # FAOLEX de la loi 2019-570 porte le calque ABBYY du PDF de mffe.ci). Écarté.
    lectures_du_meme_scan = {nom for nom, _, _, _, _ in lectures}
    independants, copies = [], []
    for nom, arts in etalons:
        if nom in lectures_du_meme_scan:
            independants.append((nom, arts))
            continue
        copie = False
        for _, _, arts_scan, _, _ in lectures:   # copie de N'IMPORTE QUELLE lecture du scan ?
            communs = [n for n in arts_scan if n in arts]
            identiques = sum(1 for n in communs if " ".join(arts_scan[n].split()) == " ".join(arts[n].split()))
            if communs and identiques >= 0.5 * len(communs):
                copie = True
                break
        (copies if copie else independants).append((nom, arts))
    etalons = independants
    confiance, ecartes = None, []
    comparateur = "+".join(nom for nom, _ in etalons if nom != nom_principal) or None
    second = bool(comparateur)
    articles = dict(candidats)
    nombres_divergents, nombres_contestes, illisibles = [], {}, []
    if second:
        confiance, retenus = {}, {}
        lectures_scan = [(nom, arts) for nom, _, arts, _, _ in lectures]
        for numero in candidats:
            # Pour chaque article : la lecture DE CE SCAN la mieux confirmée par une
            # autre lecture (jamais par elle-même), à condition que les nombres
            # (délais, montants, renvois) soient identiques dans la lecture qui confirme.
            meilleur = None   # (similarité, texte, lecture)
            divergence = False
            for nom_l, arts_l in lectures_scan:
                if numero not in arts_l:
                    continue
                texte = arts_l[numero]
                for nom_e, arts_e in etalons:
                    if nom_e == nom_l or numero not in arts_e:
                        continue
                    valeur = ocr.similarite(texte, arts_e[numero])
                    if valeur < ocr.QUALITE_MINIMALE:
                        continue
                    if nombres_substitues(texte, arts_e[numero]):
                        divergence = True
                        continue
                    if meilleur is None or valeur > meilleur[0]:
                        meilleur = (valeur, texte, nom_l)
            if meilleur and illisible(meilleur[1]):
                illisibles.append(numero)
                ecartes.append((numero, None))
                continue
            if meilleur:
                retenus[numero], confiance[numero] = meilleur[1], round(meilleur[0], 4)
                provenance[numero] = meilleur[2]
                # Nombres contestés : une AUTRE lecture concordante (>= 0,80) lit un nombre
                # différent au même endroit. L'article reste indexé (une lecture le
                # confirme) mais il est listé pour vérification humaine ciblée.
                for nom_e, arts_e in etalons:
                    if nom_e == meilleur[2] or numero not in arts_e:
                        continue
                    if ocr.similarite(meilleur[1], arts_e[numero]) >= ocr.QUALITE_MINIMALE:
                        paires = nombres_substitues(meilleur[1], arts_e[numero])
                        if paires:
                            nombres_contestes.setdefault(numero, []).append(
                                {"lecture": nom_e.split(":")[0] + ":" + nom_e.split(":")[1][:40] if ":" in nom_e else nom_e,
                                 "ecarts": paires[:6]})
            else:
                ecartes.append((numero, None))
                if divergence:
                    nombres_divergents.append(numero)
        articles = retenus
    else:
        articles = dict(lectures[0][2])   # une seule lecture : pas de complément non vérifié
    return {"articles": articles, "confiance": confiance, "ecartes": ecartes, "principal": principal,
            "principal_brut": next((t for nom, t in _textes_bruts(d, resultat) if nom == nom_principal), None),
            "nom_principal": nom_principal, "comparateur": comparateur, "copies": copies, "second": second,
            "corrections_en_tetes": corrections_en_tetes, "retraits": retraits,
            "hors_principale": sum(1 for n in articles if provenance.get(n) != nom_principal),
            "nombres_divergents": nombres_divergents, "nombres_contestes": nombres_contestes,
            "illisibles": illisibles,
            "provenance": provenance}


def officialiser_ocr(cles=None, lecture_unique=False):
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
        if (manifeste.get(d["cle"]) or {}).get("version_abrogee"):
            bilan.append((d["cle"], "IGNORE", "version abrogée : " + manifeste[d["cle"]]["version_abrogee"]["constat"]))
            continue
        motifs_bloquants = [m for m in d["motifs_quarantaine"] if not m.startswith("découpage en articles")]
        if motifs_bloquants or d["integrite_pdf"] != "OK":
            bilan.append((d["cle"], "IGNORE", "; ".join(motifs_bloquants) or d["integrite_pdf"]))
            continue
        domaine = DOMAINE_MOTEUR.get((d["domaines"] or [None])[0])
        if not domaine:
            bilan.append((d["cle"], "IGNORE", "aucun domaine du moteur"))
            continue
        prep = preparer_ocr(d, inventaire, manifeste)
        if prep is None:
            bilan.append((d["cle"], "IGNORE", "aucune lecture OCR exploitable"))
            continue
        if not prep["second"] and not lecture_unique:
            # Une seule lecture : aucun article ne serait confirmé par une autre. Refusé
            # depuis le 20/10/2026 (seconde lecture : bin/ocr_local.py --modele fast).
            bilan.append((d["cle"], "IGNORE", "une seule lecture du scan : seconde lecture requise"))
            continue
        articles, confiance, ecartes = prep["articles"], prep["confiance"], prep["ecartes"]
        # Couverture vérifiée AVANT toute écriture (base, fichiers, journal). Un refus
        # d'indexation après coup laissait une référence munie d'un extrait jamais
        # indexé, contre lequel une citation aurait pu être « vérifiée » (20/10/2026).
        taux_prevu, maximum_prevu = corpus.taux_couverture(articles)
        if not articles or taux_prevu < corpus.COUVERTURE_MINIMALE:
            bilan.append((d["cle"], "REFUSE", "couverture %.0f %% des articles 1..%s (minimum %.0f %%) : "
                          "rien n'est écrit" % (100 * taux_prevu, maximum_prevu, 100 * corpus.COUVERTURE_MINIMALE)))
            continue
        # Couverture vérifiée AVANT toute écriture : un refus d'indexation après coup
        # laissait une référence munie d'un extrait jamais indexé, contre lequel une
        # citation aurait pu être « vérifiée » (constaté le 20/10/2026).
        taux, maximum = corpus.taux_couverture(articles)
        if taux < corpus.COUVERTURE_MINIMALE:
            bilan.append((d["cle"], "REFUSE", "couverture %.0f %% des articles 1..%s (minimum %.0f %%) : rien n'est écrit"
                          % (100 * taux, maximum, 100 * corpus.COUVERTURE_MINIMALE)))
            continue
        principal, nom_principal, comparateur = prep["principal"], prep["nom_principal"], prep["comparateur"]
        copies, second = prep["copies"], prep["second"]
        corrections_en_tetes, retraits = prep["corrections_en_tetes"], prep["retraits"]
        dossier, _ = collecter_domaine.chemin_manifeste(domaine)
        os.makedirs(dossier, exist_ok=True)
        chemin_pdf = os.path.join(dossier, d["cle"] + ".pdf")
        shutil.copyfile(os.path.join(DOSSIER_PDF, d["cle"] + ".pdf"), chemin_pdf)
        chemin_ocr = os.path.join(dossier, d["cle"] + ".ocr.txt")
        with open(chemin_ocr, "w", encoding="utf-8") as flux:
            flux.write(principal or "")
        source = manifeste[d["cle"]]
        aujourd_hui = _dt.date.today().isoformat()
        lecture = "lecture principale %s (%d articles découpés)" % (nom_principal, len(articles) + len(ecartes))
        if comparateur:
            lecture += " ; chaque article retenu concorde à 0,80 au moins avec : %s" % comparateur
        if copies:
            lecture += " ; écarté(s) comme copie du même calque OCR : %s" % ", ".join(n for n, _ in copies)
        lecture += " ; %d en-tête(s), pied(s) ou numéro(s) de page retiré(s)" % retraits
        if corrections_en_tetes:
            lecture += (" ; %d en-tête(s) d'article mal lu(s) par l'OCR rétabli(s) au format « Art. N. — »"
                        " (corps des articles inchangé)" % len(corrections_en_tetes))
        ref_id = base.ajouter_reference(
            titre_officiel=source["titre"], type_texte=source["type_texte"],
            numero_texte=source.get("numero_texte"), date_publication=source.get("date_texte"),
            domaine=domaine, source_nom=source["autorite"], source_url=source["url"],
            date_consultation=aujourd_hui,
            # Même convention que la filiation (2019-571, OCR d'éditeur) : l'extrait
            # enregistré est le texte des articles RETENUS, pour que toute citation
            # soit vérifiée mot pour mot contre lui. L'état reste
            # PARTIELLEMENT_VERIFIE et l'origine OCR voyage avec chaque article.
            texte_complet_present=bool(articles),
            extrait_texte="\n\n".join("Article %s\n%s" % (n, articles[n])
                                        for n in sorted(articles, key=ocr._tri_numero)) or None,
            articles=("%d articles indexés (OCR)" % len(articles)) if articles else None,
            limites_interpretation=("Exemplaire officiel numérisé ; texte lu par %s. %s"
                                    % (lecture, source.get("notes") or "")).strip())
        extrait = "\n\n".join("Article %s\n%s" % (n, articles[n]) for n in sorted(articles, key=ocr._tri_numero))
        existante = base.obtenir_reference(ref_id)
        if existante and (existante.get("extrait_texte") or "") != extrait and existante["etat_verification"] != "VERIFIE":
            # Référence déjà créée pour CE document (souvent sans texte, scan non lu) :
            # son extrait devient celui des articles retenus, pour que les citations
            # restent vérifiables mot pour mot contre ce qui est indexé.
            base.completer_extrait_ocr(
                ref_id, extrait, ("%d articles indexés (OCR)" % len(articles)) if articles else None,
                source["url"], "texte lu par OCR le %s (%s)" % (aujourd_hui, lecture))
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
        journal = lire_json(JOURNAL_OCR, {"objet": ("Journal des intégrations OCR : lecture de chaque article, "
                                                       "articles écartés et nombres contestés à vérifier."),
                                             "integrations": {}})
        journal["integrations"][d["cle"]] = {
            "date": aujourd_hui, "ref_id": ref_id, "doc_id": doc_id, "numero_texte": d["numero_texte"],
            "lecture_principale": nom_principal, "etalons": comparateur,
            "copies_ecartees": [n for n, _ in copies], "articles_indexes": indexation["articles_indexes"],
            "couverture": indexation["couverture"], "accord_moyen": moyenne,
            "articles_ecartes": [{"numero": n, "similarite": v} for n, v in ecartes],
            "nombres_divergents_ecartes": prep["nombres_divergents"],
            "illisibles_ecartes": prep["illisibles"],
            "nombres_contestes_a_verifier": prep["nombres_contestes"],
            "lecture_par_article": {n: prep["provenance"].get(n) for n in sorted(articles, key=ocr._tri_numero)}}
        ecrire_json(JOURNAL_OCR, journal)
        bilan.append((d["cle"], "INTEGRE", "%d articles (couverture %.0f %%), %d écartés%s" % (
            indexation["articles_indexes"], 100 * indexation["couverture"], len(ecartes),
            ", accord moyen %s" % moyenne if moyenne else "")))
    for ligne in bilan:
        print("%-46s %-8s %s" % ligne)
    return bilan


def lecture_partielle(cles):
    """Document REFUSÉ à l'intégration (couverture < seuil) : écrit, article par article,
    ce qui est fiable et ce qui est exclu, avec la page du scan. Rien n'est indexé ni
    citable ; le texte source et les lectures restent dans KNOWLEDGE/collecte/textes/."""
    inventaire = lire_json(INVENTAIRE)
    manifeste = {s["cle"]: s for s in lire_json(MANIFESTE)["sources"]}
    dossier = os.path.join(DOSSIER, "lectures_partielles")
    os.makedirs(dossier, exist_ok=True)
    for d in inventaire["documents"]:
        if d["cle"] not in cles:
            continue
        prep = preparer_ocr(d, inventaire, manifeste)
        taux, maximum = corpus.taux_couverture(prep["articles"])
        # page de chaque article dans la lecture principale (marqueurs « --- PAGE n --- »)
        pages, page = {}, None
        for ligne in ocr.normaliser_en_tetes_jo(prep["principal_brut"] or "")[0].splitlines():
            m = re.match(r"^--- PAGE (\d+) ---", ligne)
            if m:
                page = int(m.group(1))
                continue
            m = re.match(r"^[ \t]*Art(?:icle)?\.?[ \t]+(\d{1,4})", ligne)
            if m and m.group(1) not in pages:
                pages[m.group(1)] = page
        ecartes = dict(prep["ecartes"])
        statuts = {}
        for n in range(1, (maximum or 0) + 1):
            numero = str(n)
            if numero in prep["articles"]:
                statut = "FIABLE_NON_INDEXE"
            elif numero in prep["illisibles"]:
                statut = "ILLISIBLE"
            elif numero in prep["nombres_divergents"]:
                statut = "NOMBRE_DIVERGENT"
            elif numero in ecartes:
                statut = "NON_CONFIRME"
            else:
                statut = "NON_LU"
            entree = {"statut": statut, "page": pages.get(numero)}
            if statut == "FIABLE_NON_INDEXE":
                entree["sha256_texte"] = corpus.empreinte_texte(prep["articles"][numero])
                entree["accord"] = (prep["confiance"] or {}).get(numero)
            statuts[numero] = entree
        compte = collections.Counter(e["statut"] for e in statuts.values())
        par_page = collections.defaultdict(collections.Counter)
        for e in statuts.values():
            par_page[e["page"]][e["statut"]] += 1
        degradees = sorted(p for p, c in par_page.items()
                           if p and (c["ILLISIBLE"] + c["NON_CONFIRME"] + c["NON_LU"]) >= max(2, sum(c.values()) // 2))
        rapport = {
            "objet": ("Lecture partielle d'un exemplaire officiel REFUSÉ à l'intégration : aucun article n'est indexé "
                      "ni citable. Sert à documenter les passages dégradés et à préparer une nouvelle lecture."),
            "cle": d["cle"], "numero_texte": d["numero_texte"], "titre": d["titre"], "url": d["url"],
            "sha256_pdf": d["sha256"], "date": datetime.date.today().isoformat(),
            "lecture_principale": prep["nom_principal"], "etalons": prep["comparateur"],
            "couverture_fiable": round(taux, 4), "seuil_integration": corpus.COUVERTURE_MINIMALE,
            "decision": "NON_INTEGRE : couverture fiable inférieure au seuil",
            "comptes": dict(sorted(compte.items())), "pages_degradees": degradees,
            "textes_sources": sorted(os.path.relpath(p, RACINE) for p in __import__("glob").glob(
                os.path.join(DOSSIER, "textes", d["cle"] + ".*"))),
            "articles": statuts,
        }
        chemin = os.path.join(dossier, d["cle"] + ".json")
        ecrire_json(chemin, rapport)
        print("%s : %s ; pages dégradées %s -> %s" % (d["cle"], dict(compte), degradees, os.path.relpath(chemin, RACINE)))


def mesurer(cles=None):
    """Ce qu'une intégration OCR retiendrait, document par document — rien n'est écrit."""
    inventaire = lire_json(INVENTAIRE)
    manifeste = {s["cle"]: s for s in lire_json(MANIFESTE)["sources"]}
    mesures = []
    for d in inventaire["documents"]:
        if (cles and d["cle"] not in cles) or not d["methode_extraction"].startswith("OCR"):
            continue
        if (manifeste.get(d["cle"]) or {}).get("version_abrogee"):
            print("%-44s VERSION ABROGÉE — non intégrable" % d["cle"][:44])
            continue
        prep = preparer_ocr(d, inventaire, manifeste)
        if prep is None:
            continue
        taux, maximum = corpus.taux_couverture(prep["articles"])
        moyenne = (round(sum(prep["confiance"].values()) / len(prep["confiance"]), 4)
                   if prep["confiance"] else None)
        mesures.append({"cle": d["cle"], "numero_texte": d["numero_texte"], "statut_controle": d["statut_controle"],
                        "lecture_principale": prep["nom_principal"], "etalons": prep["comparateur"],
                        "copies_ecartees": [n for n, _ in prep["copies"]],
                        "articles_retenus": len(prep["articles"]), "article_max": maximum,
                        "couverture": round(taux, 4), "ecartes": len(prep["ecartes"]), "accord_moyen": moyenne,
                        "nombres_divergents": prep["nombres_divergents"],
                        "nombres_contestes": prep["nombres_contestes"],
                        "illisibles": prep["illisibles"],
                        "integrable": taux >= corpus.COUVERTURE_MINIMALE})
        print("%-44s %-24s ret=%-4d couv=%.2f max=%-4s ec=%-3d nb≠=%-3d illis=%-3d contestés=%-3d accord=%s | %s" % (
            d["cle"][:44], prep["nom_principal"][:24], len(prep["articles"]), taux, maximum, len(prep["ecartes"]),
            len(prep["nombres_divergents"]), len(prep["illisibles"]), len(prep["nombres_contestes"]), moyenne, (prep["comparateur"] or "AUCUN ÉTALON")[:90]))
    return mesures


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("etape", choices=("pdf", "controler", "recouper", "officialiser", "officialiser_ocr", "mesurer",
                                                    "lecture_partielle"))
    analyseur.add_argument("--cle", action="append")
    arguments = analyseur.parse_args(argv)
    if arguments.etape == "officialiser":
        officialiser(arguments.cle)
    elif arguments.etape == "officialiser_ocr":
        officialiser_ocr(arguments.cle)
    elif arguments.etape == "mesurer":
        mesurer(arguments.cle)
    elif arguments.etape == "lecture_partielle":
        lecture_partielle(arguments.cle or [])
    else:
        {"pdf": rapatrier_pdf, "controler": controler, "recouper": recouper}[arguments.etape]()
    return 0


if __name__ == "__main__":
    sys.exit(main())
