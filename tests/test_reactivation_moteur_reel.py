# -*- coding: utf-8 -*-
"""Réactivation DeepSeek contre le MOTEUR RÉEL (bin/serveur_api.py).

Pourquoi ce fichier : les tests précédents simulaient le moteur côté web et
appelaient `verifier_solde_et_reactiver` directement côté Python. Aucun ne
passait par le serveur HTTP du moteur — or celui-ci aiguillait
`POST /llm/verifier-solde` vers `repondre` (ENTREE_INVALIDE) : la réactivation
n'avait jamais fonctionné de bout en bout. Ici, tout est réel sauf DeepSeek,
remplacé par un faux fournisseur LOCAL (127.0.0.1) : aucun crédit, aucun
réseau extérieur.

On vérifie aussi le cas de production où `RUNTIME/` n'est pas inscriptible
(systemd `ProtectSystem=strict`) : l'incident ne doit ni produire une alerte
par consultation, ni rappeler le fournisseur, ni bloquer la réactivation.
"""
import http.server
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import uuid
import urllib.error
import urllib.request

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

from core import incident_llm, llm, llm_budget  # noqa: E402

CLE_LLM = "sk-faux-deepseek-0123456789abcdef-NE-DOIT-PAS-SORTIR"
CLE_MOTEUR = "cle-moteur-de-test-0123456789abcdef"


def port_libre():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class FauxDeepSeek(object):
    """Faux fournisseur local : solde configurable, compte les appels."""

    def __init__(self):
        self.reponse_solde = (200, {"is_available": True, "balance_infos": [
            {"currency": "USD", "total_balance": "5.00", "granted_balance": "0.00",
             "topped_up_balance": "5.00"}]})
        self.attente = 0.0
        self.appels_solde = []
        self.appels_chat = 0
        self.couper = False
        parent = self

        class Gestion(http.server.BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_GET(self):
                parent.appels_solde.append(self.headers.get("Authorization"))
                if parent.attente:
                    time.sleep(parent.attente)
                if parent.couper:
                    self.connection.close()
                    return
                statut, corps = parent.reponse_solde
                donnees = corps if isinstance(corps, bytes) else json.dumps(corps).encode()
                self.send_response(statut)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(donnees)))
                self.end_headers()
                self.wfile.write(donnees)

            def do_POST(self):
                parent.appels_chat += 1
                self.send_response(500)
                self.end_headers()

        self.port = port_libre()
        self.serveur = http.server.ThreadingHTTPServer(("127.0.0.1", self.port), Gestion)
        self.fil = threading.Thread(target=self.serveur.serve_forever, daemon=True)
        self.fil.start()

    def arreter(self):
        self.serveur.shutdown()
        self.serveur.server_close()


