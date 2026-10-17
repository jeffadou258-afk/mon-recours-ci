# -*- coding: utf-8 -*-
"""Tests de l'interface fournisseur de langage.

Ce qui est prouvé ici : un fournisseur — même factice, même bavard — ne peut pas
faire entrer un article inventé dans une réponse. Le moteur filtre. Et en cas
d'indisponibilité ou de délai dépassé, le service retombe sur le déterministe.

Ce qui n'est PAS prouvé : qu'un vrai fournisseur fonctionne. Aucun appel réel n'a
été effectué, aucune dépense engagée. `statut()["operationnel"]` doit valoir False.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import llm  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _source(relatif):
    with open(os.path.join(RACINE, relatif), encoding="utf-8") as flux:
        return flux.read()


class TestFournisseurParDefaut(unittest.TestCase):
    def test_le_fournisseur_par_defaut_est_desactive(self):
        fournisseur = llm.obtenir_fournisseur()
        self.assertIsInstance(fournisseur, llm.FournisseurDesactive)
        self.assertFalse(fournisseur.disponible())

    def test_un_fournisseur_desactive_leve_et_ne_renvoie_rien(self):
        with self.assertRaises(llm.FournisseurIndisponible):
            llm.obtenir_fournisseur().proposer("Ma caution n'a pas été rendue.")

    def test_statut_ne_declare_jamais_operationnel(self):
        etat = llm.statut()
        self.assertFalse(etat["operationnel"])
        self.assertIn("n'est PAS opérationnel", etat["avertissement"])
        self.assertIn("variable_cle", etat["configuration"])

    def test_aucune_cle_par_defaut(self):
        ancienne = os.environ.pop(llm.NOM_VARIABLE_CLE, None)
        try:
            adaptateur = llm.charger_adaptateur_http()
            self.assertIsNotNone(adaptateur, "bin/fournisseur_http.py doit exister")
            self.assertFalse(adaptateur.FournisseurHTTP().disponible())
            self.assertFalse(llm.statut()["configuration"]["cle_presente"])
        finally:
            if ancienne is not None:
                os.environ[llm.NOM_VARIABLE_CLE] = ancienne

    def test_le_coeur_ne_contient_aucun_client_reseau(self):
        """Le transport vit en bordure : le cœur ne doit pas savoir faire de réseau."""
        for marque in ("urllib", "socket", "http.client", "requests"):
            self.assertNotIn(marque, _source("core/llm.py"),
                             "core/llm.py ne doit pas importer %s" % marque)

    def test_l_adaptateur_reseau_est_en_bordure(self):
        source = _source("bin/fournisseur_http.py")
        self.assertIn("urllib.request", source)
        self.assertNotIn("def valider_propositions", source,
                         "les contrôles restent dans le cœur, jamais dans l'adaptateur")


class TestFiltrageDesPropositions(unittest.TestCase):
    """Le cœur du dispositif : ce qui n'est pas dans le corpus est rejeté."""

    def _fiche(self):
        from core import catalogue
        return catalogue.charger()[0]

    def test_proposition_valide_acceptee(self):
        fiche = self._fiche()
        acceptees, rejets = llm.valider_propositions([
            {"ref_id": fiche["ref_id"], "article": fiche["article"],
             "citation": fiche["citation"]}])
        self.assertEqual(len(acceptees), 1)
        self.assertEqual(rejets, [])
        self.assertTrue(acceptees[0]["sha256_article"].startswith("sha256:"))

    def test_article_invente_rejete(self):
        fiche = self._fiche()
        acceptees, rejets = llm.valider_propositions([
            {"ref_id": "REF-INVENTEE", "article": "1", "citation": "Texte inventé de toutes pièces."}])
        self.assertEqual(acceptees, [])
        self.assertIn("ARTICLE_INCONNU", rejets[0]["raison"])

    def test_citation_modifiee_rejetee(self):
        fiche = self._fiche()
        acceptees, rejets = llm.valider_propositions([
            {"ref_id": fiche["ref_id"], "article": fiche["article"],
             "citation": fiche["citation"][:-25] + " et le bailleur doit rembourser le double."}])
        self.assertEqual(acceptees, [])
        self.assertIn("CITATION_ABSENTE", rejets[0]["raison"])

    def test_champs_incomplets_rejetes(self):
        acceptees, rejets = llm.valider_propositions([{"article": "1"}, "pas un dict"])
        self.assertEqual(acceptees, [])
        self.assertEqual(len(rejets), 2)

    def test_un_fournisseur_bavard_ne_fait_pas_entrer_d_article_invente(self):
        fiche = self._fiche()
        bavard = llm.FournisseurFactice({"propositions": [
            {"ref_id": fiche["ref_id"], "article": fiche["article"],
             "citation": fiche["citation"]},
            {"ref_id": "REF-BIDON", "article": "9999", "citation": "Article 9999 : le bail est gratuit."}]})
        rapport = llm.proposer_avec_repli("Ma caution", contextes=[fiche], fournisseur=bavard)
        references = {a["ref_id"] for a in rapport["acceptees"]}
        self.assertIn(fiche["ref_id"], references)
        self.assertNotIn("REF-BIDON", references)
        self.assertTrue(rapport["rejets"])


