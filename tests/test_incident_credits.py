# -*- coding: utf-8 -*-
"""Crédits épuisés : un incident, pas une erreur de plus.

Ce qui est verrouillé ici :
  * distinguer un vrai épuisement (402 + message explicite) d'un simple 402,
    d'un 429 ou d'une panne réseau ;
  * n'alerter qu'UNE fois, pas à chaque consultation ;
  * continuer à servir en déterministe ;
  * clôturer l'incident après vérification, sans faux bouton ;
  * ne jamais écrire de clé ni de donnée personnelle dans l'incident.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

from core import incident_llm, llm, llm_budget  # noqa: E402

RECIT = ("Mon propriétaire a gardé l'argent versé à l'entrée. Appelez-moi au 07 07 12 34 56 "
         "ou ecrivez a moi@exemple.ci.")


def erreur(statut=None, message="", texte="fournisseur : erreur"):
    adaptateur = llm.charger_adaptateur_http()
    levee = adaptateur.ErreurTransport(texte)
    levee.statut_http = statut
    levee.message_fournisseur = message
    return levee


class FauxFournisseur(object):
    nom = "deepseek"

    def __init__(self, levee=None, contenu=None):
        self.levee = levee
        self.contenu = contenu or json.dumps({"fiches": [], "suggestions": [], "resume": None})
        self.appels = 0
        self.derniere_consommation = {"entree": 10, "sortie": 5}

    def disponible(self):
        return True

    def completer(self, systeme, message, delai=None, max_tokens=800):
        self.appels += 1
        if self.levee is not None:
            raise self.levee
        return self.contenu


class Base(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="incident-test-")
        os.environ[incident_llm.NOM_VARIABLE_FICHIER] = os.path.join(self.dossier, "incident.json")
        os.environ[llm_budget.NOM_VARIABLE_REGISTRE] = os.path.join(self.dossier, "registre.json")
        self.fiches = []

    def tearDown(self):
        os.environ.pop(incident_llm.NOM_VARIABLE_FICHIER, None)
        os.environ.pop(llm_budget.NOM_VARIABLE_REGISTRE, None)
        shutil.rmtree(self.dossier, ignore_errors=True)

    def appeler(self, fournisseur):
        return llm.comprendre(RECIT, [], {"questions": []}, fournisseur=fournisseur)


class Detection(Base):
    def test_un_vrai_epuisement_ouvre_un_incident(self):
        fournisseur = FauxFournisseur(
            erreur(402, '{"error":{"message":"Insufficient Balance","type":"insufficient_balance"}}'))
        rapport = self.appeler(fournisseur)
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertIn("crédits", rapport["erreur"])
        self.assertTrue(incident_llm.ouvert())
        etat = incident_llm.etat()
        self.assertEqual(etat["statut"], "CREDITS_EPUISES")
        self.assertEqual(etat["fournisseur"], "deepseek")
        self.assertIn("Crédits deepseek épuisés — Mon Recours CI", etat["objet"])

    def test_un_402_sans_mention_de_solde_n_est_pas_un_epuisement(self):
        fournisseur = FauxFournisseur(erreur(402, '{"error":{"message":"Payment required"}}'))
        rapport = self.appeler(fournisseur)
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertFalse(incident_llm.ouvert(), "un 402 générique a déclenché l'alerte")
        self.assertNotIn("crédits", rapport["erreur"])

    def test_un_429_n_est_pas_un_epuisement(self):
        fournisseur = FauxFournisseur(erreur(429, '{"error":{"message":"Rate limit reached"}}'))
        rapport = self.appeler(fournisseur)
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertFalse(incident_llm.ouvert())

    def test_un_delai_depasse_n_est_pas_un_epuisement(self):
        fournisseur = FauxFournisseur(erreur(None, "", "délai dépassé"))
        self.appeler(fournisseur)
        self.assertFalse(incident_llm.ouvert())

    def test_une_panne_reseau_n_est_pas_un_epuisement(self):
        fournisseur = FauxFournisseur(erreur(None, "", "transport : Connection refused"))
        self.appeler(fournisseur)
        self.assertFalse(incident_llm.ouvert())


class AlerteUnique(Base):
    def test_plusieurs_consultations_ne_produisent_qu_une_alerte(self):
        fournisseur = FauxFournisseur(erreur(402, '{"error":{"message":"Insufficient Balance"}}'))
        self.appeler(fournisseur)
        detecte = incident_llm.etat()["detecte_le"]
        for _ in range(5):
            self.appeler(fournisseur)
        etat = incident_llm.etat()
        self.assertEqual(etat["detecte_le"], detecte, "l'incident a été réécrit")
        self.assertEqual(etat["statut"], "CREDITS_EPUISES")

    def test_aucun_appel_au_fournisseur_pendant_l_incident(self):
        fournisseur = FauxFournisseur(erreur(402, '{"error":{"message":"Insufficient Balance"}}'))
        self.appeler(fournisseur)
        appels = fournisseur.appels
        for _ in range(3):
            rapport = self.appeler(fournisseur)
            self.assertEqual(rapport["mode"], "deterministe")
        self.assertEqual(fournisseur.appels, appels, "le fournisseur a été rappelé pendant l'incident")

    def test_le_service_repond_quand_meme(self):
        from core.conversation import Conversation
        import config
        fournisseur = FauxFournisseur(erreur(402, '{"error":{"message":"Insufficient Balance"}}'))
        identifiant = "incident_service"
        try:
            vue = Conversation(fournisseur_langage=fournisseur).demarrer(
                identifiant, "Mon bailleur garde ma caution de deux mois.")
            self.assertIn(vue["etape"], ("clarification", "hors_catalogue", "aiguillage"))
            self.assertEqual(vue.get("comprehension", {}).get("mode", "deterministe"), "deterministe")
        finally:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)


class Resolution(Base):
    def test_resolution_cloture_l_incident(self):
        incident_llm.declarer("deepseek", "Insufficient Balance", 402)
        self.assertTrue(incident_llm.ouvert())
        self.assertTrue(incident_llm.resoudre("solde vérifié"))
        etat = incident_llm.etat()
        self.assertEqual(etat["statut"], "RESOLU")
        self.assertIsNotNone(etat["resolu_le"])
        self.assertFalse(incident_llm.ouvert())

    def test_apres_resolution_le_fournisseur_est_reappele(self):
        incident_llm.declarer("deepseek", "Insufficient Balance", 402)
        incident_llm.resoudre("solde vérifié")
        fournisseur = FauxFournisseur()
        fournisseur.contenu = json.dumps({"fiches": [], "suggestions": [],
                                          "resume": "Situation reformulée."})
        rapport = self.appeler(fournisseur)
        self.assertEqual(fournisseur.appels, 1)
        self.assertEqual(rapport["mode"], "llm")

    def test_resoudre_sans_incident_ne_fait_rien(self):
        self.assertFalse(incident_llm.resoudre("rien à clore"))


class Confidentialite(Base):
    def test_l_incident_ne_contient_ni_cle_ni_donnee_personnelle(self):
        cle = "sk-secret-de-test-0123456789abcdef"
        incident_llm.declarer("deepseek",
                              "Insufficient Balance for key %s — contact moi@exemple.ci" % cle, 402)
        with open(os.environ[incident_llm.NOM_VARIABLE_FICHIER], encoding="utf-8") as flux:
            contenu = flux.read()
        self.assertNotIn(cle, contenu)
        self.assertNotIn("moi@exemple.ci", contenu)
        self.assertNotIn("07 07 12 34 56", contenu)

    def test_le_fichier_est_prive(self):
        incident_llm.declarer("deepseek", "Insufficient Balance", 402)
        mode = oct(os.stat(os.environ[incident_llm.NOM_VARIABLE_FICHIER]).st_mode)[-3:]
        self.assertEqual(mode, "600")


class Exposition(Base):
    def test_sante_expose_l_incident_sans_secret(self):
        from core import service
        incident_llm.declarer("deepseek", "Insufficient Balance", 402)
        langage = service.sante()["data"]["langage"]
        self.assertTrue(langage["incident"]["ouvert"])
        self.assertEqual(langage["incident"]["statut"], "CREDITS_EPUISES")
        self.assertNotIn("Insufficient", json.dumps(langage))


if __name__ == "__main__":
    unittest.main()
