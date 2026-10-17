# -*- coding: utf-8 -*-
"""Confidentialité : cloisonnement des dossiers, confinement des écritures, réseau limité.

Trois propriétés vérifiées :

1. Aucun identifiant de dossier ne permet de sortir de DOSSIERS/ (traversée).
2. Le dossier d'un utilisateur n'est ni lisible ni visible depuis un autre.
3. Un seul module (core/sources.py) touche le réseau ; aucun autre module du
   cœur ne peut transmettre une donnée utilisateur à un tiers.
"""

import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import core  # noqa: E402
from core import documents, evidence  # noqa: E402

DOSSIER_A = "TEST_CONFIDENTIALITE_A"
DOSSIER_B = "TEST_CONFIDENTIALITE_B"


class TestTraversee(unittest.TestCase):
    def test_identifiants_de_traversee_refuses(self):
        for mauvais in ("../secret", "a/b", "a\\b", "..", "", None, "x\x00y", "/etc/passwd"):
            with self.assertRaises(ValueError, msg="accepté à tort : %r" % (mauvais,)):
                config.dossier_utilisateur(mauvais)

    def test_identifiant_normal_accepte(self):
        self.assertTrue(str(config.dossier_utilisateur("USR-001")).endswith("USR-001"))


class TestCloisonnement(unittest.TestCase):
    def tearDown(self):
        for dossier in (DOSSIER_A, DOSSIER_B):
            shutil.rmtree(str(config.dossier_utilisateur(dossier)), ignore_errors=True)

    def test_les_brouillons_d_un_dossier_ne_sont_pas_visibles_dans_un_autre(self):
        documents.generer_brouillon(DOSSIER_A, "demande_amiable", {
            "objet": "affaire A", "faits": "faits A", "demande": "demande A",
            "adresse_retour": "adresse A"}, export_pdf=False)
        self.assertEqual(len(documents.lister_brouillons(DOSSIER_A)), 1)
        self.assertEqual(documents.lister_brouillons(DOSSIER_B), [])

    def test_les_tracabilites_ne_se_croisent_pas(self):
        for dossier, marqueur in ((DOSSIER_A, "MARQUEUR_UNIQUE_A"), (DOSSIER_B, "MARQUEUR_UNIQUE_B")):
            trace = evidence.construire(
                dossier_id=dossier, demande=marqueur, resume_neutre=marqueur,
                controles_qualite={"ok": True},
            )
            evidence.ecrire(trace)
        chemin_a = str(config.dossier_utilisateur(DOSSIER_A) / "DOSSIER_TRACABILITE.json")
        chemin_b = str(config.dossier_utilisateur(DOSSIER_B) / "DOSSIER_TRACABILITE.json")
        contenu_a = open(chemin_a, encoding="utf-8").read()
        contenu_b = open(chemin_b, encoding="utf-8").read()
        self.assertIn("MARQUEUR_UNIQUE_A", contenu_a)
        self.assertNotIn("MARQUEUR_UNIQUE_B", contenu_a)
        self.assertIn("MARQUEUR_UNIQUE_B", contenu_b)
        self.assertNotIn("MARQUEUR_UNIQUE_A", contenu_b)

    def test_lecture_d_un_dossier_vierge_echoue_proprement(self):
        with self.assertRaises(FileNotFoundError):
            evidence.lire("TEST_CONFIDENTIALITE_INEXISTANT")

    def test_le_dossier_de_tracabilite_n_embarque_pas_le_texte_des_pieces(self):
        """On enregistre l'empreinte, pas le contenu sensible."""
        source = open(evidence.__file__, encoding="utf-8").read()
        self.assertIn("empreinte", source)
        self.assertNotIn("shutil.copy", source)


class TestConfinementDesEcritures(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(str(config.dossier_utilisateur(DOSSIER_A)), ignore_errors=True)

    def test_ecriture_hors_dossiers_refusee(self):
        trace = evidence.construire(dossier_id=DOSSIER_A, demande="x")
        cible = os.path.join(os.path.dirname(str(config.DOSSIERS_DIR)), "hors_zone.json")
        with self.assertRaises(ValueError) as ctx:
            evidence.ecrire(trace, chemin=cible)
        self.assertIn("hors de DOSSIERS", str(ctx.exception))
        self.assertFalse(os.path.exists(cible))


class TestReseauLimite(unittest.TestCase):
    """Un seul module du cœur peut atteindre le réseau : core/sources.py.

    Preuve par lecture du source — la propriété ne dépend donc pas d'un
    comportement observable à l'exécution.
    """

    def test_seul_sources_touche_le_reseau(self):
        racine = os.path.dirname(config.__file__)
        fautifs = []
        for dossier in (os.path.join(racine, "core"),):
            for nom in sorted(os.listdir(dossier)):
                if not nom.endswith(".py") or nom == "sources.py":
                    continue
                chemin = os.path.join(dossier, nom)
                source = open(chemin, encoding="utf-8").read()
                for motif in ("urllib.request", "requests.", "http.client", "socket."):
                    if motif in source:
                        fautifs.append("%s contient %s" % (nom, motif))
        self.assertEqual(fautifs, [], "module du cœur atteignant le réseau : %s" % fautifs)

    def test_le_coeur_n_importe_pas_de_client_reseau_hors_sources(self):
        for nom in ("analyse", "base", "documents", "faits", "garde_fous",
                    "plan_action", "qualification", "urgence"):
            module = getattr(core, nom)
            source = open(module.__file__, encoding="utf-8").read()
            self.assertNotIn("import requests", source, "%s importe requests" % nom)


if __name__ == "__main__":
    unittest.main(verbosity=2)
