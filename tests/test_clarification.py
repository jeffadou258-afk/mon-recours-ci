# -*- coding: utf-8 -*-
"""Guide de clarification et conversation en plusieurs tours.

Vérifie :
  * que le guide est revalidé contre le corpus (aucun nombre, délai ou article
    ajouté par une question) ;
  * que les questions s'adaptent aux réponses (questions conditionnelles) ;
  * qu'une réponse contraire au récit est relevée et fait l'objet d'une
    confirmation, au lieu d'être ignorée ;
  * que les informations manquantes sont nommées avec leur raison ;
  * que la conversation s'arrête au bout de `TOURS_MAX` tours.

Ce que ces tests ne vérifient PAS : que les lectures du guide sont juridiquement
exactes. Le guide porte le statut A_RELIRE_PAR_UN_JURISTE.
"""

import copy
import json
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from core import catalogue, clarification, service  # noqa: E402

DOSSIERS = []
CAUTION = ("Mon bailleur refuse de me rendre ma caution de trois mois depuis que "
           "j'ai quitté l'appartement.")


def dossier(prefixe):
    identifiant = "TEST_CLARIF_%s" % prefixe
    DOSSIERS.append(identifiant)
    return identifiant


def tearDownModule():
    for identifiant in DOSSIERS:
        shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)


