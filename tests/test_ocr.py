# -*- coding: utf-8 -*-
"""Qualité de l'OCR — mesure, seuils, provenance, chaîne d'outils.

Ces tests portent sur deux choses différentes, et il ne faut pas les confondre :

  * la POLITIQUE (`core/ocr.py`) : métriques, seuils, verdicts — testable sans
    réseau, sans PDF et sans macOS ;
  * l'ÉTAT RÉEL du corpus livré : quels articles viennent d'un calque texte et
    lesquels d'une reconnaissance automatique, avec quelle confiance.

Un test qui ne peut pas échouer ne vérifie rien : la régression `autojunk` est
donc explicitement reproduite ici.
"""

import difflib
import hashlib
import os
import random
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import analyse as A  # noqa: E402
from core import base, corpus, ocr  # noqa: E402

DOMAINE = "logement_baux_foncier"


def ref_par(numero_texte, etat="VERIFIE"):
    for ref in base.lister_references(domaine=DOMAINE):
        if ref["numero_texte"] == numero_texte and ref["etat_verification"] == etat:
            return ref
    return None


class TestMetriqueSimilarite(unittest.TestCase):
    def test_autojunk_fausse_la_mesure_sur_un_texte_long(self):
        """Régression documentée : `autojunk=True` détruit la mesure au-delà de 200 éléments.

        Témoin réel et reproductible (graine fixe) : deux textes de 900 mots pris
        dans un vocabulaire de 10 termes donnent 0,00 avec `autojunk=True` contre
        0,26 avec `autojunk=False`. Le même écart a été mesuré sur le corpus
        réel (0,0647 contre 0,9646 pour le même article) : c'est ce qui a fait
        rejeter la méthode par défaut avant toute conclusion de qualité.
        """
        random.seed(7)
        vocabulaire = ["bail", "loyer", "locataire", "bailleur", "immeuble",
                       "caution", "reprise", "conge", "travaux", "expertise"]
        gauche = " ".join(random.choice(vocabulaire) for _ in range(900))
        droite = " ".join(random.choice(vocabulaire) for _ in range(900))
        brute = difflib.SequenceMatcher(None, gauche, droite).ratio()
        juste = ocr.similarite(gauche, droite)
        self.assertLess(brute, 0.05, "le témoin autojunk=True doit s'effondrer")
        self.assertGreater(juste, brute + 0.2, "la mesure corrigée doit rester exploitable")
        self.assertEqual(
            juste, difflib.SequenceMatcher(None, gauche, droite, autojunk=False).ratio(),
            "`similarite()` doit désactiver autojunk")

    def test_textes_identiques(self):
        self.assertEqual(ocr.similarite("Article 416 disposition", "Article 416 disposition"), 1.0)

    def test_texte_vide(self):
        self.assertEqual(ocr.similarite("", "quelque chose"), 0.0)
        self.assertEqual(ocr.recouvrement_mots("", "x"), 0.0)

    def test_recouvrement_de_mots_independant_de_l_ordre(self):
        self.assertAlmostEqual(
            ocr.recouvrement_mots("loyer caution bailleur", "bailleur loyer caution"), 1.0)

    def test_seuils_de_verdict(self):
        self.assertEqual(ocr.verdict_de(0.95), ocr.VERDICT_RECOUPE)
        self.assertEqual(ocr.verdict_de(0.85), ocr.VERDICT_A_SURVEILLER)
        self.assertEqual(ocr.verdict_de(0.50), ocr.VERDICT_ECARTE)
        self.assertEqual(ocr.verdict_de(ocr.QUALITE_RECOUPEE), ocr.VERDICT_RECOUPE)
        self.assertEqual(ocr.verdict_de(ocr.QUALITE_MINIMALE), ocr.VERDICT_A_SURVEILLER)


