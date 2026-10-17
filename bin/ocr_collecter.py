#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collecte OCR des PDF scannés — environnement isolé, qualité mesurée.

Ce script est le SEUL point d'entrée qui compile et exécute l'outil OCR Swift.
Il ne touche ni au runtime de l'agent, ni à la configuration de Hermes.

    cd /Users/mac/mon_recours_ci
    python3 bin/ocr_collecter.py            # OCR + mesure + intégration
    python3 bin/ocr_collecter.py --etat     # état, sans rien exécuter

Ce qu'il fait, pour chaque document du domaine dépourvu de calque texte :

  1. compile `tools/ocr_pdf.swift` si le binaire manque ou si la source est plus
     récente (Vision + PDFKit, aucun accès réseau) ;
  2. exécute l'OCR page par page vers `<pdf>.ocr.txt` ;
  3. calcule l'empreinte SHA-256 du texte reconnu ;
  4. MESURE la qualité :
       - si une autre copie officielle du même texte existe (idéalement avec
         calque texte), compare article par article ;
       - sinon, applique les contrôles structurels ;
  5. n'intègre QUE les articles qui passent le seuil, en les marquant
     `origine_texte = 'OCR_AUTO'` avec leur confiance mesurée ;
  6. écrit un rapport, y compris les articles écartés et les divergences.

Invariant tenu : le PDF reste un scan (`calque_texte = 0`), la référence reste
`PARTIELLEMENT_VERIFIE`, et `texte_complet_present` reste à 0. Le texte reconnu
automatiquement n'est jamais présenté comme un texte vérifié.
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from config import KNOWLEDGE_DIR  # noqa: E402
from core import base, corpus, ocr  # noqa: E402

DOMAINE = "logement_baux_foncier"
DOSSIER_CORPUS = KNOWLEDGE_DIR / "CORPUS" / "LOGEMENT_BAUX_FONCIER"
SOURCE_SWIFT = os.path.join(RACINE, "tools", "ocr_pdf.swift")
BINAIRE_OCR = os.path.join(RACINE, "tools", "ocr_pdf")

# Dossiers par domaine : permet de traiter l'OCR d'un autre domaine sans
# toucher au comportement historique (sans --domaine, rien ne change).
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

# Chaînes attendues dans le texte reconnu, par numéro de texte. Elles servent de
# contrôle structurel quand aucune copie de référence n'est disponible.
CHAINES_ATTENDUES = {
    "98-750": ("98-750", "domaine foncier rural", "ASSEMBLEE NATIONALE"),
    "2020-624": ("2020-624", "urbanisme", "foncier urbain"),
}


def journaliser(message):
    print("  " + message, flush=True)


def verifier_swift():
    """Vérifie la disponibilité réelle de la chaîne d'OCR. Ne suppose rien."""
    etat = {
        "swiftc": shutil.which("swiftc"),
        "vision_framework": os.path.isdir("/System/Library/Frameworks/Vision.framework"),
        "pdfkit_framework": os.path.isdir("/System/Library/Frameworks/PDFKit.framework"),
        "appkit_framework": os.path.isdir("/System/Library/Frameworks/AppKit.framework"),
    }
    etat["disponible"] = all([etat["swiftc"], etat["vision_framework"],
                              etat["pdfkit_framework"], etat["appkit_framework"]])
    if etat["swiftc"]:
        try:
            sortie = subprocess.run([etat["swiftc"], "--version"], capture_output=True, text=True)
            etat["swiftc_version"] = (sortie.stdout or sortie.stderr).strip().split("\n")[0]
        except Exception as erreur:  # noqa: BLE001
            etat["swiftc_version"] = "illisible : %s" % erreur
    return etat


def compiler_si_necessaire():
    """Compile l'outil OCR si besoin. Retourne (ok, message)."""
    if os.path.isfile(BINAIRE_OCR) and os.path.getmtime(BINAIRE_OCR) >= os.path.getmtime(SOURCE_SWIFT):
        return True, "binaire à jour (pas de recompilation)"
    commande = ["swiftc", "-O", SOURCE_SWIFT, "-o", BINAIRE_OCR,
                "-framework", "Vision", "-framework", "PDFKit", "-framework", "AppKit"]
    resultat = subprocess.run(commande, capture_output=True, text=True)
    if resultat.returncode != 0:
        return False, "compilation échouée : %s" % (resultat.stderr or resultat.stdout)[:800]
    return True, "compilé (%s)" % os.path.basename(BINAIRE_OCR)