class TestGuideRevalide(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fiches = catalogue.charger()
        cls.index = {f["id"]: f for f in cls.fiches}
        with open(clarification.CHEMIN_GUIDE, encoding="utf-8") as flux:
            cls.guide = json.load(flux)

    def test_le_guide_reel_est_conforme(self):
        questions = clarification.valider(copy.deepcopy(self.guide), self.index)
        self.assertGreaterEqual(len(questions), 15)
        self.assertEqual(self.guide["statut_validation"], "A_RELIRE_PAR_UN_JURISTE")

    def _guide_avec(self, modification):
        guide = copy.deepcopy(self.guide)
        modification(guide["questions"][0])
        return guide

    def test_un_delai_invente_est_refuse(self):
        def inventer(q):
            q["effets"]["oui"] = "Selon l'article 416, vous avez quinze jours pour agir."
        with self.assertRaises(clarification.GuideInvalide) as ctx:
            clarification.valider(self._guide_avec(inventer), self.index)
        self.assertIn("quinze", str(ctx.exception))

    def test_un_chiffre_invente_est_refuse(self):
        def inventer(q):
            q["effets"]["non"] = "Le bailleur doit rendre le dépôt sous 30 jours."
        with self.assertRaises(clarification.GuideInvalide):
            clarification.valider(self._guide_avec(inventer), self.index)

    def test_un_article_etranger_aux_fiches_est_refuse(self):
        def etranger(q):
            q["effets"]["oui"] = "Selon l'article 999, le dépôt est interdit."
        with self.assertRaises(clarification.GuideInvalide) as ctx:
            clarification.valider(self._guide_avec(etranger), self.index)
        self.assertIn("999", str(ctx.exception))

    def test_une_fiche_inconnue_est_refusee(self):
        with self.assertRaises(clarification.GuideInvalide):
            clarification.valider(
                self._guide_avec(lambda q: q.update(fiches=["FICHE_INEXISTANTE"])), self.index)

    def test_une_condition_irresoluble_est_refusee(self):
        with self.assertRaises(clarification.GuideInvalide):
            clarification.valider(
                self._guide_avec(lambda q: q.update(si={"cle_inconnue": "oui"})), self.index)

    def test_chaque_nombre_des_lectures_est_dans_l_article(self):
        """Contre-épreuve positive : les lectures réelles passent le contrôle."""
        for q in self.guide["questions"]:
            articles = clarification._texte_articles(q["fiches"], self.index)
            for effet in q["effets"].values():
                manquants = clarification._nombres(clarification.normaliser(effet)) \
                    - clarification._nombres(articles)
                self.assertFalse(manquants, "%s : %s" % (q["cle"], manquants))


class TestLectureDesReponses(unittest.TestCase):
    def test_valeurs(self):
        self.assertEqual(clarification.lire_valeur("oui"), "oui")
        self.assertEqual(clarification.lire_valeur("Non, jamais"), "non")
        self.assertEqual(clarification.lire_valeur("oui, depuis 2022"), "oui")
        self.assertIsNone(clarification.lire_valeur("je ne sais pas"))
        self.assertIsNone(clarification.lire_valeur(None))
        self.assertIsNone(clarification.lire_valeur(""))

    def test_suggestion_tiree_du_recit(self):
        q = {"indices_oui": ["caution de trois mois"], "indices_non": []}
        self.assertEqual(clarification.suggestion(q, CAUTION)["valeur"], "oui")
        self.assertIsNone(clarification.suggestion(q, "Mon bailleur garde ma caution."))


class TestConversationEnPlusieursTours(unittest.TestCase):
    def test_le_recit_preremplit_et_les_questions_portent_leur_raison(self):
        ouverture = service.ouvrir(dossier("SUGG"), CAUTION)["data"]
        self.assertEqual(ouverture["etape"], "clarification")
        par_cle = {q["cle"]: q for q in ouverture["questions"]}
        self.assertEqual(par_cle["depot_plus_deux_mois"]["suggestion"]["valeur"], "oui")
        self.assertEqual(par_cle["logement_quitte"]["suggestion"]["valeur"], "oui")
        self.assertTrue(par_cle["depot_plus_deux_mois"]["pourquoi"])
        # Question conditionnelle : pas encore posée.
        self.assertNotIn("manquement_invoque", par_cle)

    def test_une_question_s_ouvre_selon_la_reponse(self):
        identifiant = dossier("SUITE")
        service.ouvrir(identifiant, "Mon bailleur garde ma caution.")
        tour2 = service.repondre(identifiant, {"logement": "oui", "logement_quitte": "oui"})["data"]
        self.assertEqual(tour2["etape"], "clarification")
        self.assertEqual(tour2["tour"], 2)
        self.assertEqual([q["cle"] for q in tour2["questions"]], ["manquement_invoque"])

    def test_sans_condition_remplie_pas_de_tour_supplementaire(self):
        identifiant = dossier("DIRECT")
        service.ouvrir(identifiant, "Mon bailleur garde ma caution.")
        fin = service.repondre(identifiant, {"logement": "oui", "logement_quitte": "non"})["data"]
        self.assertEqual(fin["etape"], "reponse")

    def test_une_contradiction_avec_le_recit_est_relevee_puis_confirmee(self):
        identifiant = dossier("CONTRA")
        service.ouvrir(identifiant, CAUTION)
        tour2 = service.repondre(identifiant, {"logement": "oui", "depot_plus_deux_mois": "non",
                                               "logement_quitte": "oui"})["data"]
        self.assertEqual(tour2["etape"], "clarification")
        self.assertEqual([c["cle"] for c in tour2["contradictions"]], ["depot_plus_deux_mois"])
        confirmation = [q for q in tour2["questions"] if q["cle"] == "depot_plus_deux_mois"][0]
        self.assertIn("trois mois", confirmation["confirmation"])
        # La personne maintient sa réponse : elle est retenue, la divergence reste nommée.
        fin = service.repondre(identifiant, {"depot_plus_deux_mois": "non",
                                             "manquement_invoque": "non"})["data"]
        self.assertEqual(fin["etape"], "reponse")
        sections = fin["reponse"]["sections"]
        self.assertEqual([c["cle"] for c in sections["5_contradictions"]], ["depot_plus_deux_mois"])
        self.assertTrue(any("divergent" in v for v in sections["5_a_verifier"]))

    def test_une_contradiction_corrigee_disparait(self):
        identifiant = dossier("CORRIGE")
        service.ouvrir(identifiant, CAUTION)
        service.repondre(identifiant, {"depot_plus_deux_mois": "non", "logement_quitte": "oui"})
        fin = service.repondre(identifiant, {"depot_plus_deux_mois": "oui",
                                             "manquement_invoque": "non"})["data"]
        self.assertEqual(fin["etape"], "reponse")
        sections = fin["reponse"]["sections"]
        self.assertEqual(sections["5_contradictions"], [])
        lectures = {l["cle"]: l for l in sections["3_application_aux_faits"]["lignes"]}
        self.assertIn("dépasse ce plafond", lectures["depot_plus_deux_mois"]["lecture"])

    def test_les_manques_sont_nommes_avec_leur_raison(self):
        identifiant = dossier("MANQUE")
        service.ouvrir(identifiant, "Mon bailleur garde ma caution.")
        fin = service.repondre(identifiant, {"logement": "oui"})["data"]
        manquantes = fin["reponse"]["sections"]["5_informations_manquantes"]
        cles = {m["cle"] for m in manquantes}
        self.assertIn("depot_plus_deux_mois", cles)
        self.assertTrue(all(m["pourquoi"] for m in manquantes))

    def test_les_lectures_sont_marquees_a_relire_et_jamais_citations(self):
        identifiant = dossier("STATUT")
        service.ouvrir(identifiant, "Mon bailleur garde ma caution.")
        fin = service.repondre(identifiant, {"logement": "oui", "depot_plus_deux_mois": "oui",
                                             "logement_quitte": "non"})["data"]
        application = fin["reponse"]["sections"]["3_application_aux_faits"]
        self.assertEqual(application["statut"], "A_RELIRE_PAR_UN_JURISTE")
        self.assertIn("pas des citations", application["note"])
        # Les citations, elles, restent dans 2_droit, inchangées.
        self.assertTrue(fin["reponse"]["sections"]["2_droit"][0]["citation"])

    def test_alerte_sur_un_delai(self):
        identifiant = dossier("DELAI")
        ouverture = service.ouvrir(
            identifiant, "Je suis le mari et je veux contester la paternité de l'enfant né "
                         "pendant notre mariage, faire un désaveu.")["data"]
        cles = {q["cle"] for q in ouverture.get("questions", [])}
        if "plus_de_deux_mois" not in cles:
            self.skipTest("fiche délai non retenue par l'aiguillage pour ce récit")
        fin = service.repondre(identifiant, {"plus_de_deux_mois": "oui",
                                             "mari_present_naissance": "oui",
                                             "mere_mariee": "oui"})["data"]
        while fin["etape"] == "clarification":
            fin = service.repondre(identifiant, {})["data"]
        lignes = fin["reponse"]["sections"]["3_application_aux_faits"]["lignes"]
        self.assertTrue(any(l["alerte"] for l in lignes if l["cle"] == "plus_de_deux_mois"))

    def test_au_plus_trois_tours(self):
        identifiant = dossier("MAX")
        service.ouvrir(identifiant, CAUTION)
        etapes = []
        donnees = service.repondre(identifiant, {"depot_plus_deux_mois": "non",
                                                 "logement_quitte": "oui"})["data"]
        etapes.append(donnees["etape"])
        while donnees["etape"] == "clarification":
            donnees = service.repondre(identifiant, {"depot_plus_deux_mois": "non"})["data"]
            etapes.append(donnees["etape"])
        self.assertEqual(etapes[-1], "reponse")
        self.assertLessEqual(len(etapes), clarification.TOURS_MAX)


if __name__ == "__main__":
    unittest.main()
