# -*- coding: utf-8 -*-
"""Veille de vigueur — constats techniques, jamais de conclusion juridique.

Ce que ces tests protègent :
  1. la classification d'un code HTTP reste factuelle ;
  2. `interroger` lit réellement un document et en calcule l'empreinte ;
  3. une source morte est signalée comme telle, sans lever d'exception ;
  4. le rapport ne porte JAMAIS un statut de vigueur autre que NON_VERIFIEE —
     même quand la source répond parfaitement, ce qui est précisément le piège :
     « joignable » n'est pas « en vigueur ».

Le serveur HTTP de test est local et temporaire : aucune requête vers un site
officiel n'est faite ici.
"""

import hashlib
import http.server
import json
import os
import shutil
import sys
import tempfile
import threading
import unittest
import functools

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bin import veille_vigueur as V  # noqa: E402
from core import base  # noqa: E402


class GestionnaireSilencieux(http.server.SimpleHTTPRequestHandler):
    """Sert les fichiers sans écrire de ligne de journal à chaque requête."""

    def log_message(self, *args):  # noqa: D401 - signature imposée par la stdlib
        return


class ServeurLocal:
    """Sert un répertoire temporaire sur un port libre."""

    def __init__(self, racine):
        gestionnaire = functools.partial(GestionnaireSilencieux, directory=str(racine))
        self.serveur = http.server.ThreadingHTTPServer(("127.0.0.1", 0), gestionnaire)
        self.port = self.serveur.server_address[1]
        self.thread = threading.Thread(target=self.serveur.serve_forever, daemon=True)
        self.thread.start()

    def url(self, nom):
        return "http://127.0.0.1:%d/%s" % (self.port, nom)

    def fermer(self):
        self.serveur.shutdown()
        self.serveur.server_close()


class TestClassification(unittest.TestCase):
    def test_codes_http(self):
        self.assertEqual(V.classer_joignabilite(200), "JOIGNABLE")
        self.assertEqual(V.classer_joignabilite(204), "JOIGNABLE")
        self.assertEqual(V.classer_joignabilite(301), "REDIRIGE")
        self.assertEqual(V.classer_joignabilite(404), "REFUSE")
        self.assertEqual(V.classer_joignabilite(503), "ERREUR_SERVEUR")
        self.assertEqual(V.classer_joignabilite(None), "INACCESSIBLE")


class TestInterrogation(unittest.TestCase):
    def setUp(self):
        self.racine = tempfile.mkdtemp(prefix="veille_http_")
        with open(os.path.join(self.racine, "texte.txt"), "w", encoding="utf-8") as f:
            f.write("contenu officiel de test")
        self.serveur = ServeurLocal(self.racine)

    def tearDown(self):
        self.serveur.fermer()
        shutil.rmtree(self.racine, ignore_errors=True)

    def test_lit_le_document_et_calcule_l_empreinte(self):
        code, empreinte, octets = V.interroger(self.serveur.url("texte.txt"), telecharger=True)
        self.assertEqual(code, 200)
        attendu = hashlib.sha256(b"contenu officiel de test").hexdigest()
        self.assertEqual(empreinte, attendu)
        self.assertEqual(octets, len(b"contenu officiel de test"))

    def test_source_absente_signalee_sans_exception(self):
        code, empreinte, _ = V.interroger(self.serveur.url("inexistant.pdf"), telecharger=True)
        self.assertEqual(code, 404)
        self.assertIsNone(empreinte)

    def test_port_ferme_donne_inaccessible(self):
        code, _, _ = V.interroger("http://127.0.0.1:9/rien", telecharger=False)
        self.assertIsNone(code)
        self.assertEqual(V.classer_joignabilite(code), "INACCESSIBLE")


class TestRapport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="veille_db_")
        self.chemin_db = os.path.join(self.tmp, "corpus.sqlite3")
        base.initialiser(self.chemin_db)
        self.racine = os.path.join(self.tmp, "web")
        os.makedirs(self.racine)
        with open(os.path.join(self.racine, "loi.pdf"), "wb") as f:
            f.write(b"%PDF-1.4 contenu synthetique")
        self.serveur = ServeurLocal(self.racine)
        base.ajouter_reference(
            "Loi synthétique de veille (test)",
            "loi",
            "Source de test",
            self.serveur.url("loi.pdf"),
            "2026-10-21",
            numero_texte="2099-002",
            extrait_texte="Article 1 — texte synthétique.",
            chemin=self.chemin_db,
        )

    def tearDown(self):
        self.serveur.fermer()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_source_joignable_reste_non_verifiee(self):
        """Le piège : une source qui répond ne prouve pas qu'elle est en vigueur."""
        rapport = V.construire(self.chemin_db, reseau=True, journal=lambda *_: None)
        entree = rapport["references"][0]
        self.assertEqual(entree["technique"]["joignabilite"], "JOIGNABLE")
        self.assertEqual(entree["statut_vigueur"], "NON_VERIFIEE")
        self.assertTrue(entree["a_valider_par_un_juriste"])
        self.assertEqual(rapport["resume"]["statut_vigueur_verifie"], 0)

    def test_aucune_entree_n_echappe_a_la_regle(self):
        rapport = V.construire(self.chemin_db, reseau=True, journal=lambda *_: None)
        for entree in rapport["references"]:
            self.assertEqual(entree["statut_vigueur"], "NON_VERIFIEE")
            self.assertTrue(entree["a_valider_par_un_juriste"])
        self.assertIn("relecture juridique", rapport["avertissement"])

    def test_hors_ligne_ne_contacte_rien(self):
        rapport = V.construire(self.chemin_db, reseau=False)
        self.assertEqual(rapport["references"][0]["technique"], {})
        self.assertEqual(rapport["references"][0]["statut_vigueur"], "NON_VERIFIEE")

    def test_rapport_serialisable(self):
        rapport = V.construire(self.chemin_db, reseau=False)
        texte = json.dumps(rapport, ensure_ascii=False)
        self.assertIn("NON_VERIFIEE", texte)


if __name__ == "__main__":
    unittest.main(verbosity=2)
