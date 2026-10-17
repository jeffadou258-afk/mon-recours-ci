#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collecteur du corpus LOGEMENT, BAUX ET FONCIER (Côte d'Ivoire).

Ce script est le SEUL point d'entrée qui télécharge et qui exige `pypdf`.
Il s'exécute avec le venv de collecte, jamais avec le runtime de l'agent :

    cd /Users/mac/mon_recours_ci
    ./.venv-corpus/bin/python bin/collecter_corpus.py            # collecte complète
    ./.venv-corpus/bin/python bin/collecter_corpus.py --etat     # lit l'état, ne télécharge rien

Ce qu'il fait, dans l'ordre, pour chaque source déclarée :

  1. télécharge le PDF vers KNOWLEDGE/CORPUS/<domaine>/ ;
  2. recalcule le SHA-256 et compare à l'empreinte constatée au premier accès ;
  3. détecte la présence d'un calque texte (objets /Type/Font dans le PDF) ;
  4. si le calque existe : extrait le texte, le stocke en .txt, indexe les
     articles ; sinon il DÉCLARE le document comme scan non exploitable ;
  5. enregistre la référence juridique (core.base) avec ses métadonnées et sa
     preuve, puis promeut l'état à VERIFIE ;
  6. enregistre le document et ses articles (core.corpus).

Aucune source n'est inventée : la liste est explicite, chaque URL a été
constatée accessible par HTTP 200 avant d'être écrite ici.
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from config import KNOWLEDGE_DIR, USER_AGENT  # noqa: E402
from core import base, corpus  # noqa: E402

DOMAINE = "logement_baux_foncier"
DOSSIER_CORPUS = KNOWLEDGE_DIR / "CORPUS" / "LOGEMENT_BAUX_FONCIER"

CONDITIONS_ACCES = (
    "Publication officielle librement téléchargeable depuis un domaine public "
    "ivoirien (*.gouv.ci). Consultation et conservation à des fins "
    "d'information juridique citoyenne. L'usage commercial et la "
    "redistribution ne sont pas revendiqués par l'agent : seules les "
    "références et extraits nécessaires à la réponse sont reproduits."
)

