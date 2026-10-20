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


# ---------------------------------------------------------------------------
# Intégration OCR : règles de sûreté
# ---------------------------------------------------------------------------
class TestReglesIntegrationOCR(unittest.TestCase):
    def setUp(self):
        import integrer_collecte
        self.ic = integrer_collecte

    def test_nombre_remplace_detecte(self):
        self.assertEqual(self.ic.nombres_substitues("ainsi que des articles 43, 51 et 56.",
                                                    "ainsi que des articles 45, 51 et 56."), [("43", "45")])

    def test_numero_de_page_incruste_n_est_pas_une_substitution(self):
        self.assertEqual(self.ic.nombres_substitues("dans un délai de 3 202 mois", "dans un délai de 3 mois"), [])

    def test_journal_des_integrations_present_et_coherent(self):
        chemin = os.path.join(RACINE, "KNOWLEDGE", "collecte", "integrations_ocr.json")
        journal = json.load(open(chemin, encoding="utf-8"))["integrations"]
        for cle in ("mffe_code_penal_2019_574", "mffe_mariage_2019_570", "mffe_successions_2019_573"):
            self.assertIn(cle, journal)
            entree = journal[cle]
            self.assertGreaterEqual(entree["couverture"], corpus.COUVERTURE_MINIMALE, cle)
            # la copie FAOLEX du calque ABBYY du mariage ne doit jamais servir d'étalon
            self.assertNotIn("mariage_2019_570_faolex", entree["etalons"] or "")
        self.assertIn("SECONDAIRE:mariage_2019_570_faolex", journal["mffe_mariage_2019_570"]["copies_ecartees"])

    def test_articles_indexes_viennent_du_scan_officiel(self):
        journal = json.load(open(os.path.join(RACINE, "KNOWLEDGE", "collecte", "integrations_ocr.json"),
                                 encoding="utf-8"))["integrations"]
        for cle, entree in journal.items():
            for numero, lecture in entree["lecture_par_article"].items():
                self.assertTrue(lecture.startswith(("CALQUE_EDITEUR", "TESSERACT_")), (cle, numero, lecture))


