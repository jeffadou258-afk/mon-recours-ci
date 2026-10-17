# -*- coding: utf-8 -*-
"""Analyse : la traçabilité est vérifiée mécaniquement, l'invention est refusée."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import analyse as A  # noqa: E402


def ref(ref_id, etat="VERIFIE", extrait="", complet=True, articles="Article 1"):
    return {
        "ref_id": ref_id,
        "titre_officiel": "Texte de test (contenu fictif)",
        "articles": articles,
        "numero_texte": "TEST-0000",
        "date_publication": "2020-01-01",
        "extrait_texte": extrait,
        "texte_complet_present": 1 if complet else 0,
        "etat_verification": etat,
    }


def codes(violations):
    return [v["code"] for v in violations]


class TestReglesSansSource(unittest.TestCase):
    def test_regle_sans_ref_id(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, None, "Le préavis est obligatoire.")
        self.assertIn("REGLE_SANS_SOURCE", codes(A.valider(analyse)))

    def test_reference_inconnue(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-ABSENTE", "Le préavis est obligatoire.")
        violations = A.valider(analyse, references={})
        self.assertIn("REF_INCONNUE", codes(violations))

    def test_reference_vide(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        vide = ref("REF-VIDE")
        vide["articles"] = ""
        vide["extrait_texte"] = ""
        vide["titre_officiel"] = ""
        A.ajouter_regle(analyse, "REF-VIDE", "Une règle.")
        self.assertIn("REF_VIDE", codes(A.valider(analyse, references={"REF-VIDE": vide})))


class TestApplications(unittest.TestCase):
    def test_application_sans_regle(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_application(analyse, "La règle s'applique.", ref_ids=[], faits_ids=["F01"])
        self.assertIn("APPLICATION_SANS_REGLE", codes(A.valider(analyse)))

    def test_application_citant_une_regle_non_enoncee(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_application(analyse, "Application.", ref_ids=["REF-1"], faits_ids=["F01"])
        self.assertIn("APPLICATION_SANS_REGLE", codes(A.valider(analyse)))

    def test_application_sans_fait(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Règle.")
        A.ajouter_application(analyse, "Application.", ref_ids=["REF-1"], faits_ids=[])
        violations = A.valider(analyse, references={"REF-1": ref("REF-1")})
        self.assertIn("APPLICATION_SANS_FAIT", codes(violations))


class TestHypothesesEtCitations(unittest.TestCase):
    def test_hypothese_sans_condition_de_conclusion(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_hypothese(analyse, "Il pourrait s'agir d'un abus.", pour_conclure="")
        self.assertIn("HYPOTHESE_SANS_CONDITION", codes(A.valider(analyse)))

    def test_hypothese_complete_conforme(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Règle enregistrée.")
        A.ajouter_application(analyse, "Application aux faits.", ref_ids=["REF-1"], faits_ids=["F01"])
        A.ajouter_hypothese(analyse, "Piste possible.",
                            pour_conclure="Obtenir le contrat écrit signé.")
        self.assertEqual(A.valider(analyse, references={"REF-1": ref("REF-1")}), [])
        self.assertEqual(analyse["validite"], "CONFORME")

    def test_citation_absente_du_texte_enregistre(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Le texte parle de restitution.",
                        citation="« trois mois d'indemnité sont dus »")
        violations = A.valider(analyse, references={"REF-1": ref("REF-1", extrait="restitution du dépôt")})
        self.assertIn("CITATION_NON_VERIFIABLE", codes(violations))

    def test_citation_presente_dans_l_extrait(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Le texte parle de restitution.",
                        citation="« restitution du dépôt »")
        violations = A.valider(analyse, references={"REF-1": ref("REF-1", extrait="restitution du dépôt")})
        self.assertNotIn("CITATION_NON_VERIFIABLE", codes(violations))

    def test_citation_exige_des_guillemets(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        with self.assertRaises(ValueError):
            A.ajouter_regle(analyse, "REF-1", "Énoncé.", citation="citation sans guillemets")


class TestIncertitudes(unittest.TestCase):
    def test_reference_non_verifiee_sans_incertitude_declaree(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Règle appuyée sur un texte non vérifié.")
        violations = A.valider(analyse, references={"REF-1": ref("REF-1", etat="NON_VERIFIE")})
        self.assertIn("INCERTITUDE_NON_DECLAREE", codes(violations))

    def test_incertitude_declaree_leve_la_violation(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Règle appuyée sur un texte non vérifié.")
        A.ajouter_application(analyse, "Application.", ref_ids=["REF-1"], faits_ids=["F01"])
        A.declarer_incertitude(analyse, "REF-1", "L'état de vérification est NON_VERIFIE.")
        violations = A.valider(analyse, references={"REF-1": ref("REF-1", etat="NON_VERIFIE")})
        self.assertNotIn("INCERTITUDE_NON_DECLAREE", codes(violations))


class TestNombreNonSoutenu(unittest.TestCase):
    def test_delai_invente_refuse(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Le délai applicable est de 15 jours.")
        violations = A.valider(
            analyse, references={"REF-1": ref("REF-1", extrait="aucun délai mentionné")},
            faits_texte="Mon employeur ne m'a pas payé mon salaire.",
        )
        self.assertIn("NOMBRE_NON_SOUTENU", codes(violations))

    def test_montant_des_faits_accepte(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Le montant réclamé s'élève à 250 000 FCFA.")
        A.ajouter_application(analyse, "Application au montant de 250 000 FCFA.",
                              ref_ids=["REF-1"], faits_ids=["F01"])
        violations = A.valider(
            analyse, references={"REF-1": ref("REF-1", extrait="montant")},
            faits_texte="Le salaire impayé est de 250000 FCFA selon ma fiche de paie.",
        )
        self.assertNotIn("NOMBRE_NON_SOUTENU", codes(violations))

    def test_controle_desactive_si_aucun_fait_fourni(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Le délai est de 15 jours.")
        violations = A.valider(analyse, references={"REF-1": ref("REF-1")})
        self.assertNotIn("NOMBRE_NON_SOUTENU", codes(violations))


class TestDomaineEtConclusion(unittest.TestCase):
    def test_domaine_indetermine(self):
        analyse = A.nouvelle_analyse("D1", [])
        self.assertIn("DOMAINE_INDETERMINE", codes(A.valider(analyse)))

    def test_peut_conclure_sans_reference(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        ok, raisons = A.peut_conclure(analyse)
        self.assertFalse(ok)
        self.assertTrue(any("AUCUNE_REFERENCE_VERIFIEE" in r for r in raisons))

    def test_peut_conclure_avec_regle_et_application(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, "REF-1", "Règle.")
        A.ajouter_application(analyse, "Application.", ref_ids=["REF-1"], faits_ids=["F01"])
        references = {"REF-1": ref("REF-1")}
        ok, raisons = A.peut_conclure(analyse, references=references)
        self.assertTrue(ok, raisons)

    def test_exiger_conformite_leve(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, None, "Règle orpheline.")
        with self.assertRaises(ValueError) as ctx:
            A.exiger_conformite(analyse)
        self.assertIn("REGLE_SANS_SOURCE", str(ctx.exception))

    def test_validite_enregistree(self):
        analyse = A.nouvelle_analyse("D1", ["travail"])
        A.ajouter_regle(analyse, None, "Règle orpheline.")
        A.valider(analyse)
        self.assertEqual(analyse["validite"], "REFUSEE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