class MoteurReel(unittest.TestCase):
    """Démarre le vrai serveur du moteur une fois par test."""

    runtime_inscriptible = True

    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="moteur-reel-")
        self.faux = FauxDeepSeek()
        if self.runtime_inscriptible:
            runtime = os.path.join(self.dossier, "RUNTIME")
        else:
            # Un FICHIER à la place du dossier : aucune écriture possible, même
            # en root (os.makedirs lève NotADirectoryError).
            bloqueur = os.path.join(self.dossier, "bloqueur")
            open(bloqueur, "w").close()
            runtime = os.path.join(bloqueur, "RUNTIME")
        self.fichier_incident = os.path.join(runtime, "incident.json")
        env = dict(os.environ)
        env.update({
            "MONRECOURS_API_KEY": CLE_MOTEUR,
            "MONRECOURS_PDF_NON_DISTRIBUES": "1",
            incident_llm.NOM_VARIABLE_FICHIER: self.fichier_incident,
            llm_budget.NOM_VARIABLE_REGISTRE: os.path.join(runtime, "registre.json"),
            llm.NOM_VARIABLE_VERROU: os.path.join(runtime, "verrou.lock"),
            "MONRECOURS_LLM_FOURNISSEUR": "deepseek",
            "MONRECOURS_LLM_API_KEY": CLE_LLM,
            "MONRECOURS_LLM_ACCORD_DONNEES": "oui",
            "MONRECOURS_LLM_URL": "http://127.0.0.1:%d/chat/completions" % self.faux.port,
            "MONRECOURS_LLM_URL_SOLDE": "http://127.0.0.1:%d/user/balance" % self.faux.port,
            "PYTHONUNBUFFERED": "1",
        })
        if self.runtime_inscriptible:
            os.makedirs(runtime, mode=0o700)
            # Incident ouvert AVANT le démarrage, comme après un épuisement réel.
            with open(self.fichier_incident, "w", encoding="utf-8") as flux:
                json.dump({"statut": incident_llm.OUVERT, "fournisseur": "deepseek",
                           "detecte_le": "2026-10-22T20:00:00", "resolu_le": None}, flux)
        self.port = port_libre()
        self.journal = open(os.path.join(self.dossier, "moteur.log"), "w+")
        self.processus = subprocess.Popen(
            [sys.executable, os.path.join(RACINE, "bin", "serveur_api.py"),
             "--port", str(self.port), "--debit", "1000"],
            cwd=RACINE, env=env, stdout=self.journal, stderr=subprocess.STDOUT)
        limite = time.time() + 30
        while time.time() < limite:
            try:
                self.get("/sante")
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.2)
        else:
            self.fail("le moteur n'a pas démarré")
        # Nettoyages en pile (dernier inscrit, premier exécuté) : les dossiers
        # ouverts par un test sont supprimés AVANT l'arrêt du moteur.
        self.addCleanup(self._arreter)

    def _arreter(self):
        self.processus.terminate()
        try:
            self.processus.wait(timeout=10)
        except subprocess.TimeoutExpired:
            self.processus.kill()
        self.journal.close()
        self.faux.arreter()
        shutil.rmtree(self.dossier, ignore_errors=True)

    # -- transport -----------------------------------------------------------
    def _requete(self, methode, route, corps=None):
        donnees = json.dumps(corps).encode() if corps is not None else None
        requete = urllib.request.Request(
            "http://127.0.0.1:%d%s" % (self.port, route), data=donnees, method=methode,
            headers={"X-API-Key": CLE_MOTEUR, "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(requete, timeout=40) as reponse:
                return reponse.status, reponse.read().decode()
        except urllib.error.HTTPError as erreur:
            return erreur.code, erreur.read().decode()

    def get(self, route):
        statut, texte = self._requete("GET", route)
        return statut, json.loads(texte)

    def verifier(self):
        statut, texte = self._requete("POST", "/llm/verifier-solde", {"verification": True})
        self.assertNotIn(CLE_LLM, texte, "la clé du fournisseur ne doit jamais sortir")
        return statut, json.loads(texte)

    def incident_sante(self):
        statut, corps = self.get("/sante")
        self.assertEqual(statut, 200)
        return corps["data"]["langage"]["incident"]


class ReactivationDeBoutEnBout(MoteurReel):
    def test_route_aiguillee_vers_la_verification_et_non_vers_repondre(self):
        statut, corps = self.verifier()
        self.assertEqual(statut, 200, corps)
        self.assertTrue(corps["ok"], corps)
        self.assertIn("reactive", corps["data"])

    def test_solde_positif_ferme_l_incident_dans_le_moteur(self):
        self.assertTrue(self.incident_sante()["ouvert"])
        statut, corps = self.verifier()
        self.assertEqual(statut, 200, corps)
        self.assertTrue(corps["data"]["reactive"], corps)
        self.assertEqual(corps["data"]["etat"], "POSITIF")
        # L'état utilisé par le moteur a réellement changé : /sante et le fichier.
        self.assertFalse(self.incident_sante()["ouvert"])
        with open(self.fichier_incident, encoding="utf-8") as flux:
            self.assertEqual(json.load(flux)["statut"], incident_llm.RESOLU)
        # La clé est partie vers le faux fournisseur, en en-tête, et nulle part ailleurs.
        self.assertEqual(self.faux.appels_solde, ["Bearer %s" % CLE_LLM])

    def test_solde_epuise_laisse_l_incident_ouvert(self):
        self.faux.reponse_solde = (200, {"is_available": False, "balance_infos": [
            {"currency": "USD", "total_balance": "0.00"}]})
        statut, corps = self.verifier()
        self.assertEqual(statut, 200)
        self.assertFalse(corps["data"]["reactive"])
        self.assertEqual(corps["data"]["etat"], "EPUISE")
        self.assertTrue(self.incident_sante()["ouvert"])

    def test_reponse_mal_formee_laisse_l_incident_ouvert(self):
        self.faux.reponse_solde = (200, b"<html>pas du json</html>")
        _, corps = self.verifier()
        self.assertFalse(corps["data"]["reactive"])
        self.assertEqual(corps["data"]["etat"], "AMBIGU")
        self.assertTrue(self.incident_sante()["ouvert"])

    def test_indicateur_de_disponibilite_absent_est_ambigu(self):
        self.faux.reponse_solde = (200, {"balance_infos": [{"currency": "USD", "total_balance": "9"}]})
        _, corps = self.verifier()
        self.assertFalse(corps["data"]["reactive"])
        self.assertEqual(corps["data"]["etat"], "AMBIGU")

    def test_erreur_http_laisse_l_incident_ouvert(self):
        self.faux.reponse_solde = (500, {"error": "boom"})
        _, corps = self.verifier()
        self.assertFalse(corps["data"]["reactive"])
        self.assertEqual(corps["data"]["etat"], "ERREUR")
        self.assertTrue(self.incident_sante()["ouvert"])

    def test_coupure_reseau_laisse_l_incident_ouvert(self):
        self.faux.couper = True
        _, corps = self.verifier()
        self.assertFalse(corps["data"]["reactive"])
        self.assertEqual(corps["data"]["etat"], "ERREUR")
        self.assertTrue(self.incident_sante()["ouvert"])

    def test_verifications_simultanees_une_seule_interrogation(self):
        self.faux.attente = 1.5
        resultats = []

        def lancer():
            resultats.append(self.verifier()[1])

        fils = [threading.Thread(target=lancer) for _ in range(2)]
        for fil in fils:
            fil.start()
        for fil in fils:
            fil.join(30)
        etats = sorted(r["data"]["etat"] for r in resultats)
        self.assertEqual(etats, ["EN_COURS", "POSITIF"], resultats)
        self.assertEqual(len(self.faux.appels_solde), 1)
        self.assertFalse(self.incident_sante()["ouvert"])

    def ouvrir_puis_supprimer(self, demande):
        """Ouvre une consultation sous un identifiant unique, et la supprime ensuite
        (le moteur écrit dans DOSSIERS/ du dépôt : rien ne doit y rester)."""
        dossier_id = "test-reactivation-%s" % uuid.uuid4().hex[:12]
        self.addCleanup(self._requete, "POST", "/supprimer", {"dossier_id": dossier_id})
        return self._requete("POST", "/ouvrir", {"dossier_id": dossier_id, "demande": demande})

    def test_pendant_l_incident_la_consultation_reste_deterministe(self):
        statut, texte = self.ouvrir_puis_supprimer(
            "Mon bailleur veut m'expulser sans préavis de mon logement à Abidjan.")
        self.assertEqual(statut, 200, texte)
        self.assertTrue(json.loads(texte)["ok"])
        self.assertEqual(self.faux.appels_chat, 0,
                         "aucun appel au fournisseur tant que l'incident est ouvert")
        self.assertTrue(self.incident_sante()["ouvert"])

    def test_temoin_sans_incident_le_fournisseur_est_bien_appele(self):
        """Témoin : prouve que le « zéro appel » ci-dessus n'est pas vide de sens."""
        self.verifier()  # solde positif : incident clos
        self.assertFalse(self.incident_sante()["ouvert"])
        statut, texte = self.ouvrir_puis_supprimer(
            "Mon bailleur veut m'expulser sans préavis de mon logement à Abidjan.")
        self.assertEqual(statut, 200, texte)
        self.assertGreaterEqual(self.faux.appels_chat, 1)
        # Le faux fournisseur répond 500 : la consultation aboutit quand même.
        self.assertTrue(json.loads(texte)["ok"])

    def test_le_journal_du_moteur_ne_contient_pas_la_cle(self):
        self.verifier()
        self.journal.flush()
        self.journal.seek(0)
        self.assertNotIn(CLE_LLM, self.journal.read())


class RuntimeNonInscriptible(MoteurReel):
    """Cas de l'unité systemd d'origine : RUNTIME en lecture seule."""

    runtime_inscriptible = False

    def test_la_reactivation_n_est_pas_bloquee_en_cours(self):
        statut, corps = self.verifier()
        self.assertEqual(statut, 200, corps)
        self.assertNotEqual(corps["data"]["etat"], "EN_COURS",
                            "un verrou impossible à créer ne doit pas bloquer la vérification")
        self.assertEqual(corps["data"]["etat"], "POSITIF")

    def test_l_etat_signale_qu_il_n_est_pas_persistant(self):
        incident = self.incident_sante()
        self.assertFalse(incident["ouvert"])
        # Après une tentative d'écriture, le moteur sait que le disque refuse.
        self.verifier()
        self.assertIn("persistant", self.incident_sante())


class RepliMemoire(unittest.TestCase):
    """Fonctions du cœur, sans serveur, avec un RUNTIME impossible à écrire."""

    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="repli-")
        bloqueur = os.path.join(self.dossier, "bloqueur")
        open(bloqueur, "w").close()
        runtime = os.path.join(bloqueur, "RUNTIME")
        self.variables = {
            incident_llm.NOM_VARIABLE_FICHIER: os.path.join(runtime, "incident.json"),
            llm_budget.NOM_VARIABLE_REGISTRE: os.path.join(runtime, "registre.json"),
            llm.NOM_VARIABLE_VERROU: os.path.join(runtime, "verrou.lock"),
            llm.NOM_VARIABLE_FOURNISSEUR: "deepseek",
            llm.NOM_VARIABLE_CLE: CLE_LLM,
            llm.NOM_VARIABLE_ACCORD: "oui",
        }
        os.environ.update(self.variables)

    def tearDown(self):
        for nom in self.variables:
            os.environ.pop(nom, None)
        os.environ.pop(llm_budget.NOM_VARIABLE_PLAFOND, None)
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_une_seule_alerte_meme_sans_disque(self):
        self.assertTrue(incident_llm.declarer("deepseek", "Insufficient Balance", 402))
        self.assertFalse(incident_llm.declarer("deepseek", "Insufficient Balance", 402))
        self.assertTrue(incident_llm.ouvert())
        self.assertFalse(incident_llm.etat()["persistant"])

    def test_declarations_concurrentes_une_seule_nouvelle(self):
        resultats = []
        fils = [threading.Thread(target=lambda: resultats.append(
            incident_llm.declarer("deepseek", "Insufficient Balance", 402))) for _ in range(8)]
        for fil in fils:
            fil.start()
        for fil in fils:
            fil.join()
        self.assertEqual(resultats.count(True), 1, resultats)

    def test_aucun_appel_au_fournisseur_pendant_l_incident(self):
        incident_llm.declarer("deepseek", "Insufficient Balance", 402)

        class Espion(object):
            nom = "deepseek"
            appels = 0

            def completer(self, *args, **kwargs):
                Espion.appels += 1
                return "{}"

        rapport = llm.comprendre("récit", [], {}, fournisseur=Espion())
        self.assertEqual(Espion.appels, 0)
        self.assertEqual(rapport["mode"], "deterministe")

    def test_le_plafond_reste_applique_en_memoire(self):
        os.environ[llm_budget.NOM_VARIABLE_PLAFOND] = "1000"
        llm_budget.enregistrer(600, 300)
        self.assertFalse(llm_budget.peut_appeler(200))
        self.assertFalse(llm_budget.etat()["persistant"])

    def test_verification_possible_et_signalee_non_persistante(self):
        incident_llm.declarer("deepseek", "Insufficient Balance", 402)
        resultat = llm.verifier_solde_et_reactiver(
            verificateur=lambda delai=10.0: {"etat": "POSITIF", "devise": "USD", "total": "3"})
        self.assertTrue(resultat["reactive"], resultat)
        self.assertIn("RUNTIME", resultat["message"])
        self.assertFalse(incident_llm.ouvert())

    def test_delai_depasse_ne_ferme_pas_l_incident(self):
        incident_llm.declarer("deepseek", "Insufficient Balance", 402)

        def lent(delai=10.0):
            raise socket.timeout("délai dépassé")

        resultat = llm.verifier_solde_et_reactiver(verificateur=lent)
        self.assertFalse(resultat["reactive"])
        self.assertEqual(resultat["etat"], "ERREUR")
        self.assertTrue(incident_llm.ouvert())


class FournisseurNonDeepSeek(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="non-deepseek-")
        self.variables = {
            incident_llm.NOM_VARIABLE_FICHIER: os.path.join(self.dossier, "incident.json"),
            llm.NOM_VARIABLE_VERROU: os.path.join(self.dossier, "verrou.lock"),
            llm.NOM_VARIABLE_FOURNISSEUR: "anthropic",
            llm.NOM_VARIABLE_CLE: "cle-anthropic-qui-ne-doit-pas-partir-chez-deepseek",
            llm.NOM_VARIABLE_ACCORD: "oui",
        }
        os.environ.update(self.variables)

    def tearDown(self):
        for nom in self.variables:
            os.environ.pop(nom, None)
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_la_cle_d_un_autre_fournisseur_n_est_jamais_envoyee_a_deepseek(self):
        appels = []
        resultat = llm.verifier_solde_et_reactiver(
            verificateur=lambda delai=10.0: appels.append(1) or {"etat": "POSITIF"})
        self.assertEqual(appels, [])
        self.assertEqual(resultat["etat"], "NON_APPLICABLE")
        self.assertFalse(resultat["reactive"])


class AdresseDeSolde(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("MONRECOURS_LLM_URL_SOLDE", None)

    def test_seules_l_adresse_officielle_et_la_boucle_locale_sont_acceptees(self):
        adaptateur = llm.charger_adaptateur_http()
        self.assertEqual(adaptateur.url_solde_autorisee(), "https://api.deepseek.com/user/balance")
        for refusee in ("https://evil.example/user/balance", "http://api.deepseek.com/user/balance",
                        "ftp://127.0.0.1/x", "https://api.deepseek.com.evil.example/x"):
            os.environ["MONRECOURS_LLM_URL_SOLDE"] = refusee
            self.assertIsNone(adaptateur.url_solde_autorisee(), refusee)
        os.environ["MONRECOURS_LLM_URL_SOLDE"] = "http://127.0.0.1:9999/user/balance"
        self.assertEqual(adaptateur.url_solde_autorisee(), "http://127.0.0.1:9999/user/balance")


if __name__ == "__main__":
    unittest.main()
