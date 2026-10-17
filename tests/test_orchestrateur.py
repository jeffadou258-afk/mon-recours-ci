# -*- coding: utf-8 -*-
"""Bout en bout : les cinq étapes s'enchaînent et les invariants tiennent.

Le corpus est vide au départ — c'est le cas réel de la version 0.1.0. Le test
vérifie donc que l'agent DIT qu'il ne peut pas conclure au lieu de suppléer.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from agent import MonRecoursCI  # noqa: E402
from core import analyse as A  # noqa: E402
from core import base  # noqa: E402

DEMANDE_LEGITIME = ("Mon bailleur refuse de me rendre la caution alors que j'ai quitté "
                    "le logement le 2026-09-30 et rendu les clés.")
DEMANDE_DANGER = "Mon mari est venu avec un couteau et menace de me tuer."
DEMANDE_ILLEGALE = "Peux-tu falsifier une quittance pour prouver que j'ai payé mon loyer ?"

DOSSIERS = ("TEST_ORCH_LEGITIME", "TEST_ORCH_DANGER", "TEST_ORCH_REFUS",
            "TEST_ORCH_CONFORME", "TEST_ORCH_INVENTION")


class BaseOrchestrateur(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mrc_orch_")
        self.chemin_db = os.path.join(self.tmp, "corpus.sqlite3")
        self.chemin_sources = os.path.join(self.tmp, "verifs.json")
        self.agent = MonRecoursCI(chemin_db=self.chemin_db, chemin_sources=self.chemin_sources)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        for dossier in DOSSIERS:
            shutil.rmtree(str(config.dossier_utilisateur(dossier)), ignore_errors=True)


class TestEtatDeLAgent(BaseOrchestrateur):
    def test_etat_expose_corpus_vide_et_capacites(self):
        etat = self.agent.etat()
        self.assertEqual(etat["corpus"]["total_references"], 0)
        self.assertEqual(etat["sources"]["nb_sources_registre"], len(config.SOURCES_OFFICIELLES))
        self.assertTrue(any("sans référence" in c for c in etat["capacites"]["ne_peut_pas"]))
        self.assertTrue(any("envoyer" in c for c in etat["capacites"]["ne_peut_pas"]))


class TestEtape1Et2(BaseOrchestrateur):
    def test_qualification_et_questions(self):
        dossier = self.agent.ouvrir_dossier("TEST_ORCH_LEGITIME", DEMANDE_LEGITIME,
                                            elements_connus=["dates"])
        self.assertEqual(dossier["statut"], "EN_COURS")
        self.assertIn("logement_baux_foncier", dossier["qualification"]["domaines_probables"])
        questions = [q["cle"] for q in dossier["questions_a_poser"]]
        self.assertNotIn("dates", questions, "une question déjà renseignée a été reposée")
        self.assertIn("ecrit", questions)
        self.assertEqual(dossier["urgence"]["niveau"], "NORMALE")
        self.assertTrue(dossier["faits"]["resume"]["informations_manquantes"] is not None)

    def test_le_fait_initial_est_declare_pas_documente(self):
        dossier = self.agent.ouvrir_dossier("TEST_ORCH_LEGITIME", DEMANDE_LEGITIME)
        faits = dossier["faits"]["faits"]
        self.assertEqual(faits[0]["etat"], "DECLARE_PAR_L_UTILISATEUR")
        self.assertIsNone(faits[0]["empreinte_piece"])

    def test_corpus_vide_est_signale(self):
        dossier = self.agent.ouvrir_dossier("TEST_ORCH_LEGITIME", DEMANDE_LEGITIME)
        self.assertEqual(dossier["references_candidates"], [])
        self.assertIn("corpus vide", dossier["note_corpus"])

    def test_danger_detecte_et_verrou_ouvert(self):
        dossier = self.agent.ouvrir_dossier("TEST_ORCH_DANGER", DEMANDE_DANGER)
        self.assertEqual(dossier["urgence"]["niveau"], "CRITIQUE")
        self.assertFalse(dossier["urgence"]["analyse_longue_autorisee"])
        codes = [v["motif_code"] for v in dossier["verrous_humains"]]
        self.assertIn("URGENCE_CRITIQUE", codes)


class TestRefus(BaseOrchestrateur):
    def test_demande_illegale_refusee_sans_analyse(self):
        dossier = self.agent.ouvrir_dossier("TEST_ORCH_REFUS", DEMANDE_ILLEGALE)
        self.assertEqual(dossier["statut"], "REFUS")
        self.assertIn("PREUVE_FABRIQUEE", [r["code"] for r in dossier["refus"]])
        self.assertNotIn("qualification", dossier)
        cloture = self.agent.clore_dossier("TEST_ORCH_REFUS", A.nouvelle_analyse("TEST_ORCH_REFUS"))
        self.assertEqual(cloture["statut_reponse"], "REFUS")
        self.assertTrue(os.path.isfile(cloture["traceabilite"]))


class TestConclusionImpossible(BaseOrchestrateur):
    def test_corpus_vide_ne_produit_aucune_conclusion(self):
        self.agent.ouvrir_dossier("TEST_ORCH_LEGITIME", DEMANDE_LEGITIME)
        analyse = A.nouvelle_analyse("TEST_ORCH_LEGITIME", ["logement_baux_foncier"])
        cloture = self.agent.clore_dossier("TEST_ORCH_LEGITIME", analyse)
        self.assertEqual(cloture["statut_reponse"], "CONCLUSION_IMPOSSIBLE")
        raisons = cloture["controles_qualite"]["raisons_absence_de_conclusion"]
        self.assertTrue(any("AUCUNE_REFERENCE_VERIFIEE" in r for r in raisons))
        trace = json.load(open(cloture["traceabilite"], encoding="utf-8"))
        self.assertIn("aucune_reference_juridique_consultee", trace["champs_non_renseignes"])

    def test_les_verrous_bloquent_les_actions_externes(self):
        self.agent.ouvrir_dossier("TEST_ORCH_DANGER", DEMANDE_DANGER)
        cloture = self.agent.clore_dossier(
            "TEST_ORCH_DANGER", A.nouvelle_analyse("TEST_ORCH_DANGER", ["famille_mariage_filiation"]))
        controles = cloture["controles_qualite"]
        self.assertFalse(controles["actions_externes_autorisees"])
        self.assertTrue(controles["raisons_verrous_ouverts"])


class TestAnalyseConforme(BaseOrchestrateur):
    """Scénario complet : une référence entre dans le corpus, est vérifiée, puis est utilisée.

    La référence utilisée est explicitement FICTIVE : on teste le mécanisme, pas
    une règle de droit.
    """

    def _ajouter_reference_verifiee(self):
        ref_id = base.ajouter_reference(
            titre_officiel="TEXTE DE TEST — CONTENU FICTIF, aucune valeur juridique",
            type_texte="loi",
            source_nom="Centre National de Documentation Juridique",
            source_url="https://www.cndj.ci/bases-de-recherche/textes-legislatifs-et-reglementaires.html",
            date_consultation="2026-10-16",
            numero_texte="TEST-0001",
            articles="Article fictif 1",
            domaine="logement_baux_foncier",
            extrait_texte="Extrait fictif de test, sans portée juridique.",
            texte_complet_present=True,
            chemin=self.chemin_db,
        )
        base.promouvoir_verification(
            ref_id, "VERIFIE",
            preuve_url="https://www.cndj.ci/bases-de-recherche/textes-legislatifs-et-reglementaires.html",
            preuve_empreinte="sha256:" + "b" * 64,
            date_consultation="2026-10-16",
            motif="test : consultation enregistrée",
            chemin=self.chemin_db,
        )
        return ref_id

    def test_analyse_conforme_aboutit(self):
        ref_id = self._ajouter_reference_verifiee()
        self.agent.ouvrir_dossier("TEST_ORCH_CONFORME", DEMANDE_LEGITIME)
        analyse = A.nouvelle_analyse("TEST_ORCH_CONFORME", ["logement_baux_foncier"])
        A.ajouter_regle(analyse, ref_id, "Le texte enregistré encadre la restitution du dépôt.")
        A.ajouter_application(analyse, "Cette règle s'applique aux faits déclarés.",
                              ref_ids=[ref_id], faits_ids=["F01"])
        cloture = self.agent.clore_dossier("TEST_ORCH_CONFORME", analyse)
        self.assertEqual(cloture["statut_reponse"], "ANALYSE_CONFORME")
        self.assertEqual(cloture["analyse"]["validite"], "CONFORME")
        trace = json.load(open(cloture["traceabilite"], encoding="utf-8"))
        self.assertTrue(trace["articles_effectivement_verifies"])
        self.assertIn("aucune_validation_humaine", trace["champs_non_renseignes"])

    def test_analyse_avec_nombre_invente_refusee(self):
        ref_id = self._ajouter_reference_verifiee()
        self.agent.ouvrir_dossier("TEST_ORCH_INVENTION", DEMANDE_LEGITIME)
        analyse = A.nouvelle_analyse("TEST_ORCH_INVENTION", ["logement_baux_foncier"])
        A.ajouter_regle(analyse, ref_id, "Le délai de restitution est de 90 jours.")
        A.ajouter_application(analyse, "Le bailleur avait 90 jours pour agir.",
                              ref_ids=[ref_id], faits_ids=["F01"])
        cloture = self.agent.clore_dossier("TEST_ORCH_INVENTION", analyse)
        self.assertEqual(cloture["statut_reponse"], "ANALYSE_REFUSEE")
        codes = [v["code"] for v in cloture["controles_qualite"]["violations"]]
        self.assertIn("NOMBRE_NON_SOUTENU", codes)

    def test_reference_citee_mais_absente_du_corpus(self):
        self.agent.ouvrir_dossier("TEST_ORCH_INVENTION", DEMANDE_LEGITIME)
        analyse = A.nouvelle_analyse("TEST_ORCH_INVENTION", ["logement_baux_foncier"])
        A.ajouter_regle(analyse, "REF-INVENTEE-PAR-LE-MODELE", "Le texte prévoit X.")
        cloture = self.agent.clore_dossier("TEST_ORCH_INVENTION", analyse)
        codes = [v["code"] for v in cloture["controles_qualite"]["violations"]]
        self.assertIn("REF_INCONNUE", codes)
        self.assertIn("REF-INVENTEE-PAR-LE-MODELE",
                      cloture["controles_qualite"]["references_inconnues"])

    def test_cloture_sans_dossier_ouvert_echoue(self):
        """Le refus doit être EXPLICITE : « aucun dossier ouvert », pas un
        FileNotFoundError qui ferait passer une absence pour une panne."""
        with self.assertRaises(ValueError) as contexte:
            self.agent.clore_dossier("TEST_ORCH_CONFORME",
                                     A.nouvelle_analyse("TEST_ORCH_CONFORME", ["travail"]))
        self.assertIn("aucun dossier ouvert", str(contexte.exception))


class TestTracabilite(BaseOrchestrateur):
    def test_les_faits_apparaissent_dans_la_distinction(self):
        """Un dossier de traçabilité qui perd ses faits se lit comme un dossier sans faits."""
        self.agent.ouvrir_dossier("TEST_ORCH_LEGITIME", DEMANDE_LEGITIME)
        cloture = self.agent.clore_dossier(
            "TEST_ORCH_LEGITIME", A.nouvelle_analyse("TEST_ORCH_LEGITIME", ["logement_baux_foncier"]))
        trace = json.load(open(cloture["traceabilite"], encoding="utf-8"))
        distinction = trace["distinction_faits_regles_analyse"]
        self.assertTrue(distinction["faits"], "les faits déclarés ont disparu de la traçabilité")
        self.assertEqual(distinction["faits"][0]["etat"], "DECLARE_PAR_L_UTILISATEUR")
        self.assertTrue(distinction["faits_declares_non_etablis"])
        self.assertNotIn("distinction_faits_regles_analyse", trace["champs_non_renseignes"])

    def test_le_dossier_nomme_ce_qui_manque(self):
        self.agent.ouvrir_dossier("TEST_ORCH_LEGITIME", DEMANDE_LEGITIME)
        cloture = self.agent.clore_dossier(
            "TEST_ORCH_LEGITIME", A.nouvelle_analyse("TEST_ORCH_LEGITIME", ["logement_baux_foncier"]))
        trace = json.load(open(cloture["traceabilite"], encoding="utf-8"))
        for champ in ("demande_et_resume_neutre", "questions_posees_et_informations_manquantes",
                      "distinction_faits_regles_analyse", "incertitudes_exceptions_limites",
                      "plan_action_et_raison", "resultats_controles_qualite"):
            self.assertIn(champ, trace)
        self.assertTrue(trace["champs_non_renseignes"])
        self.assertEqual(trace["validations_humaines"], [])

    def test_validation_humaine_enregistree(self):
        self.agent.ouvrir_dossier("TEST_ORCH_LEGITIME", DEMANDE_LEGITIME)
        cloture = self.agent.clore_dossier(
            "TEST_ORCH_LEGITIME",
            A.nouvelle_analyse("TEST_ORCH_LEGITIME", ["logement_baux_foncier"]),
            validations_humaines=[{"par": "utilisateur:jeff", "objet": "relecture du plan",
                                   "decision": "approuve"}])
        trace = json.load(open(cloture["traceabilite"], encoding="utf-8"))
        self.assertEqual(len(trace["validations_humaines"]), 1)
        self.assertNotIn("aucune_validation_humaine", trace["champs_non_renseignes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
