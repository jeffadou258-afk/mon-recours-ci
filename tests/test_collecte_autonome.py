# -*- coding: utf-8 -*-
"""Reprise autonome de la collecte (20/10/2026) — garde-fous des outils ajoutés.

* la normalisation des en-têtes OCR ne touche QUE l'en-tête d'un article, exige
  le tiret du Journal officiel et ne crée jamais d'article à partir d'une phrase ;
* le manifeste ne perd aucune entrée : les échecs définitifs sont désactivés
  avec un motif, jamais supprimés ;
* le collecteur distant consigne chaque tentative.
"""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "bin"))

from core import corpus, ocr  # noqa: E402

MANIFESTE = os.path.join(RACINE, "KNOWLEDGE", "collecte", "manifeste.json")


class TestEnTetesOCR(unittest.TestCase):
    def test_en_tetes_mal_lus_retablis(self):
        texte = ("An. 2. — Le mineur est l'individu de l'un ou l'autre sexe.\n"
                 "Ant, 4, — L'autorité parentale appartient aux père et mère.\n"
                 "Art.6. — Si les père et mère sont divorcés, le juge statue.\n"
                 "Aït 10. — Le juge des tutelles est compétent.\n")
        corrige, corrections = ocr.normaliser_en_tetes_jo(texte)
        articles = corpus.extraire_articles(corrige)
        self.assertEqual(sorted(articles, key=int), ["2", "4", "6", "10"])
        self.assertEqual(len(corrections), 4)

    def test_le_corps_des_articles_n_est_jamais_modifie(self):
        corps = "Le mineur devenu majeur ne peut plus attaquer l'engagement. An 2019 : rien."
        corrige, _ = ocr.normaliser_en_tetes_jo("An. 39, — " + corps + "\n")
        attendu = corpus.extraire_articles("Art. 39. — " + corps + "\n")["39"]
        self.assertEqual(corpus.extraire_articles(corrige)["39"], attendu)
        self.assertTrue(attendu.endswith(corps))

    def test_en_tete_deja_lisible_ni_modifie_ni_compte(self):
        texte = "Art. 5. — Durant le mariage, l'autorité parentale est exercée.\nArt. 14, — La délégation.\n"
        corrige, corrections = ocr.normaliser_en_tetes_jo(texte)
        self.assertEqual(corrige, texte)
        self.assertEqual(corrections, [])

    def test_aucune_phrase_ordinaire_ne_devient_un_article(self):
        for ligne in ("An 2019, le législateur a réformé la minorité.",
                      "At 10 heures, l'audience est ouverte.",
                      "Art 12 du code précité est applicable.",
                      "An. 2 ans après la décision, le juge peut statuer."):
            corrige, corrections = ocr.normaliser_en_tetes_jo(ligne + "\n")
            self.assertEqual(corrections, [], ligne)
            self.assertEqual(corrige, ligne + "\n")

    def test_seulement_en_debut_de_ligne(self):
        texte = "conformément à l'An. 12. — disposition citée\n"
        self.assertEqual(ocr.normaliser_en_tetes_jo(texte)[1], [])