class TestEvaluation(unittest.TestCase):
    def test_sans_reference_la_qualite_n_est_pas_mesurable(self):
        rapport = ocr.evaluer_articles_ocr({"1": "un texte"}, None)
        self.assertFalse(rapport["avec_reference"])
        self.assertIsNone(rapport["statistiques"])
        self.assertIn("ne peut pas être mesurée", rapport["raison"])

    def test_sans_articles_ocr(self):
        rapport = ocr.evaluer_articles_ocr({}, {"1": "un texte"})
        self.assertEqual(rapport["nb_articles_ocr"], 0)
        self.assertIn("aucun article détecté", rapport["raison"])

    def test_appariement_ecartes_et_absents(self):
        reference = {"1": "le loyer est payable chaque mois", "2": "la caution ne peut exceder deux mois",
                     "3": "le conge est de trois mois"}
        ocr_textes = {"1": "le loyer est payable chaque mois",
                      "2": "texte completement different sans rapport aucun",
                      "4": "article qui n'existe pas dans la reference"}
        rapport = ocr.evaluer_articles_ocr(ocr_textes, reference)
        self.assertEqual(sorted(rapport["apparies"]), ["1"])
        self.assertEqual(rapport["apparies"]["1"]["similarite"], 1.0)
        self.assertEqual(rapport["apparies"]["1"]["verdict"], ocr.VERDICT_RECOUPE)
        self.assertEqual([e["numero"] for e in rapport["ecartes"]], ["2"])
        self.assertEqual(rapport["absents_de_l_ocr"], ["3"])
        # La moyenne porte sur TOUTES les paires comparées, écartées comprises :
        # c'est la qualité de l'OCR qui est mesurée, pas celle des seuls succès.
        self.assertAlmostEqual(rapport["statistiques"]["similarite_moyenne"],
                               (1.0 + rapport["ecartes"][0]["similarite"]) / 2.0, places=4)
        self.assertEqual(rapport["statistiques"]["part_ge_seuil"], 0.5)
        self.assertEqual(rapport["statistiques"]["part_recoupee"], 0.5)

    def test_statistiques_presentes(self):
        reference = {"1": "a" * 300 + " caution ", "2": "b" * 300 + " loyer "}
        rapport = ocr.evaluer_articles_ocr(dict(reference), reference)
        stats = rapport["statistiques"]
        for cle in ("similarite_moyenne", "similarite_mediane", "similarite_minimale",
                    "part_recoupee", "part_ge_seuil", "taux_couverture"):
            self.assertIn(cle, stats)
        self.assertEqual(stats["part_recoupee"], 1.0)


class TestDecision(unittest.TestCase):
    def test_refus_quand_rien_ne_passe_le_seuil(self):
        evaluation = {"avec_reference": True, "apparies": {}, "ecartes": [{"numero": "1"}],
                      "statistiques": {"part_ge_seuil": 0.0}}
        verdict = ocr.decision(evaluation)
        self.assertEqual(verdict["decision"], ocr.DECISION_REFUS)
        self.assertEqual(verdict["articles_integrables"], 0)

    def test_integration_recoupee_au_dessus_de_90_pour_cent(self):
        evaluation = {"avec_reference": True, "apparies": {"1": {}, "2": {}}, "ecartes": [],
                      "statistiques": {"part_ge_seuil": 0.95}}
        self.assertEqual(ocr.decision(evaluation)["decision"], ocr.DECISION_OCR_RECOUPE)

    def test_integration_a_confirmer_entre_les_deux_seuils(self):
        evaluation = {"avec_reference": True, "apparies": {"1": {}}, "ecartes": [{"numero": "2"}],
                      "statistiques": {"part_ge_seuil": 0.82}}
        verdict = ocr.decision(evaluation)
        self.assertEqual(verdict["decision"], ocr.DECISION_OCR_A_CONFIRMER)
        self.assertIn("partielle", " ".join(verdict["raisons"]))

    def test_sans_reference_le_controle_structurel_decide(self):
        evaluation = {"avec_reference": False, "nb_articles_ocr": 4, "ecartes": []}
        bon = ocr.decision(evaluation, {"ok": True, "echecs": []})
        mauvais = ocr.decision(evaluation, {"ok": False, "echecs": ["trop peu de lignes"]})
        self.assertEqual(bon["decision"], ocr.DECISION_OCR_A_CONFIRMER)
        self.assertEqual(mauvais["decision"], ocr.DECISION_REFUS)
        self.assertIn("trop peu de lignes", " ".join(mauvais["raisons"]))

    def test_decision_sans_controle_structurel_execute(self):
        evaluation = {"avec_reference": False, "nb_articles_ocr": 4}
        verdict = ocr.decision(evaluation, None)
        self.assertEqual(verdict["decision"], ocr.DECISION_REFUS)
        self.assertIn("non exécuté", " ".join(verdict["raisons"]))


