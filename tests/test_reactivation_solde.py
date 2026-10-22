# -*- coding: utf-8 -*-
"""Réactivation contrôlée : on ne rétablit que sur preuve de solde.

Aucun appel réseau : la réponse du fournisseur est simulée. La règle testée est
celle du service — un solde illisible, une panne ou une configuration
incomplète laissent l'incident ouvert et le secours déterministe en place.
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

CLE = "sk-test-0123456789abcdef-ne-doit-jamais-sortir"


class Base(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="reactivation-")
        os.environ[incident_llm.NOM_VARIABLE_FICHIER] = os.path.join(self.dossier, "incident.json")
        os.environ[llm_budget.NOM_VARIABLE_REGISTRE] = os.path.join(self.dossier, "registre.json")
        os.environ[llm.NOM_VARIABLE_VERROU] = os.path.join(self.dossier, "verrou.lock")
        os.environ[llm.NOM_VARIABLE_FOURNISSEUR] = "deepseek"
        os.environ[llm.NOM_VARIABLE_CLE] = CLE
        os.environ[llm.NOM_VARIABLE_ACCORD] = "oui"
        self.adaptateur = llm.charger_adaptateur_http()
        self.original = self.adaptateur.FournisseurDeepSeek.verifier_solde
        incident_llm.declarer("deepseek", "Insufficient Balance", 402)

    def tearDown(self):
        for nom in (incident_llm.NOM_VARIABLE_FICHIER, llm_budget.NOM_VARIABLE_REGISTRE,
                    llm.NOM_VARIABLE_VERROU, llm.NOM_VARIABLE_FOURNISSEUR,
                    llm.NOM_VARIABLE_CLE, llm.NOM_VARIABLE_ACCORD):
            os.environ.pop(nom, None)
        shutil.rmtree(self.dossier, ignore_errors=True)

    def solde(self, reponse, exceptions=None):
        """Injecte la réponse du fournisseur — aucun appel réseau n'est fait."""
        def faux(delai=10.0):
            if exceptions is not None:
                raise exceptions
            return reponse
        self.verificateur = faux


class Reactivation(Base):
    def test_solde_positif_et_configuration_complete_reactive(self):
        self.solde({"etat": "POSITIF", "devise": "USD", "total": "12.50"})
        resultat = llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        self.assertTrue(resultat["reactive"])
        self.assertEqual(resultat["mode"], "llm")
        self.assertFalse(incident_llm.ouvert())
        etat = incident_llm.etat()
        self.assertEqual(etat["statut"], "RESOLU")
        self.assertIn("12.50", etat["resolution"])

    def test_solde_epuise_conserve_l_incident(self):
        self.solde({"etat": "EPUISE", "devise": "USD", "total": "0"})
        resultat = llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        self.assertFalse(resultat["reactive"])
        self.assertEqual(resultat["mode"], "deterministe")
        self.assertTrue(incident_llm.ouvert())

    def test_reponse_ambigue_conserve_l_incident(self):
        self.solde({"etat": "AMBIGU", "detail": "aucun solde dans la réponse"})
        resultat = llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        self.assertFalse(resultat["reactive"])
        self.assertTrue(incident_llm.ouvert())

    def test_erreur_reseau_conserve_l_incident(self):
        self.solde(None, exceptions=OSError("Connection refused"))
        resultat = llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        self.assertEqual(resultat["etat"], "ERREUR")
        self.assertFalse(resultat["reactive"])
        self.assertTrue(incident_llm.ouvert(), "une panne a fermé l'incident")

    def test_erreur_qualifiee_conserve_l_incident(self):
        self.solde({"etat": "ERREUR", "detail": "HTTP 503"})
        resultat = llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        self.assertFalse(resultat["reactive"])
        self.assertTrue(incident_llm.ouvert())


class Configuration(Base):
    def test_cle_absente_ne_verifie_rien(self):
        os.environ.pop(llm.NOM_VARIABLE_CLE, None)
        self.solde({"etat": "POSITIF", "devise": "USD", "total": "99"})
        resultat = llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        self.assertFalse(resultat["reactive"])
        self.assertEqual(resultat["etat"], "SANS_CLE")
        self.assertTrue(incident_llm.ouvert())

    def test_consentement_absent_bloque_la_reactivation(self):
        os.environ.pop(llm.NOM_VARIABLE_ACCORD, None)
        self.solde({"etat": "POSITIF", "devise": "USD", "total": "99"})
        resultat = llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        self.assertFalse(resultat["reactive"])
        self.assertEqual(resultat["mode"], "deterministe")
        self.assertTrue(incident_llm.ouvert(), "réactivé sans consentement")
        self.assertIn("accord de traitement des données non donné", resultat["manques"])

    def test_fournisseur_non_configure_bloque_la_reactivation(self):
        os.environ[llm.NOM_VARIABLE_FOURNISSEUR] = "desactive"
        self.solde({"etat": "POSITIF", "devise": "USD", "total": "99"})
        resultat = llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        self.assertFalse(resultat["reactive"])
        self.assertTrue(incident_llm.ouvert())


class Concurrence(Base):
    def test_deux_verifications_simultanees_une_seule_passe(self):
        self.solde({"etat": "POSITIF", "devise": "USD", "total": "99"})
        verrou = llm._verrouiller()
        self.assertIsNotNone(verrou)
        try:
            resultat = llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
            self.assertEqual(resultat["etat"], "EN_COURS")
            self.assertFalse(resultat["reactive"])
            self.assertTrue(incident_llm.ouvert())
        finally:
            llm._deverrouiller(verrou)

    def test_apres_la_verification_le_verrou_est_libere(self):
        self.solde({"etat": "EPUISE", "devise": "USD", "total": "0"})
        llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        verrou = llm._verrouiller()
        self.assertIsNotNone(verrou, "le verrou n'a pas été libéré")
        llm._deverrouiller(verrou)


class Confidentialite(Base):
    def test_la_cle_n_apparait_dans_aucun_resultat(self):
        self.solde({"etat": "POSITIF", "devise": "USD", "total": "12.50"})
        contenu = json.dumps(llm.verifier_solde_et_reactiver(verificateur=self.verificateur), ensure_ascii=False)
        self.assertNotIn(CLE, contenu)
        self.assertNotIn("sk-", contenu)
        with open(os.environ[incident_llm.NOM_VARIABLE_FICHIER], encoding="utf-8") as flux:
            self.assertNotIn(CLE, flux.read())

    def test_aucune_nouvelle_alerte_pendant_les_tentatives(self):
        self.solde({"etat": "ERREUR", "detail": "HTTP 500"})
        detecte = incident_llm.etat()["detecte_le"]
        for _ in range(4):
            llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        self.assertEqual(incident_llm.etat()["detecte_le"], detecte)


class Secours(Base):
    def test_le_moteur_deterministe_repond_malgre_l_incident(self):
        from core.conversation import Conversation
        import config
        self.solde({"etat": "EPUISE", "devise": "USD", "total": "0"})
        llm.verifier_solde_et_reactiver(verificateur=self.verificateur)
        identifiant = "secours_reactivation"
        try:
            vue = Conversation().demarrer(identifiant, "Mon bailleur garde ma caution.")
            self.assertIn("etape", vue)
        finally:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