class TestManifesteReprise(unittest.TestCase):
    def setUp(self):
        self.manifeste = json.load(open(MANIFESTE, encoding="utf-8"))
        self.cles = {s["cle"]: s for s in self.manifeste["sources"]}

    def test_aucune_cle_en_double(self):
        cles = [s["cle"] for s in self.manifeste["sources"]]
        self.assertEqual(len(cles), len(set(cles)))

    def test_desactivation_motivee_et_jamais_sur_un_succes(self):
        for cle, source in self.cles.items():
            if not source.get("desactivee"):
                continue
            self.assertTrue(source["desactivee"].get("motif"), cle)
            chemin = os.path.join(RACINE, "KNOWLEDGE", "collecte", "resultats", cle + ".json")
            if os.path.isfile(chemin):
                statut = json.load(open(chemin, encoding="utf-8")).get("statut")
                self.assertNotIn(statut, ("TELECHARGE", "DECOUVERTE"), cle)
            remplacante = source["desactivee"].get("remplacee_par")
            if remplacante:
                self.assertIn(remplacante, self.cles, cle)

    def test_les_url_civlii_ont_la_forme_qui_repond(self):
        """Les 404 du 19/10 venaient de `/source.pdf`, `/fr/.../publication` et du résolveur."""
        for cle, source in self.cles.items():
            if source.get("desactivee") or "laws.africa" not in source["url"]:
                continue
            self.assertNotIn("resolver.laws.africa", source["url"], cle)
            self.assertFalse(source["url"].endswith("/source.pdf"), cle)
            if source["url"].endswith("/publication"):
                self.assertIn("/en/akn/", source["url"], cle)

    def test_une_reproduction_n_est_jamais_declaree_officielle(self):
        for cle, source in self.cles.items():
            if "laws.africa" in source["url"] or "faolex" in source["url"]:
                self.assertFalse(source["categorie_source"].startswith("OFFICIEL"), cle)

    def test_reprise_idempotente(self):
        import manifeste_reprise
        with tempfile.TemporaryDirectory() as dossier:
            copie = os.path.join(dossier, "manifeste.json")
            with open(copie, "w", encoding="utf-8") as flux:
                json.dump(self.manifeste, flux, ensure_ascii=False)
            with mock.patch.object(manifeste_reprise, "MANIFESTE", copie):
                manifeste_reprise.main()
            apres = json.load(open(copie, encoding="utf-8"))
        self.assertEqual(len(apres["sources"]), len(self.manifeste["sources"]))


class TestHistoriqueDesTentatives(unittest.TestCase):
    def test_chaque_tentative_est_conservee(self):
        import collecte_distante as cd
        with tempfile.TemporaryDirectory() as dossier:
            resultats = os.path.join(dossier, "resultats")
            os.makedirs(resultats)
            manifeste = os.path.join(dossier, "manifeste.json")
            source = {"cle": "essai", "url": "https://exemple.invalid/x.pdf", "mode": "fichier",
                      "categorie_source": "SECONDAIRE_AUTRE"}
            with open(manifeste, "w", encoding="utf-8") as flux:
                json.dump({"sources": [source]}, flux)
            reponses = iter([{"cle": "essai", "url": source["url"], "statut": "ECHEC_HTTP", "http": 503,
                              "date_recuperation": "2026-10-20T10:00:00+00:00"},
                             {"cle": "essai", "url": source["url"], "statut": "ECHEC_HTTP", "http": 404,
                              "date_recuperation": "2026-10-20T11:00:00+00:00"}])
            with mock.patch.object(cd, "MANIFESTE", manifeste), \
                    mock.patch.object(cd, "DOSSIER_RESULTATS", resultats), \
                    mock.patch.object(cd, "DOSSIER", dossier), \
                    mock.patch.object(cd, "version_outils", lambda: {}), \
                    mock.patch.object(cd, "traiter", lambda s: dict(next(reponses))):
                cd.main([])
                cd.main([])
            constat = json.load(open(os.path.join(resultats, "essai.json"), encoding="utf-8"))
        self.assertEqual([t["http"] for t in constat["historique"]], [503, 404])

    def test_entree_desactivee_jamais_retentee(self):
        import collecte_distante as cd
        with tempfile.TemporaryDirectory() as dossier:
            os.makedirs(os.path.join(dossier, "resultats"))
            manifeste = os.path.join(dossier, "manifeste.json")
            with open(manifeste, "w", encoding="utf-8") as flux:
                json.dump({"sources": [{"cle": "morte", "url": "https://exemple.invalid/y.pdf",
                                        "desactivee": {"motif": "404"}}]}, flux)
            appel = mock.Mock()
            with mock.patch.object(cd, "MANIFESTE", manifeste), \
                    mock.patch.object(cd, "DOSSIER_RESULTATS", os.path.join(dossier, "resultats")), \
                    mock.patch.object(cd, "DOSSIER", dossier), \
                    mock.patch.object(cd, "version_outils", lambda: {}), \
                    mock.patch.object(cd, "traiter", appel):
                cd.main([])
        appel.assert_not_called()


if __name__ == "__main__":
    unittest.main()
