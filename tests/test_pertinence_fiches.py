# -*- coding: utf-8 -*-
"""Une fiche proposée par un modèle ne doit jamais entrer sans contrôle indépendant.

Le défaut corrigé : `Conversation.demarrer` remplaçait la sélection déterministe
par la liste du modèle dès que celle-ci était non vide. Le seul contrôle était
« la fiche existe au catalogue ». Un modèle hors sujet imposait donc sa fiche.

Ces tests vérifient le contrôle ajouté (`catalogue.valider_fiches_proposees`),
puis son branchement réel dans la conversation avec un faux fournisseur. Le LLM
reste désactivé en production : aucun appel réseau n'est fait ici.
"""
import json
import os
import shutil
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import config
from core import catalogue
from core.conversation import Conversation


class FournisseurFactice(object):
    """Répond une charge JSON fixe. Aucun réseau, aucune clé."""

    nom = "factice"

    def __init__(self, charge):
        self.charge = charge

    def disponible(self):
        return True

    def completer(self, systeme, message, delai=None, max_tokens=1200):
        return json.dumps(self.charge)


def fiche(identifiant, domaine, titre, declencheurs):
    return {"id": identifiant, "domaine": domaine, "titre": titre,
            "declencheurs": list(declencheurs), "article": "1",
            "numero_texte": "0000-000", "citation": "", "lecture": "",
            "faits_requis": [], "etape_plan": ""}


class PortesDeRelevance(unittest.TestCase):
    """Le contrôle, isolé, sur des fiches maîtrisées."""

    def setUp(self):
        self.fiches = [
            fiche("F_CONSO", "consommation", "Vente à distance et retour du produit",
                  ["vente à distance", "retour du produit", "achat en ligne"]),
            fiche("F_ASSO", "associations_organisations_religieuses",
                  "Déclaration préalable d'une association",
                  ["créer une association", "déclarer une association"]),
            fiche("F_LOGEMENT", "logement_baux_foncier", "Dépôt de garantie (caution)",
                  ["caution", "depot de garantie"]),
        ]

    def test_porte_a_un_declencheur_suffit(self):
        retenues, rejets = catalogue.valider_fiches_proposees(
            ["F_LOGEMENT"], "Mon bailleur garde ma caution de deux mois.",
            fiches=self.fiches, domaines=["logement_baux_foncier"])
        self.assertEqual([f["id"] for f in retenues], ["F_LOGEMENT"])
        self.assertEqual(rejets, [])

    def test_porte_a_exige_le_domaine_pour_un_declencheur_d_un_seul_mot(self):
        """« caution » seul ne sert pas une fiche si son domaine n'est pas reconnu.

        C'est la règle déjà appliquée par `pour_demande`, rejouée ici : le
        cautionnement OHADA ne doit pas répondre à une caution de logement.
        """
        retenues, rejets = catalogue.valider_fiches_proposees(
            ["F_LOGEMENT"], "Mon bailleur garde ma caution de deux mois.",
            fiches=self.fiches, domaines=["contrats_dettes_commerce"],
            scores={"contrats_dettes_commerce": {"score": 3}, "logement_baux_foncier": {"score": 0}})
        self.assertEqual(retenues, [])
        self.assertEqual(len(rejets), 1)

    def test_porte_b_domaine_qualifie_suffit(self):
        """Aucun mot-clé ne tombe, mais le domaine est qualifié : le modèle sert.

        C'est le cas réel « l'argent versé à l'entrée » : la fiche parle de
        « dépôt de garantie », aucun mot ne coïncide, et c'est précisément là
        qu'un modèle apporte quelque chose. Le domaine, lui, reste déterministe.
        """
        retenues, _ = catalogue.valider_fiches_proposees(
            ["F_CONSO"], "Le vendeur refuse de reprendre l'article acheté la semaine dernière.",
            fiches=self.fiches, domaines=["consommation"])
        self.assertEqual([f["id"] for f in retenues], ["F_CONSO"])

    def test_un_declencheur_litteral_gagne_meme_hors_domaine(self):
        """Règle déterministe existante, inchangée : un déclencheur littéral suffit.

        Le domaine n'est exigé que pour un déclencheur d'UN SEUL mot (garde déjà
        posée par `pour_demande`). Ce test fixe ce comportement pour qu'on ne le
        modifie pas par inadvertance en croyant durcir le contrôle.
        """
        retenues, rejets = catalogue.valider_fiches_proposees(
            ["F_CONSO"],
            "Vente à distance : je veux le retour du produit et un achat en ligne remboursé.",
            fiches=self.fiches, domaines=["famille_mariage_filiation"])
        self.assertEqual([f["id"] for f in retenues], ["F_CONSO"])
        self.assertEqual(rejets, [])

    def test_rejet_hors_domaine(self):
        retenues, rejets = catalogue.valider_fiches_proposees(
            ["F_ASSO"], "Je veux déclarer la naissance de mon enfant à l'état civil.",
            fiches=self.fiches, domaines=["famille_mariage_filiation"])
        self.assertEqual(retenues, [])
        self.assertEqual(rejets[0]["raison"], "domaine hors qualification")

    def test_rejet_fiche_inconnue(self):
        retenues, rejets = catalogue.valider_fiches_proposees(
            ["F_INVENTEE"], "N'importe quoi.", fiches=self.fiches, domaines=["consommation"])
        self.assertEqual(retenues, [])
        self.assertEqual(rejets[0]["raison"], "absente du catalogue")

    def test_liste_vide_ne_produit_ni_fiche_ni_erreur(self):
        self.assertEqual(catalogue.valider_fiches_proposees([], "x", fiches=self.fiches), ([], []))

    def test_doublon_compte_une_fois(self):
        retenues, _ = catalogue.valider_fiches_proposees(
            ["F_LOGEMENT", "F_LOGEMENT"], "Mon bailleur garde ma caution.",
            fiches=self.fiches, domaines=["logement_baux_foncier"])
        self.assertEqual(len(retenues), 1)


