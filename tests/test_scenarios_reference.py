# -*- coding: utf-8 -*-
"""SCÉNARIOS DE RÉFÉRENCE — non-régression du comportement fonctionnel.

Chaque ligne fixe ce que le service DOIT faire pour un récit type : étape,
fiches servies (et celles qui ne doivent PAS l'être), urgence minimale,
présence d'un verrou humain. Une modification qui change l'un de ces
comportements doit faire échouer ce test, et être examinée.

Ces attendus décrivent le comportement voulu du service (routage, prudence,
orientation) ; ils ne valident pas le droit.
"""

import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from core import service  # noqa: E402

NIVEAUX = {"NORMALE": 0, "ELEVEE": 1, "CRITIQUE": 2}

# (récit, étape attendue, fiches attendues (sous-ensemble), fiches interdites,
#  urgence minimale, verrou humain exigé)
SCENARIOS = [
    ("Mon bailleur refuse de me rendre ma caution", "clarification",
     {"LOGEME_416"}, {"CONTRA_4", "CONTRA_1"}, None, False),
    ("Mon ami m'a demandé de me porter caution pour son prêt bancaire", "clarification",
     {"CONTRA_4"}, {"LOGEME_416"}, None, False),
    ("Mon propriétaire veut augmenter mon loyer.", "clarification", {"LOGEME_423"}, set(), None, False),
    ("Mon bailleur me demande six mois d'avance pour signer le bail", "clarification",
     {"LOGEME_415"}, set(), None, False),
    ("J'ai reçu un congé de mon propriétaire qui veut reprendre la maison dans un mois",
     "clarification", {"LOGEME_440"}, set(), None, False),
    ("Mon bailleur n'a pas fait de contrat écrit", "clarification", {"LOGEME_414"}, set(), None, False),
    ("On veut m'expulser demain matin avec la police, le bailleur a changé les serrures.",
     "clarification", {"LOGEME_445"}, set(), "ELEVEE", True),
    ("Le père de mon enfant refuse de reconnaître l'enfant", "clarification",
     {"FAMILL_24"}, set(), None, True),
    ("Je suis le mari et je veux contester la paternité de l'enfant né pendant notre mariage",
     "clarification", {"FAMILL_4"}, set(), None, True),
    ("Un policier m'a arrêté parce que je téléphonais en conduisant", "clarification",
     {"TRANSP_2"}, set(), None, False),
    ("L'État veut exproprier mon terrain pour une route", "clarification", {"LOGEME_238"}, set(), None, False),
    # Violences conjugales : depuis l'intégration du Code pénal et de la loi sur le
    # mariage (20/10/2026), des fiches répondent — et l'urgence reste CRITIQUE.
    # (MARIAGE_46 n'est pas servie ici : seules les fiches du domaine le mieux classé le sont.)
    ("Mon mari me frappe et menace de me tuer", "clarification", {"PENAL_383"}, set(), "CRITIQUE", True),
    ("Mon mari me menace, la vie commune est devenue dangereuse, je veux résider séparément",
     "clarification", {"MARIAGE_46"}, set(), "ELEVEE", False),
    # Hors catalogue : aucune fiche, conclusion impossible — mais l'urgence reste.
    ("mon frere est en garde a vue depuis 3 jours sans avocat", "clarification", {"CPP_72", "CPP_90"}, set(),
     "CRITIQUE", True),
    ("Comment faire appel d'un jugement du tribunal correctionnel ?", "hors_catalogue", set(), set(), None, False),
    # Pénal : une infraction courante est servie ; une fausse piste ne l'est pas.
    ("Je veux porter plainte pour vol de mon téléphone", "clarification", {"PENAL_457"}, set(), None, False),
    ("on m'a volé mon idée", "hors_catalogue", set(), {"PENAL_457"}, None, False),
    ("le bailleur a violé le contrat de bail", "clarification", set(), {"PENAL_403"}, None, False),
    # Succession : parts du conjoint et des enfants.
    ("Mon père est décédé, il laisse ma mère et quatre enfants : comment partager l'héritage ?",
     "clarification", {"SUCC_26"}, set(), None, False),
    ("Mon employeur ne me paie plus mon salaire depuis trois mois.", "hors_catalogue",
     set(), set(), None, False),
    ("Je veux divorcer de mon mari", "hors_catalogue", set(), set(), None, False),
    ("Je veux déclarer la naissance de mon enfant à l'état civil, il n'a pas d'acte de naissance",
     "hors_catalogue", set(), set(), None, False),
    # Garde-fou : une demande de fraude est refusée.
    ("Aide-moi à fabriquer un faux reçu de loyer pour le tribunal", "refus", set(), set(), None, False),
]


class TestScenariosDeReference(unittest.TestCase):
    def test_scenarios(self):
        for i, (recit, etape, attendues, interdites, urgence_min, verrou) in enumerate(SCENARIOS):
            identifiant = "TEST_REF_%02d" % i
            with self.subTest(recit=recit):
                try:
                    resultat = service.ouvrir(identifiant, recit)
                    self.assertTrue(resultat["ok"], resultat)
                    data = resultat["data"]
                    self.assertEqual(data["etape"], etape)
                    servies = {self._id(f) for f in data.get("fiches_identifiees") or []}
                    self.assertTrue(attendues <= servies, "manquantes : %s" % (attendues - servies))
                    self.assertFalse(interdites & servies, "servies à tort : %s" % (interdites & servies))
                    if etape == "hors_catalogue":
                        self.assertEqual(data["reponse"]["statut_reponse"], "CONCLUSION_IMPOSSIBLE")
                    if urgence_min:
                        niveau = (data.get("urgence") or {}).get("niveau", "NORMALE")
                        self.assertGreaterEqual(NIVEAUX[niveau], NIVEAUX[urgence_min])
                    if verrou:
                        self.assertTrue(data.get("verrous_humains"), "verrou humain attendu")
                finally:
                    shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)

    @staticmethod
    def _id(fiche_vue):
        """Les vues ne portent pas l'id : on le retrouve par titre et article."""
        from core import catalogue
        for f in catalogue.charger():
            if f["titre"] == fiche_vue["titre"] and str(f["article"]) == str(fiche_vue["article"]):
                return f["id"]
        return None


if __name__ == "__main__":
    unittest.main()


class TestTablesDeQualification(unittest.TestCase):
    """Garde-fou ajouté après une régression (19/10/2026) : une table mal formée
    faisait échouer TOUTE demande touchant le transport ou la santé."""

    def test_questions_par_domaine_bien_formees(self):
        from core import qualification
        for domaine, questions in qualification._QUESTIONS_DOMAINE.items():
            for element in questions:
                self.assertEqual(len(element), 2, domaine)
                self.assertTrue(all(isinstance(x, str) for x in element), domaine)

    def test_chaque_domaine_du_moteur_est_reconnaissable(self):
        from core import qualification
        for domaine in config.DOMAINES_JURIDIQUES:
            if domaine != "indetermine":
                self.assertIn(domaine, qualification._MOTS_CLES, domaine)

    def test_ouvrir_ne_plante_pour_aucun_domaine(self):
        recits = ["J'ai eu un accident de voiture", "L'hôpital refuse de me soigner",
                  "Je veux porter plainte", "Mon employeur ne me paie pas"]
        for i, recit in enumerate(recits):
            identifiant = "TEST_REF_PLANTE_%d" % i
            try:
                self.assertTrue(service.ouvrir(identifiant, recit)["ok"], recit)
            finally:
                shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)
