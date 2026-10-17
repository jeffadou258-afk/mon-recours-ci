#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérifie l'accessibilité RÉELLE des sources officielles du registre.

Usage :
    python3 bin/verifier_sources.py               # toutes les sources
    python3 bin/verifier_sources.py SGG CNDJ      # sources choisies
    python3 bin/verifier_sources.py --rapport     # n'interroge rien, lit l'historique

Ce script écrit un journal horodaté (KNOWLEDGE/verifications_sources.json) et
affiche le résultat tel qu'il est : un 503 est affiché 503.
"""

import argparse
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import sources  # noqa: E402


def main(argv=None):
    parseur = argparse.ArgumentParser(description="Vérification des sources officielles.")
    parseur.add_argument("source_ids", nargs="*", help="identifiants du registre (défaut : toutes)")
    parseur.add_argument("--rapport", action="store_true", help="lire l'historique sans interroger le réseau")
    parseur.add_argument("--timeout", type=int, default=20)
    arguments = parseur.parse_args(argv)

    if arguments.rapport:
        rapport = sources.rapport_sources()
    else:
        resultats = sources.verifier_sources(arguments.source_ids or None, timeout=arguments.timeout)
        rapport = sources.rapport_sources()
        print("=== Vérifications de cette exécution ===")
        for rec in resultats:
            print("  %-18s %-14s HTTP %-5s %s" % (
                rec["source_id"], rec["statut"], rec.get("http_status"),
                rec.get("erreur") or rec["url"]))

    print()
    print("=== Rapport sur le registre ===")
    print("Sources au registre : %d | vérifications journalisées : %d"
          % (rapport["nb_sources_registre"], rapport["nb_verifications_enregistrees"]))
    for ligne in rapport["sources"]:
        print("  %-18s %-14s HTTP %-5s consulté le %s | %s" % (
            ligne["source_id"], ligne["statut"], ligne["http_status"],
            ligne["date_consultation"] or "jamais", ligne["url"]))
    if rapport["jamais_testees"]:
        print("  JAMAIS TESTÉES : %s" % ", ".join(rapport["jamais_testees"]))
    print()
    print(rapport["avertissement"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