class SurLeCatalogueReel(unittest.TestCase):
    """Les deux erreurs observées en production, rejouées sur les vraies fiches."""

    @classmethod
    def setUpClass(cls):
        cls.fiches = catalogue.charger()

    def test_naissance_n_ouvre_pas_la_consommation(self):
        retenues, rejets = catalogue.valider_fiches_proposees(
            ["LOGEME_416"],
            "Je veux déclarer la naissance de mon enfant à l'état civil, il n'a pas d'acte de naissance.",
            fiches=self.fiches,
            domaines=["famille_mariage_filiation", "administratif_voies_de_recours"])
        self.assertEqual(retenues, [], "une fiche logement a été acceptée pour une naissance")
        self.assertTrue(rejets)

    def test_saisie_bancaire_n_ouvre_pas_une_fiche_penale(self):
        penale = [f for f in self.fiches if f["domaine"] == "penal_procedure_penale"][:2]
        retenues, _ = catalogue.valider_fiches_proposees(
            [f["id"] for f in penale],
            "Je veux saisir le compte bancaire de mon débiteur qui ne paie pas.",
            fiches=self.fiches, domaines=["contrats_dettes_commerce"])
        self.assertEqual(retenues, [], "une fiche pénale a été acceptée pour une saisie bancaire")

    def test_caution_de_logement_reste_servie(self):
        retenues, _ = catalogue.valider_fiches_proposees(
            ["LOGEME_416"], "Mon bailleur garde ma caution de deux mois.",
            fiches=self.fiches, domaines=["logement_baux_foncier"])
        self.assertEqual([f["id"] for f in retenues], ["LOGEME_416"])


class BranchementDansLaConversation(unittest.TestCase):
    """Le contrôle est-il réellement appliqué ? On fait parler un faux modèle."""

    QUESTIONS = []

    def tearDown(self):
        for identifiant in self.QUESTIONS:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)
        del self.QUESTIONS[:]

    def _demarrer(self, identifiant, demande, charge):
        self.QUESTIONS.append(identifiant)
        return Conversation(fournisseur_langage=FournisseurFactice(charge)).demarrer(identifiant, demande)

    def test_fiche_hors_sujet_proposee_par_le_modele_est_ignoree(self):
        resultat = self._demarrer(
            "test_pertinence_naissance",
            "Je veux déclarer la naissance de mon enfant à l'état civil, il n'a pas d'acte de naissance.",
            {"fiches": ["LOGEME_416"], "suggestions": [], "resume": None})
        charge = json.dumps(resultat, ensure_ascii=False)
        self.assertEqual(resultat["comprehension"]["mode"], "llm", "le faux modèle n'a pas été utilisé")
        self.assertNotIn("LOGEME_416", charge, "la fiche hors sujet a été servie")
        # L'identifiant n'est pas exposé, et le titre apparaît dans la liste de
        # couverture du catalogue : le seul témoin fiable d'une fiche SERVIE est
        # la question qu'elle pose au citoyen.
        self.assertNotIn("bail à usage d'habitation", charge,
                         "les questions du logement ont été posées pour une naissance")
        identifiees = resultat.get("fiches_identifiees") or []
        self.assertEqual([f for f in identifiees if str(f.get("article")) == "416"], [],
                         "l'article 416 a été servi pour une question de naissance")
        self.assertGreaterEqual(resultat["comprehension"]["elements_rejetes"], 1,
                                "le rejet n'est pas compté dans la réponse")

    def test_fiche_a_valider_ne_peut_pas_entrer(self):
        """Les 11 fiches A_VALIDER ne sont pas dans le catalogue : inatteignables."""
        resultat = self._demarrer(
            "test_pertinence_a_valider",
            "Le magasin refuse de me rembourser un produit défectueux.",
            {"fiches": ["CONSO_11_RETOUR_VENTE_DISTANCE"], "suggestions": [], "resume": None})
        charge = json.dumps(resultat, ensure_ascii=False)
        self.assertNotIn("CONSO_11_RETOUR_VENTE_DISTANCE", charge)

    def test_fiche_pertinente_proposee_reste_servie(self):
        resultat = self._demarrer(
            "test_pertinence_caution",
            "Mon bailleur refuse de me rendre la caution de deux mois.",
            {"fiches": ["LOGEME_416"], "suggestions": [], "resume": None})
        charge = json.dumps(resultat, ensure_ascii=False)
        self.assertIn("416", charge, "la fiche pertinente a été perdue par le contrôle")


if __name__ == "__main__":
    unittest.main()
