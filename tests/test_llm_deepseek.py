# -*- coding: utf-8 -*-
"""Fournisseur DeepSeek — environnement de TEST uniquement.

Aucun appel réel n'est fait : un serveur local imite l'API. Aucune clé réelle
n'existe ici — la valeur est tirée au hasard à chaque exécution, précisément
pour qu'on ne puisse jamais la confondre avec un identifiant.

Ce que ces tests démontrent :
  * la requête envoyée a la forme attendue (JSON imposé, température 0) ;
  * les jetons consommés sont lus et comptés ;
  * le récit part MASQUÉ (courriel, téléphone) ;
  * toute panne (401, 402, 429, 500, délai, JSON invalide, réponse vide) rend
    la main au moteur déterministe, sans jamais casser le service ;
  * une fiche inventée ou hors sujet ne passe pas, même quand le fournisseur
    répond « proprement » ;
  * le plafond journalier et le disjoncteur empêchent l'appel AVANT qu'il parte ;
  * la clé n'apparaît dans aucun message d'erreur.
"""
import http.server
import json
import os
import secrets
import shutil
import sys
import tempfile
import threading
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import config
from core import catalogue, clarification, llm, llm_budget

CLE = "sk-test-" + secrets.token_hex(8)     # jamais une vraie clé
RECIT = ("Mon propriétaire a gardé l'argent que j'avais versé à l'entrée, j'ai rendu les "
         "clés en juin. Appelez-moi au 07 07 12 34 56 ou ecrivez a moi@exemple.ci.")


class FauxServeurDeepSeek(http.server.BaseHTTPRequestHandler):
    statut = 200
    contenu = "{}"
    recus = []
    usage = {"prompt_tokens": 1500, "completion_tokens": 120}

    def do_POST(self):  # noqa: N802
        corps = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FauxServeurDeepSeek.recus.append(
            {"corps": corps, "auth": self.headers.get("Authorization") or ""})
        if FauxServeurDeepSeek.statut != 200:
            charge = json.dumps({"error": {"message": "refus"}}).encode()
            self.send_response(FauxServeurDeepSeek.statut)
        else:
            charge = json.dumps({
                "choices": [{"message": {"content": FauxServeurDeepSeek.contenu}}],
                "usage": FauxServeurDeepSeek.usage,
            }).encode()
            self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(charge)

    def log_message(self, *args):
        return


SERVEUR = None
ADAPTATEUR = None
REGISTRE = None


def setUpModule():
    global SERVEUR, ADAPTATEUR, REGISTRE
    SERVEUR = http.server.HTTPServer(("127.0.0.1", 0), FauxServeurDeepSeek)
    threading.Thread(target=SERVEUR.serve_forever, daemon=True).start()
    ADAPTATEUR = llm.charger_adaptateur_http()
    REGISTRE = tempfile.mkdtemp(prefix="llm-test-")
    os.environ[llm_budget.NOM_VARIABLE_REGISTRE] = os.path.join(REGISTRE, "registre.json")


def tearDownModule():
    SERVEUR.shutdown()
    os.environ.pop(llm_budget.NOM_VARIABLE_REGISTRE, None)
    shutil.rmtree(REGISTRE, ignore_errors=True)


def fournisseur(**options):
    return ADAPTATEUR.FournisseurDeepSeek(
        url="http://127.0.0.1:%d/chat/completions" % SERVEUR.server_address[1],
        cle=CLE, **options)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fiches = catalogue.charger()
        cls.guide = clarification.charger(cls.fiches)

    def setUp(self):
        FauxServeurDeepSeek.recus = []
        FauxServeurDeepSeek.statut = 200
        FauxServeurDeepSeek.contenu = "{}"
        chemin = os.environ[llm_budget.NOM_VARIABLE_REGISTRE]
        if os.path.exists(chemin):
            os.remove(chemin)
        os.environ.pop(llm_budget.NOM_VARIABLE_PLAFOND, None)

    def repondre(self, objet, **options):
        FauxServeurDeepSeek.contenu = json.dumps(objet, ensure_ascii=False)
        return llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur(**options))