class TestNouvellesFiches(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from core import catalogue
        cls.fiches = {f["id"]: f for f in catalogue.charger()}

    def test_fiches_chargees_et_traçables(self):
        for prefixe, numero in (("MARIAGE_", "2019-570"), ("SUCC_", "2019-573"), ("PENAL_", "2019-574")):
            lot = [f for i, f in self.fiches.items() if i.startswith(prefixe)]
            self.assertGreaterEqual(len(lot), 10, prefixe)
            for f in lot:
                self.assertEqual(f["numero_texte"], numero)
                self.assertEqual(f["origine_texte"], "OCR_AUTO")      # provenance déclarée
                self.assertNotEqual(f["etat_verification"], "VERIFIE")  # jamais relu par un juriste
                self.assertTrue(f["sha256_article"])

    def test_aucune_lecture_n_ajoute_un_nombre_absent_de_l_article(self):
        from core import clarification
        from core.base import normaliser
        for fid, f in self.fiches.items():
            if not fid.startswith(("PENAL_", "MARIAGE_", "SUCC_")):
                continue
            article = corpus.obtenir_article_par_reference(f["ref_id"], f["article"])
            ajoutes = clarification._nombres(normaliser(f["lecture"])) - clarification._nombres(normaliser(article["texte"]))
            self.assertEqual(ajoutes, set(), fid)

    def test_declencheurs_discriminants(self):
        """Un déclencheur se réduit à ses mots de 4 lettres ou plus : « mon mari me bat »
        devenait « mari » et servait la fiche au premier « souci avec mon mari »."""
        import re
        from core.base import normaliser
        generiques = {"pour", "peine", "mari", "femme", "mariage", "enfant", "enfants", "vole", "maison"}
        for fid, f in self.fiches.items():
            if not fid.startswith(("PENAL_", "MARIAGE_", "SUCC_")):
                continue
            for t in f["declencheurs"]:
                mots = {m for m in re.findall(r"[a-z0-9']+", normaliser(t)) if len(m) >= 4}
                self.assertFalse(mots and mots <= generiques, (fid, t))

    def test_faux_positifs_connus(self):
        from core import catalogue
        from core.base import normaliser
        for recit, interdite in (("j'ai un souci avec mon mari", "MARIAGE_46"),
                                 ("Quelle est la peine pour piratage informatique ?", "PENAL_458"),
                                 ("on m'a volé mon idée", "PENAL_457"),
                                 ("le bailleur a violé le contrat", "PENAL_403"),
                                 ("Après combien d'années de mariage obtient-on la nationalité ?", "MARIAGE_103")):
            n = normaliser(recit)
            servies = {f["id"] for f in self.fiches.values() for m in f["declencheurs"] if catalogue._correspond(m, n)}
            self.assertNotIn(interdite, servies, recit)


class TestUrgencesAjoutees(unittest.TestCase):
    def test_violences_sexuelles_et_mutilations(self):
        from core import urgence
        for recit in ("j'ai été violée hier", "Un voisin a abusé sexuellement de ma fille",
                      "elle a été victime d'attouchements", "ils veulent exciser ma fille"):
            self.assertEqual(urgence.detecter(recit)["niveau"], "CRITIQUE", recit)

    def test_sens_juridique_de_violer_sans_alerte(self):
        from core import urgence
        for recit in ("le bailleur a violé le contrat de bail", "ils ont violé les règles", "il a violé la loi"):
            self.assertEqual(urgence.detecter(recit)["niveau"], "NORMALE", recit)

    def test_mariage_force_et_menaces_d_un_proche(self):
        from core import urgence
        self.assertNotEqual(urgence.detecter("on veut la marier de force")["niveau"], "NORMALE")
        self.assertNotEqual(urgence.detecter("mon mari me menace")["niveau"], "NORMALE")


# ---------------------------------------------------------------------------
# Reconstruction de la base et refus sans écriture (20/10/2026)
# ---------------------------------------------------------------------------
class TestReconstructionDeBase(unittest.TestCase):
    def _copie(self, dossier):
        import shutil
        import config
        copie = os.path.join(dossier, "copie.sqlite3")
        shutil.copyfile(str(config.CHEMIN_DB), copie)
        return copie

    def test_controles_passent_sur_la_base_active(self):
        import reconstruire_base as rb
        journal = os.path.join(RACINE, "KNOWLEDGE", "collecte", "integrations_ocr.json")
        with tempfile.TemporaryDirectory() as dossier:
            copie = self._copie(dossier)
            controles = rb.controler(copie, journal, copie)
        echecs = [c for c in controles if not c["ok"]]
        self.assertEqual(echecs, [], echecs)

    def test_reference_orpheline_detectee(self):
        """Une référence munie d'un extrait mais sans article indexé doit bloquer."""
        import sqlite3
        import reconstruire_base as rb
        with tempfile.TemporaryDirectory() as dossier:
            depart = self._copie(dossier)
            base = os.path.join(dossier, "base.sqlite3")
            import shutil
            shutil.copyfile(depart, base)
            conn = sqlite3.connect(base)
            colonnes = [c[1] for c in conn.execute("PRAGMA table_info(references_juridiques)")]
            ligne = dict(zip(colonnes, conn.execute("SELECT * FROM references_juridiques LIMIT 1").fetchone()))
            ligne.update(ref_id="REF-ORPHELINE0000", extrait_texte="Article 1\ntexte jamais indexé",
                         titre_officiel="Référence orpheline de test")
            conn.execute("INSERT INTO references_juridiques (%s) VALUES (%s)"
                         % (", ".join(ligne), ", ".join("?" * len(ligne))), list(ligne.values()))
            conn.commit()
            conn.close()
            controles = rb.controler(base, os.path.join(dossier, "absent.json"), depart)
        orpheline = [c for c in controles if c["controle"].startswith("aucune référence nouvelle")][0]
        self.assertFalse(orpheline["ok"])
        self.assertIn("REF-ORPHELINE0000", orpheline["detail"])

    def test_refus_de_couverture_n_ecrit_rien(self):
        """L'état civil (83 % < 85 %) est refusé : ni référence, ni document, ni journal."""
        import sqlite3
        import subprocess
        inventaire = json.load(open(os.path.join(RACINE, "KNOWLEDGE", "collecte", "inventaire_ressources.json"),
                                    encoding="utf-8"))
        if not any(d["cle"] == "mffe_etat_civil_2018_862" for d in inventaire["documents"]):
            self.skipTest("document absent de l'inventaire")
        with tempfile.TemporaryDirectory() as dossier:
            copie = self._copie(dossier)
            journal = os.path.join(dossier, "journal.json")
            avant = sqlite3.connect(copie)
            compte = lambda c: (c.execute("SELECT count(*) FROM references_juridiques").fetchone()[0],
                                c.execute("SELECT count(*) FROM documents").fetchone()[0],
                                c.execute("SELECT count(*) FROM articles_corpus").fetchone()[0])
            n_avant = compte(avant)
            avant.close()
            env = dict(os.environ, MONRECOURS_CHEMIN_DB=copie, MONRECOURS_JOURNAL_OCR=journal)
            sortie = subprocess.run([sys.executable, os.path.join(RACINE, "bin", "integrer_collecte.py"),
                                     "officialiser_ocr", "--cle", "mffe_etat_civil_2018_862"],
                                    env=env, capture_output=True, text=True, cwd=RACINE)
            self.assertIn("REFUSE", sortie.stdout)
            apres = sqlite3.connect(copie)
            self.assertEqual(compte(apres), n_avant)
            apres.close()
            self.assertFalse(os.path.isfile(journal))

    def test_lecture_partielle_documentee(self):
        chemin = os.path.join(RACINE, "KNOWLEDGE", "collecte", "lectures_partielles", "mffe_etat_civil_2018_862.json")
        rapport = json.load(open(chemin, encoding="utf-8"))
        self.assertTrue(rapport["decision"].startswith("NON_INTEGRE"))
        self.assertLess(rapport["couverture_fiable"], rapport["seuil_integration"])
        self.assertIn(2, rapport["pages_degradees"])
        self.assertEqual(rapport["articles"]["17"]["statut"], "ILLISIBLE")
        import sqlite3
        import config
        conn = sqlite3.connect(str(config.CHEMIN_DB))
        indexes = conn.execute("SELECT count(*) FROM articles_corpus a JOIN documents d ON d.doc_id = a.doc_id "
                               "WHERE d.url_source = ?", (rapport["url"],)).fetchone()[0]
        conn.close()
        self.assertEqual(indexes, 0, "un document refusé ne doit avoir aucun article indexé")


class TestRegistreDesCandidates(unittest.TestCase):
    def test_candidates_hors_du_perimetre_officiel(self):
        import config
        from core.sources import est_hote_officiel
        for candidate in config.SOURCES_CANDIDATES:
            self.assertFalse(est_hote_officiel(candidate["url"]), candidate["id"])
            self.assertTrue(candidate["manque"], candidate["id"])

    def test_documents_des_candidates_jamais_officiels(self):
        import urllib.parse
        import config
        hotes = {urllib.parse.urlparse(c["url"]).hostname.replace("www.", "") for c in config.SOURCES_CANDIDATES}
        manifeste = json.load(open(MANIFESTE, encoding="utf-8"))
        for s in manifeste["sources"]:
            hote = (urllib.parse.urlparse(s["url"]).hostname or "").replace("www.", "")
            if hote in hotes:
                self.assertFalse(s["categorie_source"].startswith("OFFICIEL"), s["cle"])

    def test_oapi_officielle_avec_preuves(self):
        import config
        oapi = config.source_par_id("OAPI")
        self.assertIsNotNone(oapi)
        self.assertTrue(any("OMPI" in p for p in oapi["preuves_identite"]))

    def test_brouillons_travail_non_charges(self):
        from core import catalogue
        ids = {f["id"] for f in catalogue.charger()}
        brouillons = json.load(open(os.path.join(RACINE, "KNOWLEDGE", "fiches_brouillons", "travail_2015_faolex.json"),
                                    encoding="utf-8"))
        self.assertEqual(brouillons["statut"], "BROUILLON_SOURCE_SECONDAIRE")
        for f in brouillons["fiches"]:
            self.assertNotIn(f["id"], ids)
