# -*- coding: utf-8 -*-
"""Corpus : métadonnées obligatoires, états de vérification, citations vérifiables.

Aucun test de ce fichier ne contient de règle de droit. On y teste le CONTRAT du
corpus : ce qui ne peut pas entrer, ce qui ne peut pas être promu, ce qui ne peut
pas être cité.
"""

import os
import shutil
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import base  # noqa: E402

REF_VALIDE = dict(
    titre_officiel="Texte de test (contenu fictif de test, non juridique)",
    type_texte="loi",
    source_nom="Centre National de Documentation Juridique",
    source_url="https://www.cndj.ci/bases-de-recherche/textes-legislatifs-et-reglementaires.html",
    date_consultation="2026-10-16",
    numero_texte="TEST-0000",
    articles="Article fictif 1",
    domaine="logement_baux_foncier",
    extrait_texte="Extrait fictif de test : le présent texte ne sert qu'à valider le contrat.",
)


class BaseDeTest(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="mrc_base_")
        self.chemin = os.path.join(self.dossier, "corpus_test.sqlite3")
        base.initialiser(self.chemin)

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def ajouter(self, **surcharges):
        parametres = dict(REF_VALIDE)
        parametres.update(surcharges)
        return base.ajouter_reference(chemin=self.chemin, **parametres)


class TestMetadonneesObligatoires(BaseDeTest):
    def test_insertion_valide(self):
        ref_id = self.ajouter()
        self.assertTrue(ref_id.startswith("REF-"))
        ref = base.obtenir_reference(ref_id, self.chemin)
        self.assertEqual(ref["etat_verification"], "NON_VERIFIE")

    def test_sans_titre_refuse(self):
        with self.assertRaises(ValueError) as ctx:
            self.ajouter(titre_officiel="   ")
        self.assertIn("titre_officiel", str(ctx.exception))

    def test_sans_source_refuse(self):
        with self.assertRaises(ValueError) as ctx:
            self.ajouter(source_nom="")
        self.assertIn("source_nom", str(ctx.exception))

    def test_sans_date_de_consultation_refusee(self):
        with self.assertRaises(ValueError) as ctx:
            self.ajouter(date_consultation=None)
        self.assertIn("date_consultation", str(ctx.exception))

    def test_url_non_http_refusee(self):
        with self.assertRaises(ValueError):
            self.ajouter(source_url="www.exemple.ci")

    def test_date_non_iso_refusee(self):
        with self.assertRaises(ValueError):
            self.ajouter(date_consultation="16/10/2026")

    def test_le_schema_refuse_aussi_en_direct(self):
        """Défense en profondeur : même en contournant l'API, le SQL refuse."""
        with sqlite3.connect(self.chemin) as conn:
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute(
                    "INSERT INTO references_juridiques (ref_id, titre_officiel, type_texte,"
                    " source_nom, source_url, date_consultation, cree_le, maj_le)"
                    " VALUES ('X','T','loi','S','pas-une-url','2026-01-01','x','x')"
                )

    def test_cle_deterministe_et_non_ecrasante(self):
        premier = self.ajouter()
        base.promouvoir_verification(
            premier, "VERIFIE", preuve_url="https://www.cndj.ci/",
            preuve_empreinte="sha256:" + "c" * 64, date_consultation="2026-10-16",
            chemin=self.chemin)
        second = self.ajouter(extrait_texte="contenu différent saisi plus tard")
        self.assertEqual(premier, second)
        self.assertEqual(len(base.lister_references(chemin=self.chemin)), 1)
        ref = base.obtenir_reference(premier, self.chemin)
        self.assertEqual(ref["etat_verification"], "VERIFIE",
                         "une ré-enregistrement a rétrogradé une référence vérifiée")
        self.assertNotEqual(ref["extrait_texte"], "contenu différent saisi plus tard")

    def test_deux_textes_differents_deux_cles(self):
        un = self.ajouter(numero_texte="A-1")
        deux = self.ajouter(numero_texte="B-2")
        self.assertNotEqual(un, deux)


