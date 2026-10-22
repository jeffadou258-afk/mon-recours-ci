# -*- coding: utf-8 -*-
"""Récupération des PDF absents — l'empreinte décide, pas la disponibilité.

Ce que ces tests protègent :
  1. une empreinte qui ne correspond pas est REFUSÉE (aucun fichier écrit) ;
  2. un document déjà présent n'est jamais remplacé ;
  3. une source morte est signalée, sans exception ;
  4. la comparaison tolère le préfixe `sha256:` stocké en base ;
  5. l'écriture réelle produit un fichier en 600.
"""

import hashlib
import http.server
import os
import pathlib
import shutil
import sys
import tempfile
import threading
import unittest
import functools

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bin import recuperer_pdf as R  # noqa: E402


class GestionnaireSilencieux(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return


class ServeurLocal:
    def __init__(self, racine):
        gestionnaire = functools.partial(GestionnaireSilencieux, directory=str(racine))
        self.serveur = http.server.ThreadingHTTPServer(("127.0.0.1", 0), gestionnaire)
        self.port = self.serveur.server_address[1]
        threading.Thread(target=self.serveur.serve_forever, daemon=True).start()

    def url(self, nom):
        return "http://127.0.0.1:%d/%s" % (self.port, nom)

    def fermer(self):
        self.serveur.shutdown()
        self.serveur.server_close()


CONTENU = b"%PDF-1.4 contenu officiel de test\n%%EOF\n"


class TestRecuperation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="recup_pdf_")
        self.racine = os.path.join(self.tmp, "srv")
        os.makedirs(self.racine)
        with open(os.path.join(self.racine, "loi.pdf"), "wb") as f:
            f.write(CONTENU)
        self.serveur = ServeurLocal(self.racine)
        self.cible = os.path.join(self.tmp, "corpus", "loi.pdf")
        self.sha = "sha256:" + hashlib.sha256(CONTENU).hexdigest()

    def tearDown(self):
        self.serveur.fermer()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_empreinte_identique_recupere_le_fichier(self):
        _, statut, detail = R.traiter("D1", self.cible, self.serveur.url("loi.pdf"), self.sha, True)
        self.assertEqual(statut, R.RECUPERE, detail)
        self.assertTrue(os.path.isfile(self.cible))
        self.assertEqual(os.stat(self.cible).st_mode & 0o777, 0o600)

    def test_empreinte_differente_refuse(self):
        faux = "sha256:" + "0" * 64
        _, statut, _ = R.traiter("D2", self.cible, self.serveur.url("loi.pdf"), faux, True)
        self.assertEqual(statut, R.EMPREINTE_DIFFERENTE)
        self.assertFalse(os.path.exists(self.cible), "aucun fichier ne doit être écrit")

    def test_document_present_jamais_remplace(self):
        os.makedirs(os.path.dirname(self.cible))
        with open(self.cible, "wb") as f:
            f.write(b"ancien contenu local")
        _, statut, _ = R.traiter("D3", self.cible, self.serveur.url("loi.pdf"), self.sha, True)
        self.assertEqual(statut, R.DEJA_PRESENT)
        with open(self.cible, "rb") as f:
            self.assertEqual(f.read(), b"ancien contenu local")

    def test_source_morte_signalee_sans_exception(self):
        _, statut, detail = R.traiter("D4", self.cible, self.serveur.url("absent.pdf"), self.sha, True)
        self.assertTrue(statut.startswith(R.INACCESSIBLE), detail)

    def test_prefixe_sha256_tolere(self):
        self.assertEqual(R.empreinte_attendue("sha256:ABCDEF"), "abcdef")
        self.assertEqual(R.empreinte_attendue("ABCDEF"), "abcdef")
        self.assertEqual(R.empreinte_attendue(None), "")

    def test_simulation_n_ecrit_rien(self):
        _, statut, _ = R.traiter("D5", self.cible, self.serveur.url("loi.pdf"), self.sha, False)
        self.assertEqual(statut, R.RECUPERE)
        self.assertFalse(os.path.exists(self.cible), "la simulation ne doit rien écrire")

    def test_chemin_etranger_ramene_sous_knowledge(self):
        """Un chemin d'une autre machine est ramené sous le KNOWLEDGE local."""
        import config
        resolu = R.resoudre("/home/claude/mon-recours-ci/KNOWLEDGE/CORPUS/loi.pdf")
        self.assertEqual(resolu, pathlib.Path(str(config.KNOWLEDGE_DIR)) / "CORPUS" / "loi.pdf")


if __name__ == "__main__":
    unittest.main(verbosity=2)
