# -*- coding: utf-8 -*-
"""Portabilité du corpus : chemins de la machine de collecte, PDF non distribués."""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402
from core import corpus  # noqa: E402


class TestLocalisation(unittest.TestCase):

    def test_un_chemin_de_la_machine_de_collecte_est_retrouve_dans_le_depot(self):
        reel = os.path.join(str(config.KNOWLEDGE_DIR), "catalogue.json")
        enregistre = "/Users/quelquun/ailleurs/KNOWLEDGE/catalogue.json"
        self.assertEqual(corpus.localiser_fichier(enregistre), reel)

    def test_un_fichier_introuvable_reste_introuvable(self):
        enregistre = "/Users/quelquun/KNOWLEDGE/CORPUS/inexistant.pdf"
        self.assertEqual(corpus.localiser_fichier(enregistre), enregistre)

    def test_la_base_n_est_pas_reecrite(self):
        with corpus.connexion() as conn:
            avant = [tuple(r) for r in conn.execute(
                "SELECT doc_id, chemin_local, fichier_texte FROM documents ORDER BY doc_id")]
        corpus.lister_documents()
        with corpus.connexion() as conn:
            apres = [tuple(r) for r in conn.execute(
                "SELECT doc_id, chemin_local, fichier_texte FROM documents ORDER BY doc_id")]
        self.assertEqual(avant, apres)


class TestModePdfNonDistribues(unittest.TestCase):

    def setUp(self):
        self.ancien = os.environ.get(corpus.VARIABLE_PDF_NON_DISTRIBUES)

    def tearDown(self):
        if self.ancien is None:
            os.environ.pop(corpus.VARIABLE_PDF_NON_DISTRIBUES, None)
        else:
            os.environ[corpus.VARIABLE_PDF_NON_DISTRIBUES] = self.ancien

    def test_par_defaut_un_pdf_absent_est_un_ecart(self):
        os.environ.pop(corpus.VARIABLE_PDF_NON_DISTRIBUES, None)
        resultat = corpus.verifier_integrite()
        self.assertEqual(resultat["mode"], "strict")
        if resultat["absents"]:
            self.assertEqual(resultat["verdict"], "ECART DETECTE")

    def test_en_mode_tolere_un_texte_altere_reste_un_ecart(self):
        os.environ[corpus.VARIABLE_PDF_NON_DISTRIBUES] = "1"
        dossier = tempfile.mkdtemp()
        try:
            copie = os.path.join(dossier, "copie.sqlite3")
            shutil.copy(str(config.CHEMIN_DB), copie)
            conn = sqlite3.connect(copie)
            cible = conn.execute(
                "SELECT doc_id FROM documents WHERE sha256_texte IS NOT NULL AND fichier_texte IS NOT NULL"
                " LIMIT 1").fetchone()[0]
            conn.execute("UPDATE documents SET sha256_texte = ? WHERE doc_id = ?",
                         ("sha256:" + "0" * 64, cible))
            conn.commit()
            conn.close()
            resultat = corpus.verifier_integrite(chemin=copie)
            documents_sans_pdf = [d for d in corpus.lister_documents(chemin=copie)
                                  if not os.path.isfile(d["chemin_local"] or "")]
            if not any(d["doc_id"] == cible for d in documents_sans_pdf):
                self.skipTest("le PDF du document ciblé est présent : test sans portée ici")
            self.assertEqual(resultat["verdict"], "ECART DETECTE")
            self.assertIn(cible, [a["doc_id"] for a in resultat["alteres"]])
        finally:
            shutil.rmtree(dossier)


if __name__ == "__main__":
    unittest.main()
