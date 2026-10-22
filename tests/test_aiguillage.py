# -*- coding: utf-8 -*-
"""Aiguillage : plusieurs procédures candidates → le citoyen tranche, jamais le modèle.

L'ambiguïté naît du modèle, pas du moteur : sans modèle, le déterminisme retient
au plus une fiche (79 fois sur 92) ou une paire complémentaire (13 fois). Avec un
modèle, « récupérer son appartement » produit quatre procédures alternatives.

Ces tests utilisent un faux fournisseur — le LLM reste désactivé.
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
from core import aiguillage, catalogue
from core.conversation import Conversation

APPARTEMENT = "Mon propriétaire veut récupérer son appartement pour y habiter."
NAISSANCE = "Je veux déclarer la naissance de mon enfant à l'état civil."
CAUTION = "Mon bailleur refuse de me rendre la caution de deux mois."
SALAIRE = "On a saisi mon salaire ce mois-ci."


class FauxFournisseur(object):
    nom = "factice"

    def __init__(self, fiches):
        self.fiches = fiches

    def disponible(self):
        return True

    def completer(self, systeme, message, delai=None, max_tokens=1200):
        return json.dumps({"fiches": self.fiches, "suggestions": [], "resume": None})


class Base(unittest.TestCase):
    FICHES = []

    def tearDown(self):
        for identifiant in self.FICHES:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)
        del self.FICHES[:]

    def ouvrir(self, identifiant, question, fiches):
        self.FICHES.append(identifiant)
        conversation = Conversation(fournisseur_langage=FauxFournisseur(fiches))
        return conversation, conversation.demarrer(identifiant, question)


class LogementAmbigu(Base):
    def test_quatre_procedures_declenchent_un_choix_sans_analyse(self):
        _, vue = self.ouvrir("test_aig_appart", APPARTEMENT,
                             ["LOGEME_414", "LOGEME_440", "LOGEME_443", "LOGEME_445"])
        self.assertEqual(vue["etape"], "aiguillage")
        self.assertNotIn("reponse", vue, "une analyse a été produite avant le choix")
        cles = [o["cle"] for o in vue["options"]]
        # LOGEME_414 (forme du bail) n'est pas dans la table : elle est écartée.
        self.assertEqual(cles, ["LOGEME_440", "LOGEME_445", "LOGEME_443"])
        self.assertTrue(vue["option_aucune"])
        for option in vue["options"]:
            self.assertTrue(option["libelle"].strip())
            self.assertNotIn("résiliation", option["libelle"].lower()[:12])

    def test_le_choix_restreint_a_une_seule_procedure(self):
        conversation, _ = self.ouvrir("test_aig_choix", APPARTEMENT,
                                      ["LOGEME_414", "LOGEME_440", "LOGEME_443", "LOGEME_445"])
        vue = conversation.repondre("test_aig_choix", {"aiguillage": "LOGEME_440"})
        self.assertEqual(vue["etape"], "clarification")
        articles = [f["article"] for f in vue["fiches_identifiees"]]
        self.assertEqual(articles, ["440"], "plusieurs procédures ont survécu au choix")

    def test_aucune_situation_conclut_impossible(self):
        conversation, _ = self.ouvrir("test_aig_aucune", APPARTEMENT,
                                      ["LOGEME_414", "LOGEME_440", "LOGEME_443", "LOGEME_445"])
        vue = conversation.repondre("test_aig_aucune", {"aiguillage": "aucune"})
        self.assertEqual(vue["etape"], "reponse")
        self.assertEqual(vue["reponse"]["statut_reponse"], "CONCLUSION_IMPOSSIBLE")

    def test_selection_invalide_ne_conclut_pas(self):
        conversation, _ = self.ouvrir("test_aig_invalide", APPARTEMENT,
                                      ["LOGEME_414", "LOGEME_440", "LOGEME_443", "LOGEME_445"])
        vue = conversation.repondre("test_aig_invalide", {"aiguillage": "LOGEME_999"})
        self.assertEqual(vue["etape"], "aiguillage")
        self.assertIn("erreur_selection", vue)
        self.assertNotIn("reponse", vue, "une conclusion a été tirée d'une sélection invalide")

    def test_selection_absente_ne_conclut_pas(self):
        conversation, _ = self.ouvrir("test_aig_absente", APPARTEMENT,
                                      ["LOGEME_414", "LOGEME_440", "LOGEME_443", "LOGEME_445"])
        vue = conversation.repondre("test_aig_absente", {})
        self.assertEqual(vue["etape"], "aiguillage")

    def test_boucle_bornee_puis_conclusion_prudente(self):
        conversation, _ = self.ouvrir("test_aig_boucle", APPARTEMENT,
                                      ["LOGEME_414", "LOGEME_440", "LOGEME_443", "LOGEME_445"])
        etapes = []
        for _ in range(5):
            vue = conversation.repondre("test_aig_boucle", {"aiguillage": "n-importe-quoi"})
            etapes.append(vue["etape"])
        self.assertEqual(etapes[:3], ["aiguillage"] * 3)
        self.assertEqual(etapes[3], "reponse", "la question a été reposée indéfiniment")
        self.assertEqual(vue["reponse"]["statut_reponse"], "CONCLUSION_IMPOSSIBLE")

    def test_pas_de_second_aiguillage_apres_choix(self):
        conversation, _ = self.ouvrir("test_aig_unique", APPARTEMENT,
                                      ["LOGEME_414", "LOGEME_440", "LOGEME_443", "LOGEME_445"])
        conversation.repondre("test_aig_unique", {"aiguillage": "LOGEME_445"})
        vue = conversation.repondre("test_aig_unique", {})
        self.assertNotEqual(vue.get("etape"), "aiguillage", "un second aiguillage a été ouvert")


class AbsenceDeCouverture(Base):
    def test_naissance_conclut_impossible(self):
        """Aucune fiche ne traite de la déclaration de naissance : on se tait."""
        _, vue = self.ouvrir("test_aig_naissance", NAISSANCE,
                             ["FAMILL_1", "FAMILL_19", "FAMILL_20", "FAMILL_21"])
        self.assertEqual(vue["etape"], "hors_catalogue")
        self.assertEqual(vue["reponse"]["statut_reponse"], "CONCLUSION_IMPOSSIBLE")

    def test_propositions_rejetees_ne_detruisent_pas_la_fiche_deterministe(self):
        """Trois propositions hors sujet : la fiche établie par le moteur reste."""
        # LOGEME_445 (expulsion) est du bon domaine mais de la mauvaise
        # procédure : le contrôle de voisinage doit l'écarter et laisser 416.
        _, vue = self.ouvrir("test_aig_rejets", CAUTION, ["LOGEME_445", "LOGEME_443"])
        self.assertEqual(vue["etape"], "clarification")
        self.assertEqual([f["article"] for f in vue["fiches_identifiees"]], ["416"],
                         "une proposition rejetée a pris la place de la fiche vérifiée")


class NonRegression(Base):
    def test_caution_reste_une_clarification_normale(self):
        _, vue = self.ouvrir("test_aig_caution", CAUTION, ["LOGEME_416"])
        self.assertEqual(vue["etape"], "clarification")
        self.assertEqual([f["article"] for f in vue["fiches_identifiees"]], ["416"])

    def test_salaire_saisi_reste_une_clarification_normale(self):
        _, vue = self.ouvrir("test_aig_salaire", SALAIRE, ["OHADA_173", "OHADA_153"])
        self.assertEqual(vue["etape"], "clarification")
        self.assertEqual([f["article"] for f in vue["fiches_identifiees"]], ["173"])

    def test_paire_complementaire_non_aiguillee(self):
        """Désaveu + délai de désaveu : deux fiches du moteur, complémentaires."""
        vue = Conversation().demarrer("test_aig_paire", "Bonjour, desaveu.")
        try:
            self.assertEqual(vue["etape"], "clarification")
            self.assertEqual(len(vue["fiches_identifiees"]), 2)
        finally:
            shutil.rmtree(str(config.dossier_utilisateur("test_aig_paire")), ignore_errors=True)


class TableDAiguillage(unittest.TestCase):
    def test_la_table_est_signee_a_valider(self):
        table = aiguillage.charger()
        self.assertEqual(table["statut"], "A_VALIDER_PAR_JURISTE")

    def test_les_fiches_citees_existent_dans_le_catalogue(self):
        connues = {f["id"] for f in catalogue.charger()}
        for entree in aiguillage.charger()["situations"]:
            for option in entree["options"]:
                self.assertIn(option["fiche"], connues, option["fiche"])

    def test_aucune_fiche_a_valider_dans_la_table(self):
        a_valider = set()
        chemin = os.path.join(RACINE, "KNOWLEDGE", "catalogue_a_valider.json")
        if os.path.isfile(chemin):
            with open(chemin, encoding="utf-8") as flux:
                a_valider = {f["id"] for f in json.load(flux)["fiches"]}
        for entree in aiguillage.charger()["situations"]:
            for option in entree["options"]:
                self.assertNotIn(option["fiche"], a_valider)

    def test_une_seule_fiche_ne_declenche_jamais_l_aiguillage(self):
        fiches = catalogue.charger()
        une = [f for f in fiches if f["id"] == "LOGEME_440"]
        self.assertIsNone(aiguillage.situation_pour(une, catalogue=fiches))


if __name__ == "__main__":
    unittest.main()
