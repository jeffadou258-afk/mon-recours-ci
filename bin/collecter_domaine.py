# -*- coding: utf-8 -*-
"""Collecte d'un domaine juridique a partir de son manifeste de sources.

Usage :
    python3 bin/collecter_domaine.py --domaine famille_mariage_filiation
    python3 bin/collecter_domaine.py --domaine famille_mariage_filiation --etat

Un manifeste vit a cote des documents du domaine :
    KNOWLEDGE/CORPUS/<DOSSIER>/_sources.json
Il enregistre, pour chaque document, ce qui a ETE VERIFIE au moment du
telechargement : titre officiel tel que publie par l'autorite, URL, nombre de
pages, presence ou non d'un calque texte, et les reserves eventuelles.

Regles tenues par ce script :

  * il ne modifie aucun document existant et ne supprime rien ;
  * un document sans calque texte n'est JAMAIS promu `VERIFIE` : il part en OCR
    (`bin/ocr_collecter.py`) ;
  * une compilation (`recueil`) ne produit AUCUNE reference et AUCUN article :
    on ne peut pas rattacher une disposition tiree d'un recueil a son texte
    d'origine avec certitude, donc on ne le fait pas ;
  * l'empreinte SHA-256 est recalculee sur le fichier local, jamais reprise de
    la source ;
  * le nombre de pages annonce par la source est compare au PDF reel.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from config import (  # noqa: E402
    CHEMIN_DB, COUVERTURE_DOMAINES, DOMAINES_JURIDIQUES,
)
from core import base, corpus, sources  # noqa: E402

AGENT_HTTP = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120 Safari/537.36")

CONDITIONS_ACCES = (
    "Document publie librement par une autorite publique. Empreinte SHA-256 calculee "
    "sur le fichier telecharge ; l'usage et la citation restent soumis au droit commun."
)

# Un texte n'est indexable que s'il est SUBSTANTIEL. En dessous, il est conserve
# pour la lecture humaine mais n'alimente aucun article : quelques lignes de
# sommaire ne font pas un texte de loi.
SEUIL_CARACTERES_TEXTE = 800       # total, pour le document entier
SEUIL_CARACTERES_PAR_PAGE = 150    # densite minimale par page declaree

DOSSIERS_PAR_DOMAINE = {
    "logement_baux_foncier": "LOGEMENT_BAUX_FONCIER",
    "famille_mariage_filiation": "FAMILLE_ENFANTS",
    "travail": "TRAVAIL",
    "contrats_dettes_commerce": "ENTREPRISES_COMMERCE",
    "consommation": "DETTES_CONSOMMATION",
    "administratif_voies_de_recours": "ADMINISTRATION",
    "penal_procedure_penale": "PENAL_PROCEDURE",
    "associations_organisations_religieuses": "ASSOCIATIONS",
    "donnees_personnelles_numerique": "NUMERIQUE_DONNEES",
    "transport_responsabilite_civile": "TRANSPORT",
    "sante_droits_usagers": "SANTE",
}


def chemin_manifeste(domaine):
    dossier = os.path.join(RACINE, "KNOWLEDGE", "CORPUS", DOSSIERS_PAR_DOMAINE[domaine])
    return dossier, os.path.join(dossier, "_sources.json")


def journaliser(message):
    print("   " + message)


def telecharger(url, destination, timeout=180):
    """Telecharge et renvoie (octets, sha256). Ne remplace jamais un fichier lu."""
    requete = urllib.request.Request(url, headers={"User-Agent": AGENT_HTTP})
    with urllib.request.urlopen(requete, timeout=timeout) as reponse:
        contenu = reponse.read()
    with open(destination, "wb") as flux:
        flux.write(contenu)
    return contenu, "sha256:" + hashlib.sha256(contenu).hexdigest()


def detecter_calque_texte(chemin):
    """Compte les polices et les images : zero police = aucun texte extractible."""
    with open(chemin, "rb") as flux:
        donnees = flux.read()
    return {
        "polices": len(re.findall(rb"/Type\s*/Font", donnees)),
        "images": len(re.findall(rb"/Subtype\s*/Image", donnees)),
        "pages_detectees": len(re.findall(rb"/Type\s*/Page[^s]", donnees)),
    }


def extraire_texte_pdf(chemin):
    """Extraction via pypdf (venv de collecte). Jamais utilisee par le runtime."""
    from pypdf import PdfReader  # import local : dependance de collecte uniquement
    lecteur = PdfReader(chemin)
    pages = []
    for page in lecteur.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception as erreur:  # noqa: BLE001 — une page illisible ne bloque pas le reste
            pages.append("")
            journaliser("page illisible ignoree : %s" % (erreur,))
    return "\n\f\n".join(pages), len(lecteur.pages)


def collecter(domaine, telecharger_si_absent=True, chemin_db=None):
    chemin_db = chemin_db or str(CHEMIN_DB)
    dossier, manifeste_path = chemin_manifeste(domaine)
    if not os.path.isfile(manifeste_path):
        raise SystemExit("manifeste absent : %s" % manifeste_path)
    manifeste = json.load(open(manifeste_path, encoding="utf-8"))
    corpus.initialiser(chemin_db)
    os.makedirs(dossier, exist_ok=True)
    rapport = {"horodatage": corpus.horodatage(), "domaine": domaine,
               "documents": [], "non_juridiques": [], "echecs": []}

    for source in manifeste["sources"]:
        print("-" * 74)
        journaliser("%s — %s" % (source["type_texte"].upper(),
                                 source["titre"][:70]))
        chemin_pdf = os.path.join(dossier, source["fichier"])
        est_juridique = source.get("reference", True)
        entree = {"cle": source["cle"], "titre": source["titre"], "url": source["url"],
                  "numero_texte": source.get("numero_texte"), "statut": None}

        try:
            if os.path.isfile(chemin_pdf):
                with open(chemin_pdf, "rb") as flux:
                    contenu = flux.read()
                sha = "sha256:" + hashlib.sha256(contenu).hexdigest()
                journaliser("fichier local reutilise (%d octets)" % len(contenu))
            elif telecharger_si_absent:
                contenu, sha = telecharger(source["url"], chemin_pdf)
                journaliser("telecharge : %d octets" % len(contenu))
            else:
                raise FileNotFoundError("fichier absent et telechargement desactive")
        except Exception as erreur:  # noqa: BLE001
            journaliser("ECHEC du telechargement : %s" % (erreur,))
            entree["statut"] = "ECHEC_TELECHARGEMENT"
            entree["erreur"] = str(erreur)
            rapport["echecs"].append(entree)
            continue

        entree["sha256"] = sha
        if not contenu.startswith(b"%PDF"):
            journaliser("ce n'est pas un PDF : ecarte")
            entree["statut"] = "NON_PDF"
            rapport["echecs"].append(entree)
            continue

        detection = detecter_calque_texte(chemin_pdf)
        entree["detection"] = detection
        journaliser("polices=%d images=%d pages~%d"
                    % (detection["polices"], detection["images"],
                       detection["pages_detectees"]))
        if detection["polices"] == 0:
            entree["sha256_ocr"] = sha
        if (source.get("pages") and detection["pages_detectees"]
                and source["pages"] != detection["pages_detectees"]):
            entree["ecart_pages"] = "annonce=%s detecte=%s" % (
                source["pages"], detection["pages_detectees"])

        fichier_texte, texte, articles = None, None, {}
        motif_non_indexe = None
        # Le texte est extrait des qu'il existe un calque texte — y compris pour
        # une compilation, dont le texte reste consultable a la main. Ce qui
        # change, c'est l'INDEXATION : une compilation ne produit aucun article,
        # car on ne peut pas rattacher une disposition tiree d'un recueil a son
        # texte d'origine avec certitude.
        indexer_articles = (est_juridique and source["type_texte"] != "recueil")
        # On TENTE l'extraction meme si le document ne declare aucune police :
        # mesure sur le corpus, un PDF sans /Type/Font peut rendre du texte
        # exploitable (Journal officiel OHADA n°22 : table des matieres lisible
        # alors que le compte de polices vaut zero). Le compte de polices reste
        # un INDICATEUR dans le rapport, il ne decide plus seul.
        chemin_txt = os.path.join(dossier, source["cle"] + ".txt")
        if os.path.isfile(chemin_txt):
            texte = open(chemin_txt, encoding="utf-8").read()
            journaliser("texte deja extrait (reutilise)")
        else:
            pages_reelles = 0
            try:
                texte, pages_reelles = extraire_texte_pdf(chemin_pdf)
            except Exception as erreur:  # noqa: BLE001 — dependance de collecte absente
                texte = None
                journaliser("extraction impossible : %s" % (erreur,))
            if texte is not None and not texte.strip():
                texte = None
            if texte:
                densite = len(texte) / float(max(1, pages_reelles))
                entree["extraction"] = {"caracteres": len(texte), "pages": pages_reelles,
                                        "densite_car_par_page": round(densite, 1),
                                        "polices_declarees": detection["polices"]}
                open(chemin_txt, "w", encoding="utf-8").write(texte)
                journaliser("texte extrait : %d caracteres sur %d pages (%.0f car./page)"
                            % (len(texte), pages_reelles, densite))
            else:
                journaliser("aucun texte extractible : OCR requis")

        # Un texte n'est « presente » que s'il est SUBSTANTIEL : quelques lignes
        # de sommaire ne font pas un texte de loi indexable. En dessous du seuil,
        # le texte partiel est conserve pour la lecture humaine et l'OCR prend le
        # relais — sans jamais effacer ce qui a ete lu.
        pages_declarees = max(1, int(source.get("pages") or 0) or 1)
        substantiel = bool(texte) and len(texte) >= SEUIL_CARACTERES_TEXTE and \
            (len(texte) / float(pages_declarees)) >= SEUIL_CARACTERES_PAR_PAGE
        if texte:
            fichier_texte = chemin_txt
            entree["texte_substantiel"] = bool(substantiel)
        if substantiel and indexer_articles:
            detectes = corpus.extraire_articles(texte)
            if not detectes:
                journaliser("aucun article detecte dans le calque texte")
            else:
                taux, maximum = corpus.taux_couverture(detectes)
                entree["articles_detectes"] = {
                    "nb": len(detectes), "article_max": maximum,
                    "couverture": round(taux, 4)}
                if taux < corpus.COUVERTURE_MINIMALE:
                    # Le decoupage en articles n'est PAS fiable : une loi
                    # modificative renvoie aux articles d'autres codes, un
                    # extrait ne contient qu'une partie du texte. On
                    # n'indexe alors RIEN et on ne promeut pas la
                    # reference en VERIFIE — c'est la regle du projet :
                    # un texte dont on ne sait pas enumerer les articles
                    # ne peut pas soutenir une citation.
                    motif_non_indexe = (
                        "decoupage en articles non fiable : %d article(s) "
                        "detecte(s) sur la plage 1..%d (%.0f%%), seuil du "
                        "projet %.0f%%" % (len(detectes), maximum, 100 * taux,
                                           100 * corpus.COUVERTURE_MINIMALE))
                    journaliser("NON INDEXE — %s" % motif_non_indexe)
                    articles = {}
                else:
                    articles = detectes
                    journaliser("articles : %d indexables (couverture %.0f%% "
                                "des 1..%d)" % (len(detectes), 100 * taux, maximum))
        elif indexer_articles:
            journaliser("texte non substantiel ou absent : indexation impossible, "
                        "OCR requis")
        elif source["type_texte"] == "recueil":
            journaliser("compilation : texte conserve, AUCUNE reference et "
                        "AUCUN article indexe")

        # Une reproduction d'un editeur tiers — declaree dans le manifeste ou
        # detectee dans le texte — ne peut PAS porter VERIFIE : le contenu peut
        # etre exact, la source n'est pas le document officiel. Un texte publie
        # par une autorite peut n'etre qu'un hebergement d'une copie editee
        # ailleurs, et le dire est plus important que de compter un texte de plus.
        contaminants = corpus.textes_contaminants(texte) if texte else []
        source_secondaire = source.get("source_secondaire")
        if contaminants and not source_secondaire:
            source_secondaire = ("marques d'editeur tiers detectees dans le texte : %s"
                                 % ", ".join(contaminants))
        if source_secondaire:
            entree["source_secondaire"] = source_secondaire
            journaliser("REPRODUCTION TIERCE — ne sera pas promu VERIFIE : %s"
                        % source_secondaire)

        ref_id = None
        if est_juridique:
            ref_id = base.ajouter_reference(
                titre_officiel=source["titre"],
                type_texte=source["type_texte"],
                numero_texte=source.get("numero_texte"),
                date_publication=source.get("date_texte"),
                articles=("1 a %d" % max(int(n) for n in articles if str(n).isdigit()))
                if articles else None,
                domaine=domaine,
                source_nom=source["autorite"],
                source_url=source["url"],
                date_consultation=datetime.date.today().isoformat(),
                extrait_texte=texte if articles else None,
                texte_complet_present=bool(articles),
                limites_interpretation=source.get("limites"),
                chemin=chemin_db,
            )
            if articles and not source_secondaire:
                base.promouvoir_verification(
                    ref_id, "VERIFIE", preuve_url=source["url"], preuve_empreinte=sha,
                    date_consultation=datetime.date.today().isoformat(),
                    motif="PDF officiel telecharge, empreinte recalculee, texte lu",
                    chemin=chemin_db)
                entree["etat_verification"] = "VERIFIE"
            else:
                base.promouvoir_verification(
                    ref_id, "PARTIELLEMENT_VERIFIE", preuve_url=source["url"],
                    preuve_empreinte=sha,
                    date_consultation=datetime.date.today().isoformat(),
                    motif=(motif_non_indexe or source_secondaire or
                           "exemplaire officiel telecharge mais sans calque texte : "
                           "non exploitable avant OCR"),
                    chemin=chemin_db)
                entree["etat_verification"] = "PARTIELLEMENT_VERIFIE"
                if motif_non_indexe:
                    entree["motif_non_indexe"] = motif_non_indexe
            entree["ref_id"] = ref_id

        doc_id = corpus.importer_document(
            ref_id=ref_id,
            titre=source["titre"],
            type_texte=source["type_texte"],
            numero_texte=source.get("numero_texte"),
            date_texte=source.get("date_texte"),
            domaine=domaine,
            autorite=source["autorite"],
            url_source=source["url"],
            chemin_local=chemin_pdf,
            licence_conditions=source.get("attribution") or CONDITIONS_ACCES,
            pages=source.get("pages"),
            calque_texte=bool(fichier_texte and substantiel),
            fichier_texte=fichier_texte,
            sha256_declare=sha,
            note_qualite=("texte natif exploitable" if articles else
                          ("texte extrait mais decoupage en articles non fiable : "
                           "non indexe" if motif_non_indexe else
                           ("compilation : texte conserve, non indexe"
                            if source["type_texte"] == "recueil"
                            else "scan sans calque texte — OCR requis"))),
            methode_extraction=("TEXTE_DE_COMPILATION" if source["type_texte"] == "recueil"
                                else None),
            actualiser=True,
            chemin=chemin_db,
        )
        entree["doc_id"] = doc_id
        if articles:
            # `remplacer=True` : une extraction fraiche du meme document fait
            # autorite. Sans cela, une correction du nettoyage de texte
            # (artefacts d'editeur, ponctuation) ne pourrait jamais atteindre les
            # articles deja indexes — l'erreur resterait figee en base.
            resultat = corpus.enregistrer_articles(ref_id, doc_id, articles,
                                                   remplacer=True, chemin=chemin_db)
            entree["articles_indexes"] = resultat["articles_indexes"]
        else:
            entree["articles_indexes"] = 0
        entree["statut"] = "IMPORTE"
        (rapport["documents"] if est_juridique else rapport["non_juridiques"]).append(entree)

    return rapport


def afficher_etat(domaine, chemin_db=None):
    chemin_db = chemin_db or str(CHEMIN_DB)
    corpus.initialiser(chemin_db)
    print("=" * 74)
    print("ETAT DU DOMAINE : %s" % domaine)
    print("=" * 74)
    documents = corpus.lister_documents(domaine=domaine)
    if not documents:
        print("  aucun document collecte pour ce domaine")
    for document in documents:
        n = len(corpus.articles_dun_document(document["doc_id"]))
        print("  %-14s %-11s %-20s art=%-4s %s"
              % (document["doc_id"], document["numero_texte"] or "-",
                 document["methode_extraction"], n, document["titre"][:44]))
    compte = corpus.articles_par_origine()
    print("\n  articles indexes (toutes provenances) : %s"
          % sum(v["articles"] for v in compte.values()))
    for origine, valeurs in sorted(compte.items()):
        print("    %-24s %s" % (origine, valeurs["articles"]))


def main(argv=None):
    analyseur = argparse.ArgumentParser(description="Collecte un domaine juridique")
    analyseur.add_argument("--domaine", required=True, choices=sorted(DOSSIERS_PAR_DOMAINE))
    analyseur.add_argument("--etat", action="store_true", help="affiche l'etat, sans reseau")
    analyseur.add_argument("--sans-telecharger", action="store_true",
                           help="reutilise uniquement les fichiers deja presents")
    arguments = analyseur.parse_args(argv)

    if arguments.etat:
        afficher_etat(arguments.domaine)
        return 0

    rapport = collecter(arguments.domaine,
                        telecharger_si_absent=not arguments.sans_telecharger)
    print("\n" + "=" * 74)
    print("SYNTHESE : %s" % arguments.domaine)
    print("=" * 74)
    print("  Documents importes : %d" % len(rapport["documents"]))
    print("  Documents non juridiques : %d" % len(rapport["non_juridiques"]))
    print("  Echecs : %d" % len(rapport["echecs"]))
    for echec in rapport["echecs"]:
        print("    - %s : %s" % (echec["titre"][:52], echec.get("erreur", echec["statut"])))
    total = sum(d.get("articles_indexes", 0) for d in rapport["documents"])
    print("  Articles indexes : %d" % total)
    integrite = corpus.verifier_integrite()
    print("  Integrite : %s" % integrite["verdict"])
    return 0 if not rapport["echecs"] else 1


if __name__ == "__main__":
    sys.exit(main())
