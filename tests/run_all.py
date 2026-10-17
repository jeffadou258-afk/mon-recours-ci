#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Exécute toute la suite de tests de Mon Recours CI et imprime un verdict factuel.

Usage :
    python3 tests/run_all.py

Le script ne conclut pas « tout va bien » : il imprime TESTS / FAIL / ERR / SKIP
et sort avec un code non nul en cas d'échec.
"""

import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, RACINE)


def main():
    chargeur = unittest.TestLoader()
    suite = chargeur.discover(TESTS, pattern="test_*.py")
    resultat = unittest.TextTestRunner(verbosity=2).run(suite)

    print()
    print("=" * 68)
    print("TESTS=%d FAIL=%d ERR=%d SKIP=%d SUCCES=%d"
          % (resultat.testsRun, len(resultat.failures), len(resultat.errors),
             len(resultat.skipped), resultat.testsRun - len(resultat.failures)
             - len(resultat.errors) - len(resultat.skipped)))
    if resultat.failures:
        print("ÉCHECS :")
        for cas, _ in resultat.failures:
            print("  - %s" % cas)
    if resultat.errors:
        print("ERREURS :")
        for cas, _ in resultat.errors:
            print("  - %s" % cas)
    print("VERDICT=%s" % ("SUCCES" if resultat.wasSuccessful() else "ECHEC"))
    print("=" * 68)
    return 0 if resultat.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