# Sources constatées accessibles (HTTP 200) le 2026-10-16.
SOURCES = (
    {
        "cle": "loi_2019_576",
        "titre": "LOI N° 2019-576 DU 26 JUIN 2019 INSTITUANT CODE DE LA CONSTRUCTION ET DE L'HABITAT",
        "titre_court": "Code de la Construction et de l'Habitat",
        "type_texte": "loi",
        "numero_texte": "2019-576",
        "date_texte": "2019-06-26",
        "autorite": "DGI — Direction Générale des Impôts (republication officielle)",
        "url": ("https://www.dgi.gouv.ci/assets/documents/transfert_propriete/lois_reglements/"
                "LOI%20N%C2%B0%202019-576%20DU%2026%20JUIN%202019%20INSTITUANT%20CODE%20DE%20LA%20"
                "CONSTRUCTION%20ET%20DE%20L%27HABITAT.pdf"),
        "fichier": "loi_2019-576_code_construction_habitat.pdf",
        "pages": 117,
    },
    {
        "cle": "loi_2020_624",
        "titre": ("LOI N° 2020-624 DU 14 AOÛT 2020 INSTITUANT CODE DE L'URBANISME "
                  "ET DU DOMAINE FONCIER URBAIN"),
        "titre_court": "Code de l'Urbanisme et du Domaine Foncier Urbain",
        "type_texte": "loi",
        "numero_texte": "2020-624",
        "date_texte": "2020-08-14",
        "autorite": "Ministère de l'Urbanisme, du Logement et du Cadre de Vie",
        "url": "https://www.construction.gouv.ci/uploads/publications/178542377022.pdf",
        "fichier": "loi_2020-624_code_urbanisme_domaine_foncier_urbain.pdf",
        "pages": 66,
    },
    {
        "cle": "loi_2020_624_dgi_scan",
        "titre": ("LOI N° 2020-624 DU 14 AOÛT 2020 INSTITUANT CODE DE L'URBANISME ET DU "
                  "DOMAINE FONCIER URBAIN (exemplaire numérisé DGI)"),
        "titre_court": "Code de l'Urbanisme (exemplaire numérisé DGI)",
        "type_texte": "loi",
        "numero_texte": "2020-624",
        "date_texte": "2020-08-14",
        "autorite": "DGI — Direction Générale des Impôts (exemplaire numérisé)",
        "url": ("https://www.dgi.gouv.ci/assets/documents/transfert_propriete/lois_reglements/"
                "LOI%20INSTITUANT%20CODE%20URBANISME%20ET%20DOMAINE%20FONCIER%20URBAIN-4-45.pdf"),
        "fichier": "loi_2020-624_dgi_exemplaire_numerise.pdf",
        "pages": 42,
        "sans_texte_attendu": True,
    },
    {
        "cle": "loi_98_750",
        "titre": ("LOI N° 98-750 DU 23 DECEMBRE 1998 RELATIVE AU DOMAINE FONCIER RURAL "
                  "(exemplaire numérisé SGG)"),
        "titre_court": "Loi relative au domaine foncier rural",
        "type_texte": "loi",
        "numero_texte": "98-750",
        "date_texte": "1998-12-23",
        "autorite": "Secrétariat Général du Gouvernement (photo_doc)",
        "url": "https://www.sgg.gouv.ci/photo_doc/1339597849.pdf",
        "fichier": "loi_98-750_domaine_foncier_rural_scan.pdf",
        "pages": 13,
        "sans_texte_attendu": True,
    },
    {
        "cle": "loi_2020_623",
        "titre": ("LOI N° 2020-623 DU 14 AOUT 2020 PORTANT RATIFICATION DE L'ORDONNANCE "
                  "N° 2020-386 DU 15 AVRIL 2020 PORTANT SUSPENSION DES PROCEDURES "
                  "D'EXPULSION DES LOCATAIRES ET DE REVISION A LA HAUSSE DU LOYER DES BAUX "
                  "D'HABITATION"),
        "titre_court": "Loi de ratification — suspension des expulsions (2020)",
        "type_texte": "loi",
        "numero_texte": "2020-623",
        "date_texte": "2020-08-14",
        "autorite": "Ministère de l'Urbanisme, du Logement et du Cadre de Vie",
        "url": "https://construction.gouv.ci/uploads/publications/178542265442.pdf",
        "fichier": "loi_2020-623_ratification_suspension_expulsions.pdf",
        "pages": 2,
        "sans_texte_attendu": True,
        "limites": ("Loi de ratification d'une ordonnance de suspension TEMPORAIRE des "
                    "procédures d'expulsion et de révision à la hausse des loyers, prise dans "
                    "le contexte de la covid-19 (période du 1er avril au 30 juin 2020). "
                    "La portée actuelle de cette mesure temporaire doit être vérifiée : ne pas "
                    "la présenter comme une règle permanente."),
    },
)

# Documents NON juridiques : ils documentent le contexte, jamais le droit applicable.
# Aucune référence juridique n'est créée pour eux, aucun article n'est indexé.
DOCUMENTS_NON_JURIDIQUES = (
    {
        "cle": "communique_2024_projet_loi_bail",
        "titre": ("COMMUNIQUE DU CONSEIL DES MINISTRES DU 12 JUIN 2024 — Porte-parolat du "
                  "Gouvernement (contient la présentation du projet de loi relatif au "
                  "contentieux du bail à usage d'habitation et à l'exécution des expulsions)"),
        "titre_court": "Communiqué du Conseil des ministres du 12/06/2024",
        "type_texte": "communique",
        "numero_texte": None,
        "date_texte": "2024-06-12",
        "autorite": "Porte-parolat du Gouvernement (communication.gouv.ci)",
        "url": "https://communication.gouv.ci/uploads/publications/17204739632.pdf",
        "fichier": "communique_conseil_ministres_projet_loi_bail_2024.pdf",
        "pages": 15,
        "reference": False,
    },
)


