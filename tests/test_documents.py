# -*- coding: utf-8 -*-
"""Documents : brouillons produits, aucune capacité d'envoi, confinement vérifié."""

import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from core import documents  # noqa: E402

DOSSIER_TEST = "TEST_DOCUMENTS"
CHAMPS = {
    "objet": "restitution du dépôt de garantie",
    "faits": "J'ai quitté le logement le 2026-09-30 et remis les clés.",
    "demande": "la restitution du dépôt de garantie versé en 2026-01-10",
    "adresse_retour": "Adresse de retour à compléter",
}


class TestBrouillons(unittest.TestCase):
    def tearDown(self):
        shutil.rmtree(str(config.dossier_utilisateur(DOSSIER_TEST)), ignore_errors=True)

    def test_brouillon_produit_et_marque(self):
        resultat = documents.generer_brouillon(DOSSIER_TEST, "demande_amiable", CHAMPS)
        self.assertTrue(os.path.isfile(resultat["fichier_txt"]))
        self.assertGreater(resultat["octets_txt"], 300)
        contenu = open(resultat["fichier_txt"], encoding="utf-8").read()
        self.assertIn("BROUILLON — NON ENVOYÉ", contenu)
        self.assertIn("restitution du dépôt de garantie", contenu)
        self.assertIn("n'est ni avocat, ni huissier", contenu)

    def test_champs_obligatoires_manquants(self):
        incomplets = dict(CHAMPS)
        incomplets.pop("demande")
        with self.assertRaises(ValueError) as ctx:
            documents.generer_brouillon(DOSSIER_TEST, "demande_amiable", incomplets)
        self.assertIn("demande", str(ctx.exception))

    def test_modele_inconnu(self):
        with self.assertRaises(KeyError):
            documents.generer_brouillon(DOSSIER_TEST, "modele_bidon", CHAMPS)

    def test_champ_non_fourni_reste_visible(self):
        texte = documents.rendre_texte(DOSSIER_TEST, "reponse_a_courrier", CHAMPS)
        self.assertIn("[À COMPLÉTER : date_courrier]", texte)

    def test_formulation_interdite_refusee(self):
        champs = dict(CHAMPS)
        champs["demande"] = "Je vous garantis que vous gagnerez ce dossier."
        with self.assertRaises(ValueError) as ctx:
            documents.generer_brouillon(DOSSIER_TEST, "demande_amiable", champs)
        self.assertIn("GARANTIE_RESULTAT", str(ctx.exception))

    def test_aucun_document_ne_sort_du_dossier_brouillons(self):
        resultat = documents.generer_brouillon(DOSSIER_TEST, "reclamation", CHAMPS)
        attendu = str(config.dossier_utilisateur(DOSSIER_TEST) / "BROUILLONS")
        self.assertTrue(os.path.abspath(resultat["fichier_txt"]).startswith(attendu))

    def test_liste_des_brouillons(self):
        documents.generer_brouillon(DOSSIER_TEST, "demande_amiable", CHAMPS, export_pdf=False)
        brouillons = documents.lister_brouillons(DOSSIER_TEST)
        self.assertEqual(len(brouillons), 1)
        self.assertGreater(brouillons[0]["octets"], 0)

    def test_toutes_les_mentions_de_non_envoi(self):
        resultat = documents.generer_brouillon(DOSSIER_TEST, "demande_de_pieces", CHAMPS)
        self.assertIn("AUCUN", resultat["envoi"])


class TestAucuneCapaciteDEnvoi(unittest.TestCase):
    """Preuve PAR LECTURE DU SOURCE : aucune fonction d'envoi n'existe.

    Un garde-fou qui n'existe pas ne peut pas être contourné — c'est la meilleure
    forme de garantie pour cette contrainte (spec §8, §11).
    """

    def test_le_module_ne_peut_pas_envoyer(self):
        with open(documents.__file__, encoding="utf-8") as f:
            source = f.read()
        interdits = ("smtplib", "urllib.request", "http.client", "requests.post",
                     "requests.put", "socket.socket", "ftplib")
        for interdit in interdits:
            self.assertNotIn(interdit, source,
                             "capacité d'envoi détectée dans core/documents.py : %s" % interdit)

    def test_aucune_fonction_publique_d_envoi(self):
        noms = [n for n in dir(documents) if not n.startswith("_")]
        for nom in noms:
            self.assertFalse(any(mot in nom.lower() for mot in ("envoyer", "send", "poster")),
                             "fonction d'envoi exposée : %s" % nom)


if __name__ == "__main__":
    unittest.main(verbosity=2)