def executer_ocr(chemin_pdf, chemin_sortie, echelle=3.0):
    """Lance l'OCR. Retourne (ok, resume, erreur)."""
    resultat = subprocess.run([BINAIRE_OCR, chemin_pdf, chemin_sortie, str(echelle)],
                              capture_output=True, text=True)
    if resultat.returncode != 0:
        return False, None, resultat.stderr.strip()[:600]
    try:
        resume = json.loads(resultat.stdout.strip().split("\n")[-1])
    except (ValueError, IndexError):
        resume = {"sortie_brute": resultat.stdout[-300:]}
    resume["sha256_texte_ocr"] = "sha256:" + hashlib.sha256(
        open(chemin_sortie, "rb").read()).hexdigest()
    resume["octets_texte_ocr"] = os.path.getsize(chemin_sortie)
    return True, resume, None


def reference_pour(numero_texte):
    """Trouve, dans le corpus, une copie officielle à calque texte du même texte."""
    for document in corpus.lister_documents(domaine=DOMAINE):
        if document["numero_texte"] == numero_texte and document["calque_texte"]:
            return document
    return None


def collecter(chemin_db=None):
    rapport = {
        "horodatage": corpus.horodatage(),
        "domaine": DOMAINE,
        "chaine_ocr": verifier_swift(),
        "documents": [],
        "refus": [],
    }
    if not rapport["chaine_ocr"]["disponible"]:
        rapport["raison"] = "chaîne OCR indisponible : aucun traitement tenté"
        return rapport

    ok, message = compiler_si_necessaire()
    rapport["compilation"] = message
    if not ok:
        rapport["raison"] = message
        return rapport

    corpus.initialiser(chemin_db)

    # Cibles : documents du domaine sans calque texte ET sans texte OCR déjà fait.
    cibles = [d for d in corpus.lister_documents(domaine=DOMAINE) if not d["calque_texte"]]

    for document in cibles:
        entree = {"doc_id": document["doc_id"], "titre": document["titre"],
                  "numero_texte": document["numero_texte"],
                  "sha256_pdf": document["sha256"], "statut": None}
        chemin_pdf = document["chemin_local"]
        chemin_ocr = chemin_pdf.replace(".pdf", ".ocr.txt")
        journaliser("=== %s" % document["titre"][:70])

        if not os.path.isfile(chemin_ocr):
            commence = datetime.datetime.now()
            ok_ocr, resume, erreur = executer_ocr(chemin_pdf, chemin_ocr)
            if not ok_ocr:
                entree.update(statut="OCR_ECHOUE", erreur=erreur)
                rapport["refus"].append(entree)
                rapport["documents"].append(entree)
                journaliser("OCR ÉCHOUÉ : %s" % erreur)
                continue
            entree["ocr"] = resume
            entree["duree_s"] = round((datetime.datetime.now() - commence).total_seconds(), 1)
            journaliser("OCR terminé en %ss : %s lignes, %s"
                        % (entree["duree_s"], resume.get("lignes_reconnues"),
                           resume.get("sha256_texte_ocr")))
        else:
            entree["ocr"] = {
                "fichier_sortie": chemin_ocr,
                "sha256_texte_ocr": "sha256:" + hashlib.sha256(
                    open(chemin_ocr, "rb").read()).hexdigest(),
                "octets_texte_ocr": os.path.getsize(chemin_ocr),
                "deja_present": True,
            }
            journaliser("texte OCR déjà présent (pas de nouveau calcul)")

        texte_ocr = open(chemin_ocr, encoding="utf-8").read()
        articles_ocr = corpus.extraire_articles(texte_ocr)
        entree["articles_detectes"] = len(articles_ocr)
        journaliser("articles détectés dans l'OCR : %d" % len(articles_ocr))

        reference = reference_pour(document["numero_texte"])
        controle_structurel = None
        if reference and reference.get("fichier_texte"):
            articles_reference = corpus.extraire_articles(
                open(reference["fichier_texte"], encoding="utf-8").read())
            evaluation = ocr.evaluer_articles_ocr(articles_ocr, articles_reference)
            entree["reference"] = {"doc_id": reference["doc_id"],
                                   "titre": reference["titre"][:70],
                                   "sha256_pdf": reference["sha256"]}
            journaliser("recoupement avec la copie officielle à calque texte")
        else:
            evaluation = ocr.evaluer_articles_ocr(articles_ocr, None)
            controle_structurel = ocr.controler_structure(
                texte_ocr,
                CHAINES_ATTENDUES.get(document["numero_texte"], ()),
                # Plancher, pas mesure de qualité : une loi de ratification peut
                # légitimement ne compter que deux articles (loi 2020-623). Ce
                # seuil sert seulement à détecter un parseur qui ne trouve rien.
                minimum_articles=1)
            entree["controle_structurel"] = controle_structurel
            journaliser("aucune copie de référence : contrôle structurel %s"
                        % ("réussi" if controle_structurel["ok"] else "ÉCHOUÉ"))

        verdict = ocr.decision(evaluation, controle_structurel)
        entree["evaluation"] = {
            "avec_reference": evaluation["avec_reference"],
            "statistiques": evaluation.get("statistiques"),
            "nb_ecartes": len(evaluation.get("ecartes", [])),
            "nb_a_surveiller": len(evaluation.get("a_surveiller", [])),
            "absents_de_l_ocr": evaluation.get("absents_de_l_ocr", []),
            "ecartes": evaluation.get("ecartes", []),
        }
        entree["decision"] = verdict
        journaliser("décision : %s — %s" % (verdict["decision"], " ; ".join(verdict["raisons"])))

        if verdict["decision"] == ocr.DECISION_REFUS:
            entree["statut"] = "REFUSE"
            # La note du document doit dire la MÊME chose que le rapport : sinon
            # un document refusé garde « OCR requis » et laisse croire que l'OCR
            # n'a jamais été tenté.
            motif_refus = " ; ".join(verdict["raisons"])
            try:
                corpus.noter_refus_ocr(
                    document["doc_id"],
                    "OCR tenté le %s — REFUSÉ : %s" % (corpus.horodatage(), motif_refus),
                    fichier_ocr=chemin_ocr, chemin=chemin_db)
            except Exception as erreur:  # noqa: BLE001
                journaliser("note de refus non enregistrée : %s" % (erreur,))
            rapport["refus"].append(entree)
            rapport["documents"].append(entree)
            continue

        # Articles retenus : ceux qui passent le seuil, jamais les écartés.
        if evaluation["avec_reference"]:
            retenus = {num: articles_ocr[num] for num in evaluation["apparies"] if num in articles_ocr}
            confiance = {num: info["similarite"] for num, info in evaluation["apparies"].items()}
            recoupe = True
            doc_reference = reference["doc_id"] if reference else None
        else:
            retenus = dict(articles_ocr)
            confiance = None
            recoupe = False
            doc_reference = None

        try:
            resultat = corpus.enregistrer_articles(
                document["ref_id"], document["doc_id"], retenus,
                origine_texte="OCR_AUTO", confiance_ocr=confiance,
                recoupe=recoupe, doc_reference=doc_reference,
                remplacer=True, chemin=chemin_db)
        except ValueError as erreur:
            # Le refus arrive APRÈS une décision « intégrer » : la décision doit
            # être corrigée, sinon le rapport annonce une intégration qui n'a pas
            # eu lieu et contredit sa propre synthèse.
            entree["decision"] = {
                "decision": ocr.DECISION_REFUS,
                "raisons": ["refus à l'indexation : %s" % erreur],
                "articles_integrables": 0,
            }
            entree.update(statut="INTEGRATION_REFUSEE", erreur=str(erreur))
            try:
                corpus.noter_refus_ocr(
                    document["doc_id"],
                    "OCR tenté le %s — REFUSÉ à l'indexation : %s"
                    % (corpus.horodatage(), erreur),
                    fichier_ocr=chemin_ocr, chemin=chemin_db)
            except Exception as erreur_note:  # noqa: BLE001
                journaliser("note de refus non enregistrée : %s" % (erreur_note,))
            rapport["refus"].append(entree)
            rapport["documents"].append(entree)
            journaliser("intégration refusée : %s" % erreur)
            continue

        note = "texte OCR (%s)%s" % (
            "recoupé avec la copie à calque texte, confiance moyenne %s"
            % (evaluation["statistiques"] or {}).get("similarite_moyenne", "?")
            if recoupe else "non recoupé : qualité mesurée structurellement seulement",
            " ; %d article(s) écarté(s)" % len(evaluation.get("ecartes", []))
            if evaluation.get("ecartes") else "")
        details = corpus.enregistrer_ocr_document(
            document["doc_id"], chemin_ocr, recoupe_avec=doc_reference,
            qualite_ocr=(evaluation["statistiques"] or {}).get("similarite_moyenne"),
            note=note, chemin=chemin_db)

        entree.update(statut="INTEGRE", articles_indexes=resultat["articles_indexes"],
                      texte_ocr=details["sha256_ocr"],
                      origine_texte="OCR_AUTO", recoupe=recoupe,
                      hors_extraction=corpus.articles_hors_extraction(
                          document["doc_id"], retenus, chemin=chemin_db),
                      confiance_moyenne=(evaluation["statistiques"] or {}).get("similarite_moyenne"))
        if entree["hors_extraction"]:
            journaliser("ATTENTION : %d ligne(s) présente(s) en base mais absente(s) de "
                        "l'extraction courante (non supprimées, signalées) : %s"
                        % (len(entree["hors_extraction"]), ", ".join(entree["hors_extraction"][:12])))
        journaliser("intégrés : %d articles en OCR_AUTO (%s)"
                    % (resultat["articles_indexes"],
                       "recoupés" if recoupe else "non recoupés"))
        rapport["documents"].append(entree)

    rapport["integrite"] = corpus.verifier_integrite(chemin=chemin_db)
    rapport["synthese"] = corpus.rapport(domaine=DOMAINE, chemin=chemin_db)
    rapport["sans_articles"] = corpus.documents_sans_articles(chemin=chemin_db)
    return rapport


