# -*- coding: utf-8 -*-
"""Tests du serveur HTTP local : authentification, débit, validation, isolation.

Aucun test ne touche Internet : le serveur écoute sur 127.0.0.1 avec un port
éphémère, et les dossiers créés sont supprimés à la fin.
"""

import json
import os
import shutil
import sys
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "serveur_api", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "bin", "serveur_api.py"))
serveur_api = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(serveur_api)

CLE = "cle-de-test-0123456789"
DOSSIERS = []


def dossier(prefixe):
    identifiant = "TEST_HTTP_%s" % prefixe
    DOSSIERS.append(identifiant)
    return identifiant


class BaseServeur(unittest.TestCase):
    journal = None
    limiteur = None

    @classmethod
    def setUpClass(cls):
        cls.journal = []
        cls.serveur = serveur_api.creer_serveur(
            port=0, cle_api=CLE, journal=cls.journal,
            limiteur=cls.limiteur or serveur_api.LimiteurDebit(maximum=50))
        cls.port = cls.serveur.server_address[1]
        cls.thread = threading.Thread(target=cls.serveur.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.serveur.shutdown()
        cls.serveur.server_close()
        cls.thread.join(timeout=5)
        for identifiant in DOSSIERS:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)
        del DOSSIERS[:]

    def requete(self, methode, route, charge=None, cle=CLE, corps_brut=None, entetes=None):
        url = "http://127.0.0.1:%d%s" % (self.port, route)
        donnees = corps_brut
        if donnees is None and charge is not None:
            donnees = json.dumps(charge).encode("utf-8")
        requete = urllib.request.Request(url, data=donnees, method=methode)
        if cle is not None:
            requete.add_header("X-API-Key", cle)
        requete.add_header("Content-Type", "application/json")
        for nom, valeur in (entetes or {}).items():
            requete.add_header(nom, valeur)
        try:
            with urllib.request.urlopen(requete, timeout=15) as reponse:
                return reponse.status, json.loads(reponse.read().decode("utf-8")), dict(reponse.headers)
        except urllib.error.HTTPError as erreur:
            corps = erreur.read().decode("utf-8")
            try:
                charge_json = json.loads(corps)
            except ValueError:
                charge_json = {"brut": corps}
            return erreur.code, charge_json, dict(erreur.headers)


class TestAuthentification(BaseServeur):
    def test_sans_cle(self):
        statut, corps, _ = self.requete("GET", "/sante", cle=None)
        self.assertEqual(statut, 401)
        self.assertEqual(corps["erreur"]["code"], "NON_AUTHENTIFIE")

    def test_mauvaise_cle(self):
        statut, corps, _ = self.requete("GET", "/sante", cle="mauvaise-cle-012345")
        self.assertEqual(statut, 401)

    def test_bonne_cle(self):
        statut, corps, _ = self.requete("GET", "/sante")
        self.assertEqual(statut, 200)
        self.assertTrue(corps["ok"])
        self.assertIn("catalogue", corps["data"])

    def test_aucune_cle_par_defaut_dans_le_code(self):
        """Sans variable d'environnement, le serveur refuse de démarrer."""
        ancienne = os.environ.pop(serveur_api.NOM_VARIABLE_CLE, None)
        try:
            with self.assertRaises(RuntimeError) as contexte:
                serveur_api.creer_serveur(port=0)
            self.assertIn(serveur_api.NOM_VARIABLE_CLE, str(contexte.exception))
        finally:
            if ancienne is not None:
                os.environ[serveur_api.NOM_VARIABLE_CLE] = ancienne

    def test_cle_trop_courte_refusee(self):
        with self.assertRaises(RuntimeError):
            serveur_api.creer_serveur(port=0, cle_api="court")

    def test_ecoute_publique_refusee(self):
        with self.assertRaises(RuntimeError) as contexte:
            serveur_api.creer_serveur(port=0, cle_api=CLE, hote="0.0.0.0")
        self.assertIn("127.0.0.1", str(contexte.exception))


