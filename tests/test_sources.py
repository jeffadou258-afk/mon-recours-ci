# -*- coding: utf-8 -*-
"""Sources : table de classification, périmètre officiel, et échec réseau déclaré."""

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import SOURCES_OFFICIELLES  # noqa: E402
from core import sources  # noqa: E402


class TestClassification(unittest.TestCase):
    """Table pure : elle doit être vérifiable sans réseau."""

    def test_codes_http(self):
        attendus = {
            200: sources.STATUT_ACCESSIBLE, 204: sources.STATUT_ACCESSIBLE, 206: sources.STATUT_ACCESSIBLE,
            301: sources.STATUT_INATTENDU, 302: sources.STATUT_INATTENDU,
            401: sources.STATUT_REFUSE, 403: sources.STATUT_REFUSE, 429: sources.STATUT_REFUSE,
            404: sources.STATUT_INTROUVABLE, 410: sources.STATUT_INTROUVABLE,
            500: sources.STATUT_INDISPONIBLE, 502: sources.STATUT_INDISPONIBLE, 503: sources.STATUT_INDISPONIBLE,
            418: sources.STATUT_INATTENDU,
        }
        for code, statut in attendus.items():
            self.assertEqual(sources.classer_statut(code), statut, "HTTP %s" % code)

    def test_absence_de_reponse_est_injoignable(self):
        self.assertEqual(sources.classer_statut(None), sources.STATUT_INJOIGNABLE)

    def test_un_503_n_est_jamais_un_succes(self):
        self.assertNotEqual(sources.classer_statut(503), sources.STATUT_ACCESSIBLE)


class TestPerimetreOfficiel(unittest.TestCase):
    def test_gouv_ci_accepte(self):
        self.assertTrue(sources.est_hote_officiel("https://www.sgg.gouv.ci/journal"))
        self.assertTrue(sources.est_hote_officiel("https://sgg.gouv.ci/"))

    def test_registre_accepte(self):
        self.assertTrue(sources.est_hote_officiel("https://www.cndj.ci/bases-de-recherche/x.html"))
        self.assertTrue(sources.est_hote_officiel("https://biblio.cndj.ci/livre/1"))

    def test_hors_perimetre_refuse(self):
        for url in ("https://un-blog.example/article", "https://facebook.com/post",
                    "http://forum-juridique.net/loi", "", None):
            self.assertFalse(sources.est_hote_officiel(url), "accepté à tort : %r" % (url,))


class TestRegistre(unittest.TestCase):
    def test_les_trois_sources_du_cadre_sont_presentes(self):
        urls = [s["url"] for s in SOURCES_OFFICIELLES]
        for attendu in ("https://www.sgg.gouv.ci/", "https://www.cndj.ci/", "https://jorci.oneci.ci/"):
            self.assertIn(attendu, urls)

    def test_chaque_source_est_complete(self):
        for source in SOURCES_OFFICIELLES:
            for champ in ("id", "nom", "url", "role", "type"):
                self.assertTrue(source.get(champ), "champ %s vide pour %s" % (champ, source.get("id")))
            self.assertTrue(source["url"].startswith("https://"))


class TestRapport(unittest.TestCase):
    def test_les_sources_jamais_testees_sont_nommees(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "verifs.json")
            rapport = sources.rapport_sources(chemin)
            self.assertEqual(rapport["nb_verifications_enregistrees"], 0)
            self.assertEqual(len(rapport["jamais_testees"]), len(SOURCES_OFFICIELLES))
            for ligne in rapport["sources"]:
                self.assertEqual(ligne["statut"], "JAMAIS_TESTEE")
                self.assertIsNone(ligne["date_consultation"])
            self.assertIn("ACCESSIBILITÉ", rapport["avertissement"])

    def test_le_rapport_distingue_acces_et_validite(self):
        with tempfile.TemporaryDirectory() as dossier:
            rapport = sources.rapport_sources(os.path.join(dossier, "v.json"))
            self.assertIn("pas sur la validité", rapport["avertissement"])


class TestEchecReseauDeclare(unittest.TestCase):
    def test_hote_inexistant_donne_injoignable_avec_erreur(self):
        """Un échec réseau est enregistré, jamais converti en succès."""
        rec = sources.verifier_url("https://hote-absolument-inexistant.invalid/", timeout=10)
        self.assertEqual(rec["statut"], sources.STATUT_INJOIGNABLE)
        self.assertIsNone(rec["http_status"])
        self.assertTrue(rec["erreur"], "l'échec doit porter un message")
        self.assertTrue(rec["date_consultation"])

    def test_journalisation_atomique(self):
        with tempfile.TemporaryDirectory() as dossier:
            chemin = os.path.join(dossier, "v.json")
            rec = sources.verifier_url("https://hote-absolument-inexistant.invalid/", timeout=10)
            rec["source_id"] = "TEST"
            sources.enregistrer_verifications([rec], chemin=chemin)
            sources.enregistrer_verifications([rec], chemin=chemin)
            self.assertEqual(len(sources.charger_verifications(chemin)), 2)
            self.assertIsNotNone(sources.derniere_verification("TEST", chemin))
            self.assertIsNone(sources.derniere_verification("INCONNU", chemin))


if __name__ == "__main__":
    unittest.main(verbosity=2)
