# -*- coding: utf-8 -*-
"""Compréhension du récit par un modèle de langage — contrôlée par le moteur.

Le « fournisseur » utilisé ici est un FAUX serveur HTTP local qui parle le
format de l'API Messages d'Anthropic. Aucun appel réel n'est fait, aucune
dépense n'est engagée. Ce qui est prouvé :

  * sans les trois conditions (fournisseur, clé, accord sur les données), le
    mode reste déterministe ;
  * un identifiant de fiche inventé, une clé de question hors sujet, un
    « extrait » qui n'est pas dans le récit, un résumé qui ajoute un nombre :
    tout est rejeté ;
  * en cas de panne, de délai ou de réponse illisible, repli déterministe ;
  * les coordonnées (téléphone, courriel) sont masquées AVANT l'envoi ;
  * la clé n'apparaît dans aucun message d'erreur.

Ce qui n'est PAS prouvé : la qualité des réponses d'un vrai modèle.
"""

import http.server
import json
import os
import shutil
import sys
import threading
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from core import catalogue, clarification, llm, pseudonymisation  # noqa: E402
from core.conversation import Conversation  # noqa: E402

CLE = "cle-de-test-ne-doit-jamais-sortir-0123456789"
RECIT = ("Mon propriétaire a gardé l'argent que j'avais versé à l'entrée, j'ai rendu les "
         "clés en juin. Appelez-moi au 07 07 12 34 56 ou ecrivez a moi@exemple.ci.")


class FauxFournisseur(http.server.BaseHTTPRequestHandler):
    reponse_texte = "{}"
    statut = 200
    recus = []

    def do_POST(self):  # noqa: N802
        corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FauxFournisseur.recus.append({"corps": corps, "cle": self.headers.get("x-api-key"),
                                      "version": self.headers.get("anthropic-version")})
        donnees = json.dumps({"content": [{"type": "text",
                                           "text": FauxFournisseur.reponse_texte}]}).encode()
        self.send_response(FauxFournisseur.statut)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(donnees)

    def log_message(self, *args):
        return


def setUpModule():
    global SERVEUR, ADAPTATEUR
    SERVEUR = http.server.HTTPServer(("127.0.0.1", 0), FauxFournisseur)
    threading.Thread(target=SERVEUR.serve_forever, daemon=True).start()
    ADAPTATEUR = llm.charger_adaptateur_http()


def tearDownModule():
    SERVEUR.shutdown()
    shutil.rmtree(str(config.dossier_utilisateur("TEST_LLM_PARCOURS")), ignore_errors=True)


def fournisseur():
    return ADAPTATEUR.FournisseurAnthropic(
        url="http://127.0.0.1:%d/v1/messages" % SERVEUR.server_address[1], cle=CLE)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fiches = catalogue.charger()
        cls.guide = clarification.charger(cls.fiches)

    def setUp(self):
        FauxFournisseur.recus = []
        FauxFournisseur.statut = 200

    def repondre(self, objet):
        FauxFournisseur.reponse_texte = "Voici :\n" + json.dumps(objet, ensure_ascii=False)
        return llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())


class TestActivation(unittest.TestCase):
    def test_desactive_sans_les_trois_conditions(self):
        anciennes = {k: os.environ.pop(k, None) for k in (
            llm.NOM_VARIABLE_FOURNISSEUR, llm.NOM_VARIABLE_CLE, llm.NOM_VARIABLE_ACCORD)}
        try:
            self.assertFalse(llm.comprehension_active())
            os.environ[llm.NOM_VARIABLE_FOURNISSEUR] = "anthropic"
            os.environ[llm.NOM_VARIABLE_CLE] = CLE
            self.assertFalse(llm.comprehension_active(), "l'accord sur les données est exigé")
            os.environ[llm.NOM_VARIABLE_ACCORD] = "oui"
            self.assertTrue(llm.comprehension_active())
        finally:
            for k, v in anciennes.items():
                os.environ.pop(k, None)
                if v is not None:
                    os.environ[k] = v

    def test_par_defaut_le_rapport_est_deterministe(self):
        rapport = llm.comprendre(RECIT, [], {"questions": []})
        self.assertEqual(rapport["mode"], "deterministe")