class TestRoutesEtValidation(BaseServeur):
    def test_route_inconnue(self):
        statut, corps, _ = self.requete("GET", "/inconnue")
        self.assertEqual(statut, 404)
        self.assertEqual(corps["erreur"]["code"], "ROUTE_INCONNUE")

    def test_methode_non_autorisee(self):
        statut, corps, _ = self.requete("DELETE", "/sante")
        self.assertEqual(statut, 405)

    def test_json_invalide(self):
        statut, corps, _ = self.requete("POST", "/ouvrir", corps_brut=b"{ceci n'est pas du json")
        self.assertEqual(statut, 400)
        self.assertEqual(corps["erreur"]["code"], "CORPS_INVALIDE")

    def test_corps_trop_volumineux(self):
        gros = b'{"dossier_id":"x","demande":"' + b"a" * (serveur_api.TAILLE_MAX_CORPS + 10) + b'"}'
        statut, corps, _ = self.requete("POST", "/ouvrir", corps_brut=gros)
        self.assertEqual(statut, 413)
        self.assertEqual(corps["erreur"]["code"], "CORPS_TROP_GRAND")

    def test_service_en_erreur_renvoie_422(self):
        statut, corps, _ = self.requete("POST", "/ouvrir",
                                        {"dossier_id": dossier("VIDE"), "demande": ""})
        self.assertEqual(statut, 422)
        self.assertFalse(corps["ok"])
        self.assertEqual(corps["erreur"]["code"], "ENTREE_INVALIDE")

    def test_parcours_complet(self):
        identifiant = dossier("COMPLET")
        statut, corps, _ = self.requete("POST", "/ouvrir",
                                        {"dossier_id": identifiant,
                                         "demande": "Mon bailleur garde ma caution de deux mois."})
        self.assertEqual(statut, 200)
        self.assertIn(corps["data"]["etape"], ("clarification", "hors_catalogue"))
        statut, corps, _ = self.requete("POST", "/repondre",
                                        {"dossier_id": identifiant,
                                         "reponses": {"logement": "oui"}})
        self.assertEqual(statut, 200)
        self.assertEqual(corps["data"]["reponse"]["statut_reponse"], "ANALYSE_CONFORME")
        for source in corps["data"]["reponse"]["sections"]["6_sources"]:
            self.assertTrue(source["sha256_article"].startswith("sha256:"))


class TestLimitationDebit(BaseServeur):
    limiteur = serveur_api.LimiteurDebit(maximum=3, fenetre=60.0)

    def test_depassement_puis_retry_after(self):
        # Les requêtes précédentes d'autres classes ont leur propre limiteur ; ici
        # on consomme volontairement le quota de cette classe.
        statuts = [self.requete("GET", "/sante")[0] for _ in range(4)]
        self.assertIn(429, statuts)
        statut, corps, entetes = self.requete("GET", "/sante")
        self.assertEqual(statut, 429)
        self.assertEqual(corps["erreur"]["code"], "DEBIT_DEPASSE")
        self.assertIn("Retry-After", entetes)


class TestJournalSansDonneesPersonnelles(BaseServeur):
    def test_le_journal_ne_contient_ni_identifiant_ni_demande(self):
        identifiant = dossier("JOURNAL")
        demande = "Mon bailleur garde ma caution et me menace."
        self.requete("POST", "/ouvrir", {"dossier_id": identifiant, "demande": demande})
        self.assertTrue(self.journal, "le journal doit contenir au moins une entrée")
        for entree in self.journal:
            self.assertEqual(set(entree),
                             {"horodatage", "methode", "route", "statut", "duree_ms", "dossier"})
            self.assertNotIn(identifiant, json.dumps(entree))
            self.assertNotIn("caution", json.dumps(entree))
        self.assertEqual(self.journal[-1]["dossier"], serveur_api.empreinte_dossier(identifiant))


class TestIsolationParHTTP(BaseServeur):
    def test_deux_dossiers_par_http(self):
        a, b = dossier("HTTP_A"), dossier("HTTP_B")
        self.requete("POST", "/ouvrir", {"dossier_id": a,
                                         "demande": "Ma caution n'a pas été rendue."})
        self.requete("POST", "/ouvrir", {"dossier_id": b,
                                         "demande": "Le loyer a été augmenté sans préavis."})
        chemin_a = os.path.join(str(config.dossier_utilisateur(a)), "CONVERSATION.json")
        chemin_b = os.path.join(str(config.dossier_utilisateur(b)), "CONVERSATION.json")
        self.assertTrue(os.path.isfile(chemin_a) and os.path.isfile(chemin_b))
        self.assertNotEqual(open(chemin_a, encoding="utf-8").read(),
                            open(chemin_b, encoding="utf-8").read())


if __name__ == "__main__":
    unittest.main(verbosity=2)