class TestControleStructurel(unittest.TestCase):
    def test_texte_trop_court_refuse(self):
        resultat = ocr.controler_structure("Article 1. Court.", ("Article",))
        self.assertFalse(resultat["ok"])
        self.assertTrue(any("trop peu de lignes" in e for e in resultat["echecs"]))

    def test_chaine_attendue_absente_refusee(self):
        texte = "\n".join("Article %d. Une disposition lisible." % i for i in range(1, 40))
        resultat = ocr.controler_structure(texte, ("98-750", "domaine foncier rural"))
        self.assertFalse(resultat["ok"])
        self.assertIn("chaines_attendues_manquantes", resultat["criteres"])
        self.assertEqual(len(resultat["criteres"]["chaines_attendues_manquantes"]), 2)

    def test_texte_avec_bruit_de_symboles_refuse(self):
        texte = "\n".join("••• /// --- %d" % i for i in range(40))
        resultat = ocr.controler_structure(texte, (), minimum_articles=1)
        self.assertFalse(resultat["ok"])
        self.assertTrue(any("alphabétiques" in e for e in resultat["echecs"]))

    def test_texte_valide_accepte(self):
        texte = "\n".join("Article %d. Le present article dispose d une regle lisible." % i
                          for i in range(1, 40))
        resultat = ocr.controler_structure(texte, ("Article",), minimum_articles=1)
        self.assertTrue(resultat["ok"], resultat["echecs"])
        self.assertEqual(resultat["criteres"]["nb_articles_detectes"], 39)

    def test_un_plancher_n_est_pas_une_mesure_de_qualite(self):
        """Loi de ratification : deux articles sont un compte légitime."""
        texte = ("Article 1 : Est ratifiee l'ordonnance portant suspension des procedures.\n"
                 "Article 2 : La presente loi sera publiee au Journal officiel.\n"
                 + "\n".join("Considerant que la situation l exige, le present texte prevoit." for _ in range(20)))
        resultat = ocr.controler_structure(texte, ("ratifiee",), minimum_articles=1)
        self.assertTrue(resultat["ok"], resultat["echecs"])
        self.assertEqual(resultat["criteres"]["nb_articles_detectes"], 2)