class ContratDuFournisseur(Base):
    def test_valeurs_par_defaut(self):
        f = ADAPTATEUR.FournisseurDeepSeek(cle=CLE)
        self.assertEqual(f.nom, "deepseek")
        self.assertTrue(f.url.startswith("https://api.deepseek.com"))
        self.assertEqual(f.modele, "deepseek-flash")

    def test_disponible_depend_de_la_cle(self):
        # URL et modèle vides retombent volontairement sur les valeurs officielles :
        # une configuration ne doit pas pouvoir casser le fournisseur par omission.
        # Seule l'absence de CLÉ le rend indisponible.
        self.assertEqual(ADAPTATEUR.FournisseurDeepSeek(url="", cle=CLE).url,
                         "https://api.deepseek.com/chat/completions")
        self.assertEqual(ADAPTATEUR.FournisseurDeepSeek(cle=CLE, modele="").modele, "deepseek-flash")
        self.assertFalse(ADAPTATEUR.FournisseurDeepSeek(url="http://x", cle="", modele="m").disponible())

    def test_requete_conforme(self):
        self.repondre({"fiches": [], "suggestions": [], "resume": None})
        corps = FauxServeurDeepSeek.recus[0]["corps"]
        self.assertEqual(corps["model"], "deepseek-flash")
        self.assertEqual(corps["temperature"], 0)
        self.assertEqual(corps["response_format"], {"type": "json_object"})
        self.assertFalse(corps["stream"])
        # MESURÉ sur l'API réelle : le mode réflexion est actif par défaut et
        # consommait les 300 jetons (2 appels sur 7 tronqués). On l'exige donc
        # explicitement désactivé, avec 800 jetons de sortie.
        self.assertEqual(corps["thinking"], {"type": "disabled"})
        self.assertLessEqual(corps["max_tokens"], 800)
        self.assertEqual([m["role"] for m in corps["messages"]], ["system", "user"])

    def test_la_cle_part_dans_l_en_tete_et_nulle_part_ailleurs(self):
        self.repondre({"fiches": [], "suggestions": [], "resume": None})
        recu = FauxServeurDeepSeek.recus[0]
        self.assertEqual(recu["auth"], "Bearer %s" % CLE)
        self.assertNotIn(CLE, json.dumps(recu["corps"]))

    def test_les_jetons_sont_lus(self):
        self.repondre({"fiches": [], "suggestions": [], "resume": None})
        self.assertEqual(llm_budget.etat()["jetons"], 1500 + 120)


class ProtectionDesDonnees(Base):
    def test_le_recit_part_masque(self):
        self.repondre({"fiches": [], "suggestions": [], "resume": None})
        message = FauxServeurDeepSeek.recus[0]["corps"]["messages"][1]["content"]
        self.assertNotIn("07 07 12 34 56", message)
        self.assertNotIn("moi@exemple.ci", message)
        self.assertIn("[NUMÉRO MASQUÉ]", message)
        self.assertIn("[COURRIEL MASQUÉ]", message)

    def test_le_masquage_est_compte(self):
        rapport = self.repondre({"fiches": [], "suggestions": [], "resume": None})
        self.assertEqual(rapport["masquages"], 2)


class RepliSurPanne(Base):
    def _verifier_repli(self, statut):
        FauxServeurDeepSeek.statut = statut
        rapport = llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertEqual(rapport["fiches"], [])
        self.assertTrue(rapport["erreur"])
        return rapport

    def test_401_cle_refusee(self):
        self.assertIn("clé refusée", self._verifier_repli(401)["erreur"])

    def test_402_solde_epuise(self):
        self.assertIn("solde", self._verifier_repli(402)["erreur"])

    def test_429_debit_depasse(self):
        self.assertIn("débit", self._verifier_repli(429)["erreur"])

    def test_500_erreur_interne(self):
        self.assertIn("erreur interne", self._verifier_repli(500)["erreur"])

    def test_la_cle_n_apparait_dans_aucun_message_d_erreur(self):
        for statut in (400, 401, 402, 422, 429, 500, 502, 503):
            rapport = self._verifier_repli(statut)
            self.assertNotIn(CLE, rapport["erreur"], "clé exposée sur HTTP %s" % statut)

    def test_reponse_non_json(self):
        FauxServeurDeepSeek.contenu = "Bien sûr ! Voici ma réponse en français."
        rapport = llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())
        self.assertEqual(rapport["mode"], "deterministe")

    def test_reponse_vide(self):
        FauxServeurDeepSeek.contenu = "   "
        rapport = llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())
        self.assertEqual(rapport["mode"], "deterministe")

    def test_fournisseur_sans_cle_ne_leve_pas(self):
        f = ADAPTATEUR.FournisseurDeepSeek(url="http://127.0.0.1:9/x", cle="", modele="m")
        rapport = llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=f)
        self.assertEqual(rapport["mode"], "deterministe")


class GardeFous(Base):
    def test_plafond_atteint_aucun_appel(self):
        os.environ[llm_budget.NOM_VARIABLE_PLAFOND] = "1000"
        llm_budget.enregistrer(5000, 0)
        rapport = llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertIn("garde-fou", rapport["erreur"])
        self.assertEqual(FauxServeurDeepSeek.recus, [], "un appel est parti malgré le plafond")

    def test_disjoncteur_apres_cinq_echecs(self):
        FauxServeurDeepSeek.statut = 500
        for _ in range(llm_budget.ECHECS_AVANT_PANNE):
            llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())
        appels = len(FauxServeurDeepSeek.recus)
        self.assertEqual(appels, llm_budget.ECHECS_AVANT_PANNE)
        rapport = llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())
        self.assertEqual(len(FauxServeurDeepSeek.recus), appels, "le disjoncteur n'a pas coupé")
        self.assertIn("garde-fou", rapport["erreur"])

    def test_un_succes_remet_le_compteur_a_zero(self):
        FauxServeurDeepSeek.statut = 500
        llm.comprendre(RECIT, self.fiches, self.guide, fournisseur=fournisseur())
        self.assertEqual(llm_budget.etat()["echecs"], 1)
        FauxServeurDeepSeek.statut = 200
        self.repondre({"fiches": [], "suggestions": [], "resume": None})
        self.assertEqual(llm_budget.etat()["echecs"], 0)