def afficher_etat(chemin_db=None):
    corpus.initialiser(chemin_db)  # applique la migration avant toute lecture
    chaine = verifier_swift()
    print("Chaîne OCR : %s" % ("DISPONIBLE" if chaine["disponible"] else "INDISPONIBLE"))
    for cle in ("swiftc", "swiftc_version", "vision_framework", "pdfkit_framework", "appkit_framework"):
        print("  %-20s %s" % (cle, chaine.get(cle)))
    print("  binaire %-12s %s" % (os.path.basename(BINAIRE_OCR),
                                  "présent" if os.path.isfile(BINAIRE_OCR) else "absent"))
    resume = corpus.rapport(domaine=DOMAINE, chemin=chemin_db)
    print()
    print("Documents : %d | articles : %d" % (resume["nb_documents"], resume["nb_articles_indexes"]))
    print("Articles par origine :")
    for origine, compte in resume["articles_par_origine"].items():
        print("  %-22s %5d articles | recoupés %5d | confiance moy. %s"
              % (origine, compte["articles"], compte["recoupes"], compte["confiance_moyenne"]))
    for document in resume["documents"]:
        print("  [%-16s] %-54s %4d art." % (document["methode_extraction"],
                                            document["titre"][:54], document["articles_indexes"]))
    sans = corpus.documents_sans_articles(chemin=chemin_db)
    if sans:
        print("Documents SANS aucun article (donc sans texte exploitable) :")
        for document in sans:
            print("  %s — %s" % (document["doc_id"], document["titre"][:60]))
    return resume


