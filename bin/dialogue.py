# -*- coding: utf-8 -*-
"""Dialogue en ligne de commande — éprouve la couche conversationnelle.

    python3 bin/dialogue.py --demande "Mon bailleur garde ma caution de deux mois."
    python3 bin/dialogue.py --dossier D1 --reponses logement=oui
    python3 bin/dialogue.py --catalogue          # ce que le catalogue sait traiter
    python3 bin/dialogue.py --fichier D1         # relit une conversation

Ce CLI n'est PAS une interface utilisateur finale : c'est l'outil de recette de
la couche. Il n'envoie rien, ne déploie rien, et n'invente aucune réponse.
"""

import argparse
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402
from core import catalogue, service  # noqa: E402


def _afficher(objet):
    if not objet.get("ok"):
        erreur = objet["erreur"]
        print("\nERREUR [%s] %s" % (erreur["code"], erreur["message"]))
        if erreur.get("libelle"):
            print("       %s" % erreur["libelle"])
        return 1
    print(json.dumps(objet["data"], ensure_ascii=False, indent=1))
    return 0


def _rendre_texte(reponse):
    """Version lisible d'une réponse — 6 sections, comme le prévoit le contrat."""
    s = reponse.get("sections") or {}
    print("\n" + "=" * 72)
    print("STATUT : %s" % reponse.get("statut_reponse"))
    print("=" * 72)
    faits = s.get("1_faits") or {}
    print("\n1. CE QUE JE COMPRENDS")
    print("   %s" % (faits.get("demande") or "—"))
    print("   %s" % (faits.get("note") or ""))
    print("\n2. CE QUE DIT LE DROIT")
    for entree in s.get("2_droit") or []:
        print("   [%s art. %s · %s]" % (entree.get("numero_texte") or "—",
                                        entree.get("article"), entree.get("titre")))
        print("   « %s »" % entree.get("citation"))
        if entree.get("note_lecture"):
            print("   (%s)" % entree["note_lecture"])
        if entree.get("lecture"):
            print("   Lecture courante : %s" % entree["lecture"])
    if not s.get("2_droit"):
        print("   Aucun article cité.")
    print("\n3. COMMENT CELA S'APPLIQUE")
    print("   %s" % (s.get("3_application") or "—"))
    print("\n4. CE QUE VOUS POUVEZ FAIRE")
    for etape in s.get("4_demarches") or []:
        print("   - %s" % etape)
    print("\n5. POINTS À VÉRIFIER")
    for point in s.get("5_a_verifier") or []:
        print("   - %s" % point)
    if not s.get("5_a_verifier"):
        print("   (rien de signalé)")
    print("\n6. SOURCES")
    for source in s.get("6_sources") or []:
        print("   - %s art. %s · %s · lecture %s%s"
              % (source.get("numero_texte") or "—", source.get("article"),
                 source.get("etat_verification"), source.get("origine_texte"),
                 " (recoupé)" if source.get("recoupe") else " (non recoupé)"))
        print("     %s" % source.get("url_source"))
        print("     empreinte : %s" % source.get("sha256_article"))
    verrous = reponse.get("verrous_humains") or []
    if verrous:
        print("\nVERROUS HUMAINS")
        for verrou in verrous:
            print("   - %s" % verrou)
    brouillon = reponse.get("brouillon") or {}
    print("\nBROUILLON : %s" % ("disponible" if brouillon.get("disponible") else "non généré"))
    if brouillon.get("note"):
        print("   %s" % brouillon["note"])
    if brouillon.get("genere"):
        print("   %s" % brouillon["genere"].get("fichier_txt"))
    if brouillon.get("raison"):
        print("   raison : %s" % brouillon["raison"])
    return 0


def main(argv=None):
    parseur = argparse.ArgumentParser(description="Dialogue Mon Recours CI")
    parseur.add_argument("--demande")
    parseur.add_argument("--dossier", default="CLI_DEMO")
    parseur.add_argument("--reponses", nargs="*", default=[],
                         help="paires cle=valeur, ex. logement=oui")
    parseur.add_argument("--catalogue", action="store_true")
    parseur.add_argument("--fichier", metavar="DOSSIER")
    arguments = parseur.parse_args(argv)

    if arguments.catalogue:
        fiches = catalogue.charger()
        par_domaine = catalogue.couverture(fiches=fiches)
        print("%d fiches validées contre le corpus :" % len(fiches))
        for domaine, titres in sorted(par_domaine.items()):
            print("\n  %s (%d)" % (domaine, len(titres)))
            for titre in titres:
                print("    - %s" % titre)
        return 0

    if arguments.fichier:
        chemin = str(config.dossier_utilisateur(arguments.fichier) / "CONVERSATION.json")
        if not os.path.isfile(chemin):
            print("Aucune conversation pour %r." % arguments.fichier)
            return 1
        with open(chemin, encoding="utf-8") as flux:
            etat = json.load(flux)
        print(json.dumps(etat, ensure_ascii=False, indent=1))
        return 0

    if arguments.demande:
        resultat = service.ouvrir(arguments.dossier, arguments.demande)
        if not resultat.get("ok"):
            return _afficher(resultat)
        donnees = resultat["data"]
        print("ÉTAPE : %s" % donnees.get("etape"))
        if donnees.get("etape") == "refus":
            print(json.dumps(donnees.get("reponse"), ensure_ascii=False, indent=1))
            return 0
        if donnees.get("etape") == "clarification":
            print("\nFiches identifiées :")
            for fiche in donnees.get("fiches_identifiees") or []:
                print("  - %s (art. %s, %s)"
                      % (fiche["titre"], fiche["article"], fiche["etat_verification"]))
            print("\nQuestions :")
            for question in donnees.get("questions") or []:
                print("  [%s] %s" % (question["cle"], question["question"]))
            if not donnees.get("questions"):
                print("  (aucune question nécessaire)")
        else:
            print(json.dumps(donnees.get("reponse"), ensure_ascii=False, indent=1))
        if not arguments.reponses:
            print("\nPour poursuivre : --dossier %s --reponses cle=valeur" % arguments.dossier)
        return 0

    if arguments.reponses:
        reponses = {}
        for element in arguments.reponses:
            if "=" not in element:
                print("Réponse mal formée : %r (attendu cle=valeur)" % element)
                return 2
            cle, _, valeur = element.partition("=")
            reponses[cle.strip()] = valeur.strip()
        resultat = service.repondre(arguments.dossier, reponses)
        if not resultat.get("ok"):
            return _afficher(resultat)
        return _rendre_texte(resultat["data"]["reponse"])

    parseur.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