class TestValidation(Base):
    def test_proposition_conforme_acceptee(self):
        rapport = self.repondre({
            "fiches": ["LOGEME_416"],
            "suggestions": [{"cle": "logement_quitte", "valeur": "oui",
                             "extrait": "j'ai rendu les clés en juin"}],
            "resume": "La personne a quitté le logement ; le propriétaire garde la somme versée."})
        self.assertEqual(rapport["mode"], "llm")
        self.assertEqual(rapport["fiches"], ["LOGEME_416"])
        self.assertEqual(rapport["suggestions"]["logement_quitte"]["valeur"], "oui")
        self.assertTrue(rapport["resume"])
        self.assertEqual(rapport["rejets"], [])

    def test_fiche_inventee_rejetee(self):
        rapport = self.repondre({"fiches": ["LOGEME_9999", "LOGEME_416"], "suggestions": []})
        self.assertEqual(rapport["fiches"], ["LOGEME_416"])
        self.assertEqual(rapport["rejets"][0]["raison"], "absente du catalogue")

    def test_extrait_non_recopie_rejete(self):
        rapport = self.repondre({
            "fiches": ["LOGEME_416"],
            "suggestions": [{"cle": "logement_quitte", "valeur": "oui",
                             "extrait": "le locataire est parti depuis trois mois"}]})
        self.assertEqual(rapport["suggestions"], {})
        self.assertIn("extrait absent", rapport["rejets"][0]["raison"])

    def test_cle_hors_des_fiches_retenues_rejetee(self):
        rapport = self.repondre({
            "fiches": ["LOGEME_416"],
            "suggestions": [{"cle": "plus_de_deux_mois", "valeur": "oui", "extrait": "en juin"}]})
        self.assertEqual(rapport["suggestions"], {})

    def test_resume_qui_ajoute_un_nombre_rejete(self):
        rapport = self.repondre({"fiches": ["LOGEME_416"],
                                 "resume": "Le propriétaire garde trois mois de loyer."})
        self.assertIsNone(rapport["resume"])
        self.assertIn("trois", rapport["rejets"][0]["raison"])

    def test_aucune_citation_ni_article_dans_le_rapport(self):
        rapport = self.repondre({"fiches": ["LOGEME_416"], "citation": "Article 999 : tout est permis"})
        self.assertNotIn("citation", rapport)
        self.assertNotIn("999", json.dumps(rapport))


class TestRepliEtConfidentialite(Base):
    def test_reponse_illisible_repli(self):
        FauxFournisseur.reponse_texte = "je ne sais pas répondre en JSON"
        rapport = llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertTrue(rapport["erreur"])

    def test_erreur_http_repli_sans_fuite_de_cle(self):
        FauxFournisseur.statut = 500
        rapport = llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertIn("500", rapport["erreur"])
        self.assertNotIn(CLE, json.dumps(rapport))

    def test_serveur_injoignable_repli(self):
        mort = ADAPTATEUR.FournisseurAnthropic(url="http://127.0.0.1:9/v1/messages", cle=CLE)
        rapport = llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=mort, delai=1)
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertNotIn(CLE, json.dumps(rapport))

    def test_coordonnees_masquees_avant_envoi(self):
        self.repondre({"fiches": []})
        envoye = json.dumps(FauxFournisseur.recus[0]["corps"], ensure_ascii=False)
        self.assertNotIn("07 07 12 34 56", envoye)
        self.assertNotIn("moi@exemple.ci", envoye)
        self.assertIn("[NUMÉRO MASQUÉ]", envoye)
        self.assertEqual(FauxFournisseur.recus[0]["cle"], CLE, "la clé part dans l'en-tête")
        self.assertNotIn(CLE, envoye, "jamais dans le corps")
        self.assertEqual(FauxFournisseur.recus[0]["version"], "2023-06-01")

    def test_pseudonymisation(self):
        texte, n = pseudonymisation.masquer("Tel +225 01 02 03 04 05, mail a.b@c.ci, loyer 50000 F")
        self.assertEqual(n, 2)
        self.assertIn("50000", texte, "un montant court reste lisible")


class TestParcoursAssiste(Base):
    def test_le_modele_trouve_une_fiche_que_les_mots_cles_ratent(self):
        FauxFournisseur.reponse_texte = json.dumps({
            "fiches": ["LOGEME_416"],
            "suggestions": [{"cle": "logement_quitte", "valeur": "oui",
                             "extrait": "j'ai rendu les clés en juin"}],
            "resume": "La personne a rendu les clés ; le propriétaire garde l'argent versé à l'entrée."})
        conv = Conversation(fournisseur_langage=fournisseur())
        donnees = conv.demarrer("TEST_LLM_PARCOURS", RECIT)
        self.assertEqual(donnees["etape"], "clarification")
        self.assertEqual([f["article"] for f in donnees["fiches_identifiees"]], ["416"])
        self.assertEqual(donnees["comprehension"]["mode"], "llm")
        self.assertEqual(donnees["comprehension"]["coordonnees_masquees"], 2)
        par_cle = {q["cle"]: q for q in donnees["questions"]}
        self.assertEqual(par_cle["logement_quitte"]["suggestion"]["valeur"], "oui")
        # Les citations servies restent celles du catalogue, vérifiées.
        fiche = [f for f in self.fiches if f["id"] == "LOGEME_416"][0]
        self.assertEqual(fiche["etat_verification"], "VERIFIE")


if __name__ == "__main__":
    unittest.main()