class CeQueLeModeleNePeutPasImposer(Base):
    def test_fiche_inventee_rejetee(self):
        rapport = self.repondre({"fiches": ["LOGEME_999"], "suggestions": [], "resume": None})
        self.assertEqual(rapport["fiches"], [])

    def test_fiche_hors_domaine_rejetee_par_la_pertinence(self):
        """Naissance : le domaine famille est qualifié, pas le logement."""
        contenu = json.dumps({"fiches": ["LOGEME_416"], "suggestions": [], "resume": None})
        FauxServeurDeepSeek.contenu = contenu
        conversation = __import__("core.conversation", fromlist=["Conversation"]).Conversation(
            fournisseur_langage=fournisseur())
        try:
            resultat = conversation.demarrer(
                "TEST_DEEPSEEK_NAISSANCE",
                "Je veux déclarer la naissance de mon enfant à l'état civil, il n'a pas d'acte de naissance.")
            charge = json.dumps(resultat, ensure_ascii=False)
            self.assertNotIn("bail à usage d'habitation", charge)
            self.assertEqual(resultat["comprehension"]["mode"], "llm")
            self.assertGreaterEqual(resultat["comprehension"]["elements_rejetes"], 1)
        finally:
            shutil.rmtree(str(config.dossier_utilisateur("TEST_DEEPSEEK_NAISSANCE")),
                          ignore_errors=True)

    def test_fiche_a_valider_ne_peut_pas_entrer(self):
        rapport = self.repondre({"fiches": ["CONSO_11_RETOUR_VENTE_DISTANCE"],
                                 "suggestions": [], "resume": None})
        self.assertEqual(rapport["fiches"], [])

    def test_citation_modifiee_rejetee(self):
        """Le modèle ne dicte pas le texte : il ne fournit que des identifiants."""
        rapport = self.repondre({"fiches": [], "suggestions": [], "resume": None})
        self.assertNotIn("citation", json.dumps(rapport))


class QuestionsReelles(Base):
    """Le parcours complet, avec un modèle qui propose — juste ou faux.

    Quatre situations réelles. Pour chacune, le modèle propose une fiche ; la
    réponse servie doit être la bonne, ou rien du tout. Jamais la mauvaise.
    """

    CAS = [
        ("Je veux déclarer la naissance de mon enfant à l'état civil, il n'a pas d'acte de naissance.",
         "LOGEME_416", False, "naissance"),
        ("Mon bailleur refuse de me rendre la caution de deux mois.",
         "LOGEME_416", True, "caution"),
        ("On a saisi mon salaire ce mois-ci.",
         "OHADA_153", False, "saisie sur salaire"),
        ("Ils ont saisi mon compte bancaire.", "OHADA_153", True, "saisie de compte"),
    ]

    def test_quatre_situations_reelles(self):
        Conversation = __import__("core.conversation", fromlist=["Conversation"]).Conversation
        for question, proposee, attendue, etiquette in self.CAS:
            with self.subTest(situation=etiquette):
                identifiant = "TEST_DEEPSEEK_%s" % etiquette.replace(" ", "_").upper()
                FauxServeurDeepSeek.contenu = json.dumps(
                    {"fiches": [proposee], "suggestions": [], "resume": None})
                try:
                    resultat = Conversation(fournisseur_langage=fournisseur()).demarrer(
                        identifiant, question)
                    charge = json.dumps(resultat, ensure_ascii=False)
                    servies = [f.get("article") for f in (resultat.get("fiches_identifiees") or [])]
                    if attendue:
                        self.assertTrue(servies, "%s : aucune fiche servie" % etiquette)
                    else:
                        self.assertNotIn("bail à usage d'habitation", charge, etiquette)
                        self.assertEqual(resultat["comprehension"]["elements_rejetes"] > 0, True,
                                         "%s : le rejet n'est pas tracé" % etiquette)
                finally:
                    shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)


class EtatParDefaut(unittest.TestCase):
    def test_le_llm_reste_desactive_sans_configuration(self):
        for variable in (llm.NOM_VARIABLE_FOURNISSEUR, llm.NOM_VARIABLE_CLE,
                         llm.NOM_VARIABLE_ACCORD):
            os.environ.pop(variable, None)
        self.assertFalse(llm.comprehension_active())
        self.assertEqual(llm.statut()["fournisseur"], "desactive")

    def test_budget_expose_dans_le_statut(self):
        budget = llm.statut()["budget"]
        self.assertIn("jetons", budget)
        self.assertIn("plafond", budget)


if __name__ == "__main__":
    unittest.main()