class TestVerification(BaseDeTest):
    def test_defaut_non_verifie(self):
        ref_id = self.ajouter()
        self.assertEqual(base.obtenir_reference(ref_id, self.chemin)["etat_verification"],
                         "NON_VERIFIE")

    def test_promotion_sans_preuve_refusee(self):
        ref_id = self.ajouter()
        for incomplet in (
            dict(preuve_url="https://www.cndj.ci/", preuve_empreinte="sha256:x"),
            dict(preuve_empreinte="sha256:x", date_consultation="2026-10-16"),
            dict(preuve_url="https://www.cndj.ci/", date_consultation="2026-10-16"),
        ):
            with self.assertRaises(ValueError) as ctx:
                base.promouvoir_verification(ref_id, "VERIFIE", chemin=self.chemin, **incomplet)
            self.assertIn("preuve incomplète", str(ctx.exception))
        self.assertEqual(base.obtenir_reference(ref_id, self.chemin)["etat_verification"],
                         "NON_VERIFIE")

    def test_promotion_hors_perimetre_officiel_refusee(self):
        ref_id = self.ajouter()
        with self.assertRaises(ValueError) as ctx:
            base.promouvoir_verification(
                ref_id, "VERIFIE",
                preuve_url="https://un-blog-quelconque.example/article.html",
                preuve_empreinte="sha256:abc",
                date_consultation="2026-10-16",
                chemin=self.chemin,
            )
        self.assertIn("périmètre", str(ctx.exception))

    def test_promotion_valide_journalisee(self):
        ref_id = self.ajouter()
        ref = base.promouvoir_verification(
            ref_id, "VERIFIE",
            preuve_url="https://www.cndj.ci/bases-de-recherche/codes-et-recueils-de-textes.html",
            preuve_empreinte="sha256:" + "a" * 64,
            date_consultation="2026-10-16",
            motif="consultation directe",
            chemin=self.chemin,
        )
        self.assertEqual(ref["etat_verification"], "VERIFIE")
        historique = base.historique_verifications(ref_id, self.chemin)
        self.assertEqual(len(historique), 1)
        self.assertEqual(historique[0]["etat_precedent"], "NON_VERIFIE")
        self.assertEqual(historique[0]["motif"], "consultation directe")

    def test_etat_inconnu_refuse(self):
        ref_id = self.ajouter()
        with self.assertRaises(ValueError):
            base.promouvoir_verification(ref_id, "A_PEUT_ETRE", chemin=self.chemin)


class TestCitations(BaseDeTest):
    def test_citation_dans_un_texte_non_integral_non_verifiable(self):
        ref_id = self.ajouter()
        ok, raison = base.verifier_citation(ref_id, "Extrait fictif de test", chemin=self.chemin)
        self.assertFalse(ok)
        self.assertIn("texte intégral non présent", raison)

    def test_citation_retrouvee(self):
        ref_id = self.ajouter(texte_complet_present=True)
        ok, raison = base.verifier_citation(ref_id, "le présent texte ne sert qu'à valider",
                                            chemin=self.chemin)
        self.assertTrue(ok, raison)

    def test_citation_inventee_refusee(self):
        ref_id = self.ajouter(texte_complet_present=True)
        ok, raison = base.verifier_citation(
            ref_id, "tout locataire a droit à une indemnité de trois mois", chemin=self.chemin)
        self.assertFalse(ok)
        self.assertIn("ABSENTE", raison)

    def test_reference_inconnue(self):
        ok, raison = base.verifier_citation("REF-INEXISTANTE", "x", chemin=self.chemin)
        self.assertFalse(ok)
        self.assertIn("inconnue", raison)


class TestRechercheEtStats(BaseDeTest):
    def test_recherche_tolere_accents_et_casse(self):
        self.ajouter()
        self.assertEqual(len(base.rechercher("TEXTE DE TEST", self.chemin)), 1)
        self.assertEqual(len(base.rechercher("zzzz-introuvable", self.chemin)), 0)

    def test_liste_vide_est_une_reponse(self):
        self.assertEqual(base.rechercher("bail", self.chemin), [])

    def test_statistiques_nomment_tous_les_etats(self):
        self.ajouter()
        stats = base.statistiques(self.chemin)
        self.assertEqual(stats["total_references"], 1)
        for etat in ("VERIFIE", "PARTIELLEMENT_VERIFIE", "NON_VERIFIE", "NON_CONFIRME", "OBSOLETE"):
            self.assertIn(etat, stats["tous_les_etats_nommes"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