class TestChaineDOutils(unittest.TestCase):
    def test_detection_reelle_de_la_chaine(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ocr_collecter",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "bin", "ocr_collecter.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        etat = module.verifier_swift()
        self.assertIn("disponible", etat)
        if not etat["disponible"]:
            self.skipTest("chaîne OCR absente sur cette machine : %s" % etat)
        for cle in ("swiftc", "vision_framework", "pdfkit_framework", "appkit_framework"):
            self.assertTrue(etat[cle], "%s indisponible" % cle)
        self.assertIn("Swift", etat["swiftc_version"])

    def test_le_binaire_ocr_est_compile_si_la_chaine_existe(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ocr_collecter2",
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "bin", "ocr_collecter.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not module.verifier_swift()["disponible"]:
            self.skipTest("chaîne OCR absente")
        self.assertTrue(os.path.isfile(module.BINAIRE_OCR),
                        "binaire OCR absent : lancer bin/ocr_collecter.py")
        self.assertTrue(os.path.isfile(module.SOURCE_SWIFT))


class TestProvenanceDansLeCorpusLivre(unittest.TestCase):
    def _documents_a_ocr(self):
        return [d for d in corpus.lister_documents(domaine=DOMAINE)
                if d["methode_extraction"] == "OCR_VISION_AUTO"]

    def test_au_moins_un_document_ocr(self):
        self.assertTrue(self._documents_a_ocr(), "aucun document OCR : test sans portée")

    def test_le_texte_ocr_est_conserve_avec_son_empreinte(self):
        for document in self._documents_a_ocr():
            chemin = document["fichier_ocr"]
            self.assertTrue(chemin and os.path.isfile(chemin),
                            "%s : fichier OCR absent" % document["doc_id"])
            reel = "sha256:" + hashlib.sha256(open(chemin, "rb").read()).hexdigest()
            self.assertEqual(reel, document["sha256_ocr"],
                             "%s : empreinte du texte OCR incohérente" % document["doc_id"])

    def test_le_pdf_original_est_intact_apres_ocr(self):
        """L'OCR ne doit jamais toucher au PDF source."""
        for document in self._documents_a_ocr():
            reel = "sha256:" + hashlib.sha256(open(document["chemin_local"], "rb").read()).hexdigest()
            self.assertEqual(reel, document["sha256"])

    def test_un_document_ocr_reste_un_scan(self):
        for document in self._documents_a_ocr():
            self.assertEqual(document["calque_texte"], 0,
                             "%s : l'OCR ne transforme pas un scan en document à calque texte"
                             % document["doc_id"])

    def test_la_confiance_ocr_est_enregistree_quand_elle_est_mesurable(self):
        for document in self._documents_a_ocr():
            if not document["recoupe_avec"]:
                continue
            self.assertIsNotNone(document["qualite_ocr"])
            self.assertGreaterEqual(document["qualite_ocr"], ocr.QUALITE_MINIMALE)

    def test_compte_par_origine_coherent(self):
        compte = corpus.articles_par_origine()
        with corpus.connexion() as conn:
            total = conn.execute("SELECT COUNT(*) FROM articles_corpus").fetchone()[0]
        self.assertEqual(sum(c["articles"] for c in compte.values()), total)
        self.assertGreater(compte["OCR_AUTO"]["articles"], 0)
        self.assertEqual(compte["VERIFIE_MANUELLEMENT"]["articles"], 0,
                         "aucun texte n'a été relu manuellement : la catégorie doit rester vide")

    def test_citation_sur_article_ocr_porte_la_provenance(self):
        document = [d for d in self._documents_a_ocr() if not d["recoupe_avec"]][0]
        article = corpus.articles_dun_document(document["doc_id"])[0]
        citation = corpus.obtenir_article_par_reference(document["ref_id"], article["numero"])["texte"]
        ok, details = corpus.verifier_citation_article(
            document["ref_id"], article["numero"], citation[:80])
        self.assertTrue(ok, details)
        self.assertEqual(details["origine_texte"], "OCR_AUTO")
        self.assertFalse(details["recoupe"])
        self.assertIn("reconnaissance automatique", details.get("avertissement", ""))

    def test_citation_sur_article_a_calque_ne_porte_pas_d_avertissement(self):
        reference = ref_par("2019-576")
        article = corpus.obtenir_article_par_reference(reference["ref_id"], "423")
        ok, details = corpus.verifier_citation_article(
            reference["ref_id"], "423", article["texte"][:60])
        self.assertTrue(ok, details)
        self.assertEqual(details["origine_texte"], "CALQUE_TEXTE")
        self.assertNotIn("avertissement", details)


class TestControleDeProvenanceDansLAnalyse(unittest.TestCase):
    def test_regle_sur_ocr_non_recoupe_sans_incertitude_refusee(self):
        reference = ref_par("98-750", etat="PARTIELLEMENT_VERIFIE")
        analyse = A.nouvelle_analyse("TEST_OCR", [DOMAINE])
        A.ajouter_regle(analyse, reference["ref_id"],
                        "Le domaine foncier rural est constitue des terres mises en valeur.",
                        articles="Article 1")
        violations = corpus.verifier_provenance_analyse(analyse)
        self.assertEqual([v["code"] for v in violations], ["PROVENANCE_OCR_NON_DECLAREE"])

    def test_incertitude_declaree_leve_la_violation_de_provenance(self):
        reference = ref_par("98-750", etat="PARTIELLEMENT_VERIFIE")
        analyse = A.nouvelle_analyse("TEST_OCR", [DOMAINE])
        A.ajouter_regle(analyse, reference["ref_id"],
                        "Le domaine foncier rural est constitue des terres mises en valeur.",
                        articles="Article 1")
        A.declarer_incertitude(analyse, reference["ref_id"],
                               "Texte obtenu par OCR, non recoupé avec une autre copie.")
        self.assertEqual(corpus.verifier_provenance_analyse(analyse), [])

    def test_regle_sur_article_a_calque_aucune_violation(self):
        reference = ref_par("2019-576")
        analyse = A.nouvelle_analyse("TEST_OCR", [DOMAINE])
        A.ajouter_regle(analyse, reference["ref_id"], "Le loyer est revise tous les trois ans.",
                        articles="Article 423")
        self.assertEqual(corpus.verifier_provenance_analyse(analyse), [])

    def test_l_orchestrateur_refuse_l_analyse_non_declaree(self):
        """Le contrôle est bien INVoqué par l'orchestrateur, pas seulement écrit."""
        from agent import MonRecoursCI
        dossier_id = "TEST_OCR_PROVENANCE"
        reference = ref_par("98-750", etat="PARTIELLEMENT_VERIFIE")
        try:
            agent = MonRecoursCI()
            agent.ouvrir_dossier(dossier_id, "Un conflit de terrain au village.")
            analyse = A.nouvelle_analyse(dossier_id, [DOMAINE])
            A.ajouter_regle(analyse, reference["ref_id"],
                            "Le domaine foncier rural est constitue des terres mises en valeur.",
                            articles="Article 1")
            A.ajouter_application(analyse, "Application aux faits declares.",
                                  ref_ids=[reference["ref_id"]], faits_ids=["F01"])
            cloture = agent.clore_dossier(dossier_id, analyse)
            codes = [v["code"] for v in cloture["controles_qualite"]["violations"]]
            self.assertIn("PROVENANCE_OCR_NON_DECLAREE", codes)
            self.assertEqual(cloture["statut_reponse"], "ANALYSE_REFUSEE")
        finally:
            shutil.rmtree(str(__import__("config").dossier_utilisateur(dossier_id)),
                          ignore_errors=True)


class TestValidationDeLOrigine(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="mrc_ocr_")
        self.chemin_db = os.path.join(self.dossier, "base.sqlite3")
        corpus.initialiser(self.chemin_db)
        base.initialiser(self.chemin_db)
        self.ref_id = base.ajouter_reference(
            titre_officiel="Référence de test", type_texte="loi", source_nom="Test",
            source_url="https://www.cndj.ci/", date_consultation="2026-10-16",
            chemin=self.chemin_db)
        # Un article appartient OBLIGATOIREMENT à un document (clé étrangère) :
        # le test doit donc créer un document réel, pas un identifiant inventé.
        self.chemin_pdf = os.path.join(self.dossier, "document.pdf")
        with open(self.chemin_pdf, "wb") as flux:
            flux.write(b"%PDF-1.4 document de test\n")
        self.chemin_texte = os.path.join(self.dossier, "document.txt")
        with open(self.chemin_texte, "w", encoding="utf-8") as flux:
            flux.write("Article 1 : texte de test.\n")
        self.doc_id = corpus.importer_document(
            ref_id=self.ref_id, titre="Texte de test", type_texte="loi",
            numero_texte="TEST-1", date_texte="2020-01-01", domaine="test",
            autorite="Test", url_source="https://www.cndj.ci/",
            chemin_local=self.chemin_pdf, licence_conditions="Test",
            pages=1, calque_texte=1, fichier_texte=self.chemin_texte,
            note_qualite="test", chemin=self.chemin_db)

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def test_origine_inconnue_refusee(self):
        with self.assertRaises(ValueError) as ctx:
            corpus.enregistrer_articles(self.ref_id, self.doc_id, {"1": "texte"},
                                        origine_texte="FAIT_MAISON", chemin=self.chemin_db)
        self.assertIn("origine de texte inconnue", str(ctx.exception))

    def test_un_article_ne_peut_pas_exister_sans_document(self):
        """La clé étrangère qui rend le test précédent nécessaire est bien active."""
        import sqlite3
        with self.assertRaises(sqlite3.IntegrityError):
            corpus.enregistrer_articles(self.ref_id, "DOCUMENT-INEXISTANT", {"1": "texte"},
                                        chemin=self.chemin_db)

    def test_origine_verifiee_manuellement_acceptee(self):
        corpus.enregistrer_articles(self.ref_id, self.doc_id, {"1": "texte relu a la main"},
                                    origine_texte="VERIFIE_MANUELLEMENT", chemin=self.chemin_db)
        compte = corpus.articles_par_origine(chemin=self.chemin_db)
        self.assertEqual(compte["VERIFIE_MANUELLEMENT"]["articles"], 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