def main(argv=None):
    parseur = argparse.ArgumentParser(description="OCR des PDF scannés du corpus.")
    parseur.add_argument("--etat", action="store_true", help="état sans rien exécuter")
    parseur.add_argument("--rapport", default=None, help="chemin du rapport JSON")
    parseur.add_argument("--domaine", default=None, choices=sorted(DOSSIERS_PAR_DOMAINE),
                         help="domaine à traiter (défaut : logement_baux_foncier)")
    arguments = parseur.parse_args(argv)

    if arguments.domaine:
        # Rebranche les globales du module : sans --domaine, le comportement
        # historique (logement, baux et foncier) est strictement inchange.
        globals()["DOMAINE"] = arguments.domaine
        globals()["DOSSIER_CORPUS"] = KNOWLEDGE_DIR / "CORPUS" / DOSSIERS_PAR_DOMAINE[arguments.domaine]
        globals()["DOSSIER_CORPUS"].mkdir(parents=True, exist_ok=True)

    if arguments.etat:
        afficher_etat()
        return 0

    rapport = collecter()
    print()
    print("=" * 74)
    print("SYNTHÈSE OCR")
    print("=" * 74)
    print("Chaîne OCR        : %s" % ("disponible" if rapport["chaine_ocr"]["disponible"] else "indisponible"))
    print("Compilation       : %s" % rapport.get("compilation"))
    integres = [d for d in rapport["documents"] if d.get("statut") == "INTEGRE"]
    print("Documents intégrés: %d / %d" % (len(integres), len(rapport["documents"])))
    print("Refus             : %d" % len(rapport["refus"]))
    for entree in rapport["refus"]:
        detail = entree.get("erreur")
        if not detail:
            decision = entree.get("decision")
            detail = " ; ".join(decision.get("raisons", [])) if isinstance(decision, dict) else str(decision or "")
        print("   - %s : %s" % (str(entree.get("titre", "?"))[:50], str(detail)[:90]))
    if rapport.get("synthese"):
        print("Articles indexés  : %d" % rapport["synthese"]["nb_articles_indexes"])
    if rapport.get("integrite"):
        print("Intégrité         : %s" % rapport["integrite"]["verdict"])

    destination = arguments.rapport or str(KNOWLEDGE_DIR / "CORPUS" / "rapport_ocr.json")
    os.makedirs(os.path.dirname(destination), exist_ok=True)
    with open(destination, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    print("Rapport OCR       : %s" % destination)
    return 0


if __name__ == "__main__":
    sys.exit(main())