class TestRepliDeterministe(unittest.TestCase):
    def _fiches(self):
        from core import catalogue
        return catalogue.charger()[:2]

    def test_repli_quand_le_fournisseur_est_indisponible(self):
        fiches = self._fiches()
        rapport = llm.proposer_avec_repli("Ma caution", contextes=fiches,
                                          fournisseur=llm.FournisseurDesactive())
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertEqual(len(rapport["acceptees"]), len(fiches))
        self.assertIn("aucun fournisseur", rapport["erreur"].lower())

    def test_repli_quand_le_delai_est_depasse(self):
        fiches = self._fiches()
        lent = llm.FournisseurFactice(delai_avant=10.0)
        rapport = llm.proposer_avec_repli("Ma caution", contextes=fiches,
                                          fournisseur=lent, delai=0.5)
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertIn("délai", rapport["erreur"])

    def test_repli_quand_le_fournisseur_leve(self):
        fiches = self._fiches()
        casse = llm.FournisseurFactice(erreur=llm.ErreurFournisseur("service indisponible"))
        rapport = llm.proposer_avec_repli("Ma caution", contextes=fiches, fournisseur=casse)
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertIn("indisponible", rapport["erreur"])

    def test_repli_quand_aucune_proposition_n_est_acceptee(self):
        fiches = self._fiches()
        hors_sujet = llm.FournisseurFactice({"propositions": [
            {"ref_id": "REF-X", "article": "1", "citation": "Rien de réel."}]})
        rapport = llm.proposer_avec_repli("Ma caution", contextes=fiches,
                                          fournisseur=hors_sujet)
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertEqual(len(rapport["acceptees"]), len(fiches))
        self.assertTrue(rapport["rejets"])

    def test_le_service_fonctionne_sans_fournisseur(self):
        """Le mode déterministe n'a besoin d'aucun fournisseur pour répondre."""
        from core import catalogue
        fiches = catalogue.charger()
        self.assertGreater(len(fiches), 0)
        rapport = llm.proposer_avec_repli("test", contextes=fiches[:1])
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertEqual(len(rapport["acceptees"]), 1)


class TestAucunSecretDansLeCode(unittest.TestCase):
    def test_le_module_ne_contient_aucune_cle_litterale(self):
        chemin = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "core", "llm.py")
        with open(chemin, encoding="utf-8") as flux:
            contenu = flux.read()
        for marque in ("sk-", "api_key =", "apikey =", "Bearer sk"):
            self.assertNotIn(marque, contenu.replace("'", '"'))
        self.assertIn("MONRECOURS_LLM_API_KEY", contenu)


if __name__ == "__main__":
    unittest.main(verbosity=2)