def journaliser(message):
    print("  " + message, flush=True)


def telecharger(url, destination, timeout=120):
    """Téléchargement réel. Ne lève pas : retourne (ok, code, erreur)."""
    requete = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT,
        "Accept": "application/pdf,*/*;q=0.8",
    })
    try:
        with urllib.request.urlopen(requete, timeout=timeout) as reponse:
            code = reponse.getcode()
            donnees = reponse.read()
            if code != 200:
                return False, code, "HTTP %s" % code
        with open(destination, "wb") as f:
            f.write(donnees)
        return True, code, None
    except urllib.error.HTTPError as e:
        return False, e.code, "HTTPError %s : %s" % (e.code, e.reason)
    except Exception as e:  # noqa: BLE001 — l'échec est rapporté, pas masqué
        return False, None, "%s : %s" % (type(e).__name__, e)


def detecter_calque_texte(chemin):
    """Détecte un calque texte par la présence d'objets /Type/Font dans le PDF.

    C'est la mesure qui distingue un PDF natif d'un scan : un scan n'a que des
    images et aucune police embarquée.
    """
    with open(chemin, "rb") as f:
        donnees = f.read()
    polices = len(re.findall(rb"/Type\s*/Font", donnees))
    images = len(re.findall(rb"/Subtype\s*/Image", donnees))
    pages = len(re.findall(rb"/Type\s*/Page[^s]", donnees))
    return {"polices": polices, "images": images, "pages_detectees": pages,
            "calque_texte": polices > 0}


def extraire_texte_pdf(chemin):
    """Extraction via pypdf (venv de collecte uniquement)."""
    from pypdf import PdfReader  # import local : le runtime n'a pas besoin de pypdf
    lecteur = PdfReader(chemin)
    pages = [(page.extract_text() or "") for page in lecteur.pages]
    return "\n\f\n".join(pages), len(pages)


