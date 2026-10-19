# -*- coding: utf-8 -*-
"""Collecte documentaire : parseur d'articles étendu, contrôles et classement des sources."""

import json
import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "bin"))

from core import corpus  # noqa: E402
import integrer_collecte  # noqa: E402


class TestNumerotationDecimale(unittest.TestCase):
    """Le Code du travail de 2015 numérote « Art. 18.12 » : le parseur doit le lire."""

    def test_article_decimal_seul_sur_sa_ligne(self):
        articles = corpus.extraire_articles("Art. 18.12\nLe contrat est rompu.\nArt 18.13\nSuite.")
        self.assertEqual(articles, {"18.12": "Le contrat est rompu.", "18.13": "Suite."})

    def test_point_final_n_est_pas_une_decimale(self):
        articles = corpus.extraire_articles("Article 552. La présente loi entre en vigueur.")
        self.assertEqual(articles, {"552": "La présente loi entre en vigueur."})

    def test_mention_nouveau(self):
        articles = corpus.extraire_articles("Art. 18.14 nouveau\nTexte modifié.")
        self.assertEqual(articles, {"18.14": "Texte modifié."})

    def test_renvoi_dans_une_phrase_n_est_pas_un_article(self):
        articles = corpus.extraire_articles("Article 4 - Texte.\nl'article 5 du code reste applicable")
        self.assertEqual(list(articles), ["4"])

    def test_couverture_decimale(self):
        articles = {"1": "a", "2": "b", "3.1": "c", "3.2": "d", "3.4": "e"}
        taux, maximum = corpus.taux_couverture(articles)
        # 1, 2, puis 3.1..3.4 attendus (4) dont 3 présents : 5 / 6.
        self.assertEqual(maximum, 3)
        self.assertAlmostEqual(taux, 5 / 6.0)

    def test_couverture_inchangee_sans_decimale(self):
        self.assertEqual(corpus.taux_couverture({"1": "a", "2": "b", "4": "c"}), (0.75, 4))


class TestFormeLitterale(unittest.TestCase):
    def test_article_premier_long_n_efface_pas_l_article_1(self):
        texte = ("Article 1\nCourt.\n"
                 "Article premier\n" + "Une disposition beaucoup plus longue d'un autre texte. " * 5)
        articles = corpus.extraire_articles(texte)
        self.assertEqual(articles.get("1"), "Court.")

    def test_forme_chiffree_remplace_la_forme_litterale(self):
        texte = "Article premier\n" + "Long. " * 20 + "\nArticle 1\nCourt."
        self.assertEqual(corpus.extraire_articles(texte).get("1"), "Court.")


class TestControleDesDocuments(unittest.TestCase):
    def _resultat(self, **extraction):
        base = {"statut": "TELECHARGE", "sha256": "sha256:x", "octets": 10, "pdf": {"qpdf_check": "ok"},
                "extraction": dict({"pages": 1}, **extraction)}
        return base

    def test_document_officiel_sans_texte_ni_numero_en_quarantaine(self):
        source = {"cle": "x", "url": "https://exemple.gouv.ci/x.pdf", "categorie_source": "OFFICIEL_PORTAIL_GOUV",
                  "type_texte": "loi", "numero_texte": "2019-570"}
        fiche = integrer_collecte.controler_document(source, self._resultat())
        self.assertEqual(fiche["statut_controle"], "QUARANTAINE")

    def test_variantes_de_numero(self):
        motifs = integrer_collecte._variantes_numero("2019-570")
        self.assertTrue(any(m.search("LOI N° 2019 - 570 DU 26 JUIN") for m in motifs))
        self.assertFalse(any(m.search("LOI N° 2019-5701") for m in motifs))


class TestManifeste(unittest.TestCase):
    """Le manifeste déclare la catégorie de chaque source : jamais déduite, jamais vide."""

    def setUp(self):
        with open(os.path.join(RACINE, "KNOWLEDGE", "collecte", "manifeste.json"), encoding="utf-8") as flux:
            self.manifeste = json.load(flux)

    def test_cles_uniques_et_categories_connues(self):
        cles = [s["cle"] for s in self.manifeste["sources"]]
        self.assertEqual(len(cles), len(set(cles)))
        for source in self.manifeste["sources"]:
            self.assertIn(source["categorie_source"], self.manifeste["categories"], source["cle"])

    def test_reproductions_tierces_jamais_declarees_officielles(self):
        tiers = ("laws.africa", "civlii", "senlii", "faolex", "ohada.com", "uvci", "bice.org", "ilo.org")
        for source in self.manifeste["sources"]:
            if any(t in source["url"] for t in tiers):
                self.assertFalse(source["categorie_source"].startswith("OFFICIEL"), source["cle"])

    def test_sources_officielles_sur_un_hote_du_registre_ou_assumees(self):
        from core.sources import est_hote_officiel
        for source in self.manifeste["sources"]:
            if source["categorie_source"] in ("OFFICIEL_PORTAIL_GOUV", "OFFICIEL_ORGANISATION", "OFFICIEL_JO"):
                self.assertTrue(est_hote_officiel(source["url"]), source["cle"])


if __name__ == "__main__":
    unittest.main()
