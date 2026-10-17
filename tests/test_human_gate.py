# -*- coding: utf-8 -*-
"""Verrous humains : ils ne se ferment jamais tout seuls, et bloquent les actions externes."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.plan_action import (  # noqa: E402
    HumanGate,
    actions_externes_autorisees,
    construire_plan,
    evaluer_verrous,
)
from core.urgence import detecter  # noqa: E402


class TestOuvertureDesVerrous(unittest.TestCase):
    def test_urgence_critique_ouvre_deux_verrous(self):
        urgence = detecter("Mon mari est venu avec un couteau et menace de me tuer.")
        verrous = evaluer_verrous(urgence, ["famille_mariage_filiation"], "menace de mort")
        codes = [v["motif_code"] for v in verrous]
        self.assertIn("URGENCE_CRITIQUE", codes)
        self.assertIn("VIOLENCE_OU_MENACE", codes)
        self.assertTrue(all(v["ouvert"] for v in verrous))

    def test_procedure_penale_ouvre_le_verrou_judiciaire(self):
        urgence = detecter("Il y a une audience au tribunal.")
        codes = [v["motif_code"] for v in evaluer_verrous(urgence, ["penal_procedure_penale"], "")]
        self.assertIn("PROCEDURE_JUDICIAIRE", codes)

    def test_personne_vulnerable_detectee(self):
        urgence = detecter("Mon fils mineur est concerné.")
        codes = [v["motif_code"] for v in evaluer_verrous(urgence, ["logement_baux_foncier"],
                                                          "mon enfant mineur")]
        self.assertIn("PERSONNE_VULNERABLE", codes)

    def test_dossier_ordinaire_n_ouvre_rien(self):
        urgence = detecter("Où demander un extrait d'acte de naissance ?")
        verrous = evaluer_verrous(urgence, ["administratif_voies_de_recours"],
                                  "où demander un extrait d'acte de naissance ?")
        self.assertEqual(verrous, [])

    def test_motif_de_verrou_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            HumanGate("MOTIF_INVENTE")


class TestFermeture(unittest.TestCase):
    def test_un_verrou_neuf_est_ouvert(self):
        verrou = HumanGate("PROCEDURE_JUDICIAIRE")
        self.assertEqual(verrou.statut, "OUVERT")
        self.assertTrue(verrou.ouvert)
        self.assertIsNone(verrou.decision)

    def test_fermeture_sans_marqueur_humain_refusee(self):
        verrou = HumanGate("URGENCE_CRITIQUE")
        for marqueur in (None, "", "   "):
            with self.assertRaises(ValueError) as ctx:
                verrou.fermer_par_decision_humaine("autorise", marqueur)
            self.assertIn("aucune source humaine identifiée", str(ctx.exception))
        self.assertTrue(verrou.ouvert)

    def test_decision_inconnue_refusee(self):
        verrou = HumanGate("URGENCE_CRITIQUE")
        with self.assertRaises(ValueError):
            verrou.fermer_par_decision_humaine("peut_etre", "Jeff")

    def test_fermeture_par_decision_humaine_enregistree(self):
        verrou = HumanGate("ACTION_ENGAGEANTE")
        decision = verrou.fermer_par_decision_humaine(
            "autorise", "utilisateur:jeff", commentaire="j'envoie moi-même le courrier")
        self.assertEqual(verrou.statut, "AUTORISE")
        self.assertFalse(verrou.ouvert)
        self.assertEqual(decision["marqueur_humain"], "utilisateur:jeff")
        self.assertTrue(decision["date_decision"])

    def test_revision_demandee_est_un_statut_distinct(self):
        verrou = HumanGate("SOURCES_CONTRADICTOIRES")
        verrou.fermer_par_decision_humaine("revision_demandee", "utilisateur:jeff")
        self.assertEqual(verrou.statut, "REVISION_DEMANDEE")


class TestBlocageDesActions(unittest.TestCase):
    def test_plan_avec_verrou_ouvert_bloque(self):
        urgence = detecter("Mon mari menace de me tuer avec une arme.")
        plan = construire_plan("TEST_GATE", ["famille_mariage_filiation"], urgence)
        autorise, raisons = actions_externes_autorisees(plan)
        self.assertFalse(autorise)
        self.assertTrue(raisons)

    def test_plan_sans_verrou_autorise(self):
        urgence = detecter("Question administrative simple.")
        plan = construire_plan("TEST_GATE", ["administratif_voies_de_recours"], urgence)
        autorise, raisons = actions_externes_autorisees(plan)
        self.assertTrue(autorise, raisons)
        self.assertEqual(raisons, [])

    def test_le_plan_ordonne_la_securite_en_premier(self):
        urgence = detecter("Il menace de me tuer avec un couteau.")
        plan = construire_plan("TEST_GATE", ["penal_procedure_penale"], urgence)
        etapes = plan["etapes"]
        self.assertEqual(etapes[0]["nature"], "automatisable")
        orientation = [e for e in etapes if e["nature"] == "orientation_humaine"]
        self.assertTrue(orientation, "aucune étape d'orientation humaine dans un cas critique")

    def test_etapes_declarent_leur_nature(self):
        urgence = detecter("Demande ordinaire.")
        plan = construire_plan("TEST_GATE", ["travail"], urgence)
        for etape in plan["etapes"]:
            self.assertIn(etape["nature"], ("automatisable", "manuel", "orientation_humaine"))
            self.assertTrue(etape["objectif"])

    def test_une_etape_manuelle_n_est_pas_marquee_automatisee(self):
        urgence = detecter("Demande ordinaire.")
        plan = construire_plan("TEST_GATE", ["travail"], urgence)
        for etape in plan["etapes"]:
            if etape["nature"] != "automatisable":
                self.assertFalse(etape["automatise_par_l_agent"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