def collecter(chemin_db=None, severite_sha=None, telecharger_si_absent=True):
    """Collecte complète. Retourne un rapport détaillé, y compris les échecs."""
    corpus.initialiser(chemin_db)
    os.makedirs(str(DOSSIER_CORPUS), exist_ok=True)
    rapport = {"horodatage": corpus.horodatage(), "domaine": DOMAINE,
               "documents": [], "non_juridiques": [], "echecs": []}

    for source in SOURCES + DOCUMENTS_NON_JURIDIQUES:
        entree = {"cle": source["cle"], "titre": source["titre"], "url": source["url"],
                  "numero_texte": source["numero_texte"], "statut": None}
        est_juridique = source.get("reference", True)
        chemin_pdf = str(DOSSIER_CORPUS / source["fichier"])
        journaliser("=== %s" % source["titre_court"])

        if not os.path.isfile(chemin_pdf) and telecharger_si_absent:
            ok, code, erreur = telecharger(source["url"], chemin_pdf)
            if not ok:
                journaliser("TÉLÉCHARGEMENT ÉCHOUÉ (%s) : %s" % (code, erreur))
                entree.update(statut="TELECHARGEMENT_ECHOUE", http=code, erreur=erreur)
                rapport["echecs"].append(entree)
                rapport["documents"].append(entree)
                continue
            journaliser("téléchargé : %s (%d o, HTTP %s)"
                        % (source["fichier"], os.path.getsize(chemin_pdf), code))
        elif not os.path.isfile(chemin_pdf):
            entree.update(statut="FICHIER_ABSENT")
            rapport["echecs"].append(entree)
            rapport["documents"].append(entree)
            continue
        else:
            journaliser("déjà présent localement (pas de nouveau téléchargement)")

        sha = corpus.empreinte_fichier(chemin_pdf)
        entree["sha256"] = sha
        entree["octets"] = os.path.getsize(chemin_pdf)
        journaliser("sha256 = %s" % sha)

        detection = detecter_calque_texte(chemin_pdf)
        entree["detection"] = detection
        journaliser("calque texte : %s (polices=%d, images=%d)"
                    % ("OUI" if detection["calque_texte"] else "NON",
                       detection["polices"], detection["images"]))

        fichier_texte = None
        texte = None
        articles = {}
        if detection["calque_texte"]:
            chemin_txt = str(DOSSIER_CORPUS / (source["fichier"].replace(".pdf", ".txt")))
            if not os.path.isfile(chemin_txt):
                texte, pages = extraire_texte_pdf(chemin_pdf)
                with open(chemin_txt, "w", encoding="utf-8") as f:
                    f.write(texte)
                journaliser("texte extrait : %s (%d car., %d pages)"
                            % (os.path.basename(chemin_txt), len(texte), pages))
            else:
                texte = open(chemin_txt, encoding="utf-8").read()
                journaliser("texte déjà extrait (réutilisé)")
            fichier_texte = chemin_txt
            articles = corpus.extraire_articles(texte) if est_juridique else {}
            if articles:
                taux, maximum = corpus.taux_couverture(articles)
                entree["articles"] = {"nb": len(articles), "article_max": maximum,
                                      "couverture": round(taux, 4)}
                journaliser("articles : %d indexables (couverture %.0f%% des 1..%d)"
                            % (len(articles), 100 * taux, maximum))
            elif est_juridique:
                journaliser("aucun article détecté dans le calque texte")
            else:
                journaliser("document non juridique : texte conservé, aucun article indexé")
        else:
            journaliser("PDF SANS CALQUE TEXTE : enregistré comme non exploitable "
                        "(OCR requis), aucune citation ne pourra s'y appuyer")

        # --- référence juridique (socle existant, inchangé) -----------------
        # Un document non juridique (communiqué, rapport) ne produit AUCUNE
        # référence : il documente le contexte, il ne dit pas le droit.
        ref_id = None
        if est_juridique:
            ref_id = base.ajouter_reference(
                titre_officiel=source["titre"],
                type_texte=source["type_texte"],
                numero_texte=source["numero_texte"],
                date_publication=source["date_texte"],
                articles=("1 à %d" % entree["articles"]["article_max"]) if articles else None,
                domaine=DOMAINE,
                source_nom=source["autorite"],
                source_url=source["url"],
                date_consultation=datetime.date.today().isoformat(),
                extrait_texte=texte if articles else None,
                texte_complet_present=bool(articles),
                limites_interpretation=source.get("limites") or (
                    "Texte lu dans un PDF officiel téléchargé. L'état de vigueur n'est "
                    "pas garanti au-delà de la date de consultation : vérifier les "
                    "modifications postérieures au Journal officiel."
                ),
                chemin=chemin_db,
            )
            if articles:
                base.promouvoir_verification(
                    ref_id, "VERIFIE",
                    preuve_url=source["url"], preuve_empreinte=sha,
                    date_consultation=datetime.date.today().isoformat(),
                    motif="PDF officiel téléchargé, empreinte recalculée, texte lu",
                    chemin=chemin_db,
                )
                entree["etat_verification"] = "VERIFIE"
            else:
                base.promouvoir_verification(
                    ref_id, "PARTIELLEMENT_VERIFIE",
                    preuve_url=source["url"], preuve_empreinte=sha,
                    date_consultation=datetime.date.today().isoformat(),
                    motif="exemplaire officiel téléchargé mais SANS calque texte : non exploitable",
                    chemin=chemin_db,
                )
                entree["etat_verification"] = "PARTIELLEMENT_VERIFIE"
            entree["ref_id"] = ref_id

        doc_id = corpus.importer_document(
            ref_id=ref_id,
            titre=source["titre"],
            type_texte=source["type_texte"],
            numero_texte=source["numero_texte"],
            date_texte=source["date_texte"],
            domaine=DOMAINE,
            autorite=source["autorite"],
            url_source=source["url"],
            chemin_local=chemin_pdf,
            licence_conditions=CONDITIONS_ACCES,
            pages=source["pages"],
            calque_texte=bool(articles) if est_juridique else bool(detection["calque_texte"]),
            fichier_texte=fichier_texte,
            sha256_declare=sha,
            note_qualite=("texte natif exploitable" if articles
                          else ("document non juridique (contexte)" if not est_juridique
                                else "scan sans calque texte — OCR requis")),
            methode_extraction=None if est_juridique else "TEXTE_NON_JURIDIQUE",
            chemin=chemin_db,
        )
        entree["doc_id"] = doc_id

        if articles and est_juridique:
            # Remplacer (et non ignorer) : une extraction fraiche du meme
            # document fait autorite, sinon une correction de normalisation ne
            # pourrait jamais atteindre les articles deja indexes.
            resultat = corpus.enregistrer_articles(ref_id, doc_id, articles,
                                                   remplacer=True, chemin=chemin_db)
            entree["articles_indexes"] = resultat["articles_indexes"]
            journaliser("indexés : %d articles" % resultat["articles_indexes"])
        else:
            entree["articles_indexes"] = 0

        entree["statut"] = "IMPORTE"
        if est_juridique:
            rapport["documents"].append(entree)
        else:
            rapport["non_juridiques"].append(entree)

    rapport["integrite"] = corpus.verifier_integrite(chemin=chemin_db)
    rapport["synthese"] = corpus.rapport(domaine=DOMAINE, chemin=chemin_db)
    return rapport


