# -*- coding: utf-8 -*-
"""Urgence : la sécurité passe avant l'analyse, et une situation calme ne la déclenche pas."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.urgence import detecter  # noqa: E402


class TestUrgenceCritique(unittest.TestCase):
    def test_menace_avec_arme(self):
        resultat = detecter("Mon mari est venu avec un couteau et menace de me tuer.")
        self.assertEqual(resultat["niveau"], "CRITIQUE")
        self.assertFalse(resultat["analyse_longue_autorisee"])
        self.assertEqual(resultat["priorite"], "SECURITE_ET_ORIENTATION")
        self.assertTrue(resultat["declencheurs"])
        self.assertIn("detecte", resultat["declencheurs"][0])

    def test_violences_conjugales(self):
        self.assertEqual(detecter("Je subis des violences conjugales depuis des mois.")["niveau"],
                         "CRITIQUE")

    def test_danger_pour_un_enfant(self):
        self.assertEqual(detecter("Mon enfant est en danger, son oncle le frappe.")["niveau"],
                         "CRITIQUE")

    def test_garde_a_vue(self):
        self.assertEqual(detecter("Mon frère est en garde à vue depuis hier.")["niveau"], "CRITIQUE")

    def test_la_consigne_interdit_le_retard(self):
        resultat = detecter("Il menace de me tuer.")
        self.assertIn("Sécurité d'abord", resultat["consigne"])


class TestUrgenceElevee(unittest.TestCase):
    def test_urgence_elevee_expulsion(self):
        resultat = detecter("J'ai reçu un commandement de payer, il parle d'expulsion.")
        self.assertEqual(resultat["niveau"], "ELEVEE")
        self.assertTrue(resultat["analyse_longue_autorisee"])

    def test_verbe_expulser_detecte(self):
        """Régression : le VERBE « expulser » doit déclencher l'urgence élevée.

        Un locataire écrit « il va me faire expulser », pas « expulsion ».
        Manquer cette forme faisait passer une menace d'expulsion pour une
        demande ordinaire.
        """
        for texte in ("Mon bailleur dit qu'il va me faire expulser.",
                      "Il menace de m'expulser du logement.",
                      "Je risque de me faire expulser la semaine prochaine."):
            resultat = detecter(texte)
            self.assertEqual(resultat["niveau"], "ELEVEE", "non détecté : %s" % texte)

    def test_licenciement(self):
        self.assertEqual(detecter("Je viens de recevoir ma lettre de licenciement.")["niveau"],
                         "ELEVEE")

    def test_audience_et_assignation(self):
        self.assertEqual(detecter("J'ai une audience au tribunal la semaine prochaine.")["niveau"],
                         "ELEVEE")


class TestUrgenceNormale(unittest.TestCase):
    def test_demande_ordinaire(self):
        resultat = detecter("Mon bailleur ne m'a pas rendu la caution, comment faire ?")
        self.assertEqual(resultat["niveau"], "NORMALE")
        self.assertEqual(resultat["declencheurs"], [])
        self.assertTrue(resultat["analyse_longue_autorisee"])

    def test_question_administrative(self):
        self.assertEqual(detecter("Où demander un extrait d'acte de naissance ?")["niveau"],
                         "NORMALE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