def afficher_etat(chemin_db=None):
    resume = corpus.rapport(domaine=DOMAINE, chemin=chemin_db)
    print("Domaine : %s" % resume["domaine"])
    print("Documents : %d (dont %d exploitables, %d scans seulement)"
          % (resume["nb_documents"], resume["nb_documents_exploitables"],
             resume["nb_documents_scans_seulement"]))
    print("Articles indexés : %d" % resume["nb_articles_indexes"])
    for doc in resume["documents"]:
        print("  [%s] %-58s %5d art. %s"
              % ("TEXTE" if doc["exploitable"] else "SCAN ",
                 doc["titre"][:58], doc["articles_indexes"], doc["note_qualite"]))
    integrite = corpus.verifier_integrite(chemin=chemin_db)
    print("Intégrité : %s (%d conformes, %d altérés, %d absents)"
          % (integrite["verdict"], len(integrite["conformes"]),
             len(integrite["alteres"]), len(integrite["absents"])))
    print("Références du corpus (core.base) :")
    for ref in base.lister_references(domaine=DOMAINE, chemin=chemin_db):
        print("  %s  %-12s %s" % (ref["ref_id"], ref["etat_verification"],
                                  ref["titre_officiel"][:70]))
    return resume


def main(argv=None):
    parseur = argparse.ArgumentParser(description="Collecte du corpus logement/baux/foncier.")
    parseur.add_argument("--etat", action="store_true", help="lire l'état sans rien télécharger")
    parseur.add_argument("--rapport", default=None, help="écrire le rapport JSON à ce chemin")
    arguments = parseur.parse_args(argv)

    if arguments.etat:
        afficher_etat()
        return 0

    rapport = collecter()
    print()
    print("=" * 74)
    print("SYNTHÈSE")
    print("=" * 74)
    print("Documents importés : %d" % len([d for d in rapport["documents"] if d["statut"] == "IMPORTE"]))
    print("Échecs             : %d" % len(rapport["echecs"]))
    print("Articles indexés   : %d" % rapport["synthese"]["nb_articles_indexes"])
    print("Intégrité          : %s" % rapport["integrite"]["verdict"])

    destination = arguments.rapport or str(KNOWLEDGE_DIR / "CORPUS" / "rapport_collecte.json")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    print("Rapport de collecte : %s" % destination)
    return 0 if not rapport["echecs"] else 2


if __name__ == "__main__":
    sys.exit(main())
