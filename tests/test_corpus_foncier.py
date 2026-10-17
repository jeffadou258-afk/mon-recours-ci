# -*- coding: utf-8 -*-
"""Corpus LOGEMENT, BAUX ET FONCIER — preuves, traçabilité, refus d'invention.

Ces tests ne vérifient pas des règles de droit : ils vérifient que CHAQUE
affirmation juridique que l'agent pourrait produire depuis ce corpus peut être
reliée à un document officiel réel, empreinté, et à un article réellement
indexé.

Ils portent sur le corpus LIVRÉ (la base du projet), pas sur un jeu de test :
c'est précisément son intégrité qu'il faut prouver.
"""

import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from config import CHEMIN_DB  # noqa: E402
from core import analyse as A  # noqa: E402
from core import base, corpus  # noqa: E402
from core.sources import est_hote_officiel  # noqa: E402

DOMAINE = "logement_baux_foncier"


def ref_id_de(numero_texte, etat="VERIFIE"):
    for ref in base.lister_references(domaine=DOMAINE):
        if ref["numero_texte"] == numero_texte and ref["etat_verification"] == etat:
            return ref["ref_id"]
    return None


class TestIntegriteDuCorpus(unittest.TestCase):
    def test_les_empreintes_sont_conformes(self):
        resultat = corpus.verifier_integrite()
        self.assertEqual(resultat["alteres"], [], "documents altérés : %s" % resultat["alteres"])
        self.assertEqual(resultat["absents"], [], "documents absents : %s" % resultat["absents"])
        self.assertEqual(resultat["verdict"], "INTEGRE")
        self.assertGreaterEqual(len(resultat["conformes"]), 4)

    def test_chaque_document_porte_une_empreinte_valide(self):
        for document in corpus.lister_documents(domaine=DOMAINE):
            self.assertRegex(document["sha256"], r"^sha256:[0-9a-f]{64}$")
            self.assertGreater(document["octets"], 1000)
            self.assertGreater(document["pages"], 0)

    def test_chaque_document_vient_d_un_hote_officiel(self):
        for document in corpus.lister_documents(domaine=DOMAINE):
            self.assertTrue(est_hote_officiel(document["url_source"]),
                            "source non officielle : %s" % document["url_source"])
            self.assertEqual(document["hote_officiel"], 1)

    def test_chaque_document_porte_ses_conditions_d_acces(self):
        for document in corpus.lister_documents(domaine=DOMAINE):
            self.assertGreater(len(document["licence_conditions"].strip()), 40)
            self.assertTrue(document["date_collecte"])

    def test_l_empreinte_stockee_est_recalculable(self):
        for document in corpus.lister_documents(domaine=DOMAINE):
            h = hashlib.sha256()
            with open(document["chemin_local"], "rb") as f:
                for bloc in iter(lambda: f.read(1 << 20), b""):
                    h.update(bloc)
            self.assertEqual("sha256:" + h.hexdigest(), document["sha256"])


class TestTracabiliteDesArticles(unittest.TestCase):
    def test_chaque_article_pointe_vers_une_reference_reelle(self):
        connus = base.ref_ids_connus()
        with corpus.connexion() as conn:
            lignes = conn.execute("SELECT DISTINCT ref_id FROM articles_corpus").fetchall()
        self.assertTrue(lignes)
        for ligne in lignes:
            self.assertIn(ligne[0], connus, "article orphelin : %s" % ligne[0])

    def test_chaque_article_pointe_vers_un_document_reel(self):
        doc_ids = {d["doc_id"] for d in corpus.lister_documents()}
        with corpus.connexion() as conn:
            lignes = conn.execute("SELECT DISTINCT doc_id FROM articles_corpus").fetchall()
        for ligne in lignes:
            self.assertIn(ligne[0], doc_ids, "document inconnu : %s" % ligne[0])

    def test_l_empreinte_de_chaque_article_est_exacte(self):
        with corpus.connexion() as conn:
            lignes = conn.execute(
                "SELECT numero, texte, sha256_article FROM articles_corpus").fetchall()
        self.assertGreater(len(lignes), 800)
        for numero, texte, attendu in lignes:
            self.assertEqual(corpus.empreinte_texte(texte), attendu,
                             "empreinte incohérente pour l'article %s" % numero)

    def test_les_scans_ne_produisent_que_des_articles_ocr(self):
        """Un scan n'a AUCUN article issu d'un calque texte.

        Renforcé en phase 3 : depuis que l'OCR est branché, un scan peut porter
        des articles — mais uniquement marqués `OCR_AUTO`, avec leur provenance
        et, quand elle est mesurable, leur confiance. Aucun article d'un scan ne
        doit pouvoir se présenter comme une lecture de document.
        """
        scans = [d for d in corpus.lister_documents(domaine=DOMAINE) if not d["calque_texte"]]
        self.assertTrue(scans, "aucun scan dans le corpus : test sans portée")
        for document in scans:
            articles = corpus.articles_dun_document(document["doc_id"])
            for article in articles:
                self.assertEqual(article["origine_texte"], "OCR_AUTO",
                                 "%s art. %s porte l'origine %r"
                                 % (document["doc_id"], article["numero"], article["origine_texte"]))
                self.assertIn(document["methode_extraction"], ("OCR_VISION_AUTO", "AUCUNE"))

    def test_les_articles_de_calque_texte_viennent_de_documents_a_calque_texte(self):
        with corpus.connexion() as conn:
            lignes = conn.execute(
                "SELECT DISTINCT a.doc_id FROM articles_corpus a WHERE a.origine_texte = 'CALQUE_TEXTE'"
            ).fetchall()
        par_doc = {d["doc_id"]: d for d in corpus.lister_documents()}
        self.assertTrue(lignes)
        for ligne in lignes:
            document = par_doc[ligne[0]]
            self.assertEqual(document["calque_texte"], 1,
                             "%s porte des articles CALQUE_TEXTE sans calque texte" % ligne[0])
            self.assertEqual(document["methode_extraction"], "CALQUE_TEXTE")

    def test_les_articles_ocr_recoupes_portent_leur_confiance(self):
        recoupes = [d for d in corpus.lister_documents(domaine=DOMAINE)
                    if d["methode_extraction"] == "OCR_VISION_AUTO" and d["recoupe_avec"]]
        self.assertTrue(recoupes, "aucun document OCR recoupé : test sans portée")
        for document in recoupes:
            articles = corpus.articles_dun_document(document["doc_id"])
            self.assertTrue(articles)
            for article in articles:
                self.assertEqual(article["recoupe"], 1)
                self.assertIsNotNone(article["confiance_ocr"],
                                     "%s art. %s : confiance manquante" % (document["doc_id"],
                                                                           article["numero"]))
                self.assertGreaterEqual(article["confiance_ocr"], 0.80)

    def test_aucun_article_ocr_non_recoupe_ne_se_dit_recoupe(self):
        for document in corpus.lister_documents(domaine=DOMAINE):
            if document["recoupe_avec"]:
                continue
            for article in corpus.articles_dun_document(document["doc_id"]):
                if article["origine_texte"] == "OCR_AUTO":
                    self.assertEqual(article["recoupe"], 0)

    def test_la_reference_d_un_scan_n_a_pas_de_texte_complet(self):
        """Sans texte lu, aucune citation ne peut s'appuyer sur la référence."""
        for document in corpus.lister_documents(domaine=DOMAINE):
            if document["calque_texte"]:
                continue
            ref = base.obtenir_reference(document["ref_id"])
            self.assertEqual(ref["texte_complet_present"], 0)
            ok, raison = base.verifier_citation(ref["ref_id"], "une citation quelconque")
            self.assertFalse(ok)
            self.assertIn("texte intégral non présent", raison)

    def test_les_documents_exploitables_ont_leurs_articles(self):
        """Tout texte de loi à calque texte doit être indexé.

        Le seuil n'est pas un nombre unique : une loi de ratification compte
        quelques articles, un code en compte des centaines. Les documents non
        juridiques (communiqués) sont exclus — ils n'ont pas de référence et ne
        portent aucun article par construction.
        """
        textes = [d for d in corpus.lister_documents(domaine=DOMAINE)
                  if d["calque_texte"] and d["ref_id"]]
        self.assertTrue(textes, "aucun texte juridique à calque texte")
        for document in textes:
            articles = corpus.articles_dun_document(document["doc_id"])
            self.assertTrue(articles, "%s (%s) n'a aucun article indexé"
                            % (document["doc_id"], document["numero_texte"]))
        plus_gros = max(len(corpus.articles_dun_document(d["doc_id"])) for d in textes)
        self.assertGreater(plus_gros, 250,
                           "aucun texte volumineux indexé : le corpus est suspect")

    def test_couverture_de_numerotation_sans_trou_inexplique(self):
        """Loi 2020-624 : l'article 151 n'existe pas dans le PDF officiel.

        Constat vérifié : la chaîne « 151 » n'apparaît nulle part dans le texte
        extrait, qui passe de l'article 150 à l'article 152. La lacune est dans
        le document source, pas dans le parseur — et elle est donc documentée.
        """
        doc = [d for d in corpus.lister_documents(domaine=DOMAINE)
               if d["numero_texte"] == "2020-624" and d["calque_texte"]][0]
        texte = open(doc["fichier_texte"], encoding="utf-8").read()
        self.assertNotIn("151", re.sub(r"\s+", "", texte),
                         "l'article 151 est finalement présent : mettre à jour ce constat")
        articles = corpus.extraire_articles(texte)
        taux, maximum = corpus.taux_couverture(articles)
        self.assertEqual(maximum, 303)
        self.assertAlmostEqual(taux, 302 / 303.0, places=4)


class TestCitationSoutenueParLeTexteReel(unittest.TestCase):
    def setUp(self):
        self.ref = ref_id_de("2019-576")
        self.assertIsNotNone(self.ref, "la référence VERIFIE du Code de la Construction est absente")

    def test_citation_reelle_acceptee(self):
        ok, raison = base.verifier_citation(
            self.ref, "Le loyer peut être révisé à la hausse ou à la baisse, tous les trois ans.")
        self.assertTrue(ok, raison)

    def test_citation_inventee_refusee(self):
        ok, raison = base.verifier_citation(
            self.ref, "le locataire a droit à une indemnité de cinq ans de loyer")
        self.assertFalse(ok)
        self.assertIn("ABSENTE", raison)

    def test_articles_reels_presents(self):
        for numero in ("415", "416", "423", "440", "445", "552"):
            article = corpus.obtenir_article_par_reference(self.ref, numero)
            self.assertIsNotNone(article, "article %s absent du corpus" % numero)
            self.assertGreater(len(article["texte"]), 100)

    def test_abrogation_de_2018_575_presente_dans_l_article_552(self):
        """Les numéros subissent des espaces parasites à l'extraction, d'où la normalisation."""
        article = corpus.obtenir_article_par_reference(self.ref, "552")
        texte_normalise = base.normaliser(article["texte"])
        self.assertIn("2018-575", texte_normalise)
        self.assertIn("99-478", texte_normalise)
        self.assertIn("bail a usage d'habitation", texte_normalise)

    def test_une_citation_numerique_est_retrouvee_malgre_les_espaces_parasites(self):
        """Régression : « loi n° 99-478 » doit matcher « loi n° 99 -478 » du PDF."""
        ok, raison = base.verifier_citation(
            self.ref, "la loi 99-478 du 2 août 1999 portant organisation de la vente d'immeuble")
        self.assertTrue(ok, raison)


class TestRegleSoutenueParUnArticle(unittest.TestCase):
    def setUp(self):
        self.ref = ref_id_de("2019-576")

    def test_regle_inventee_refusee_par_le_controle_article(self):
        resultat = corpus.verifier_regle_article(
            self.ref, "423", "Le montant est plafonné à 95000 FCFA par trimestre.")
        self.assertFalse(resultat["ok"])
        self.assertIn("95000", resultat["nombres_non_soutenus"])

    def test_regle_soutenue_acceptee(self):
        resultat = corpus.verifier_regle_article(
            self.ref, "423",
            "Le loyer peut être révisé à la hausse ou à la baisse, tous les trois ans.")
        self.assertTrue(resultat["ok"], resultat)

    def test_article_inconnu_signale(self):
        resultat = corpus.verifier_regle_article(self.ref, "9999", "Un énoncé quelconque.")
        self.assertFalse(resultat["ok"])
        self.assertEqual(resultat["raison"], "ARTICLE_INCONNU")


class TestAnalyseAvecCorpusReel(unittest.TestCase):
    """Le test central : une analyse documentée sur le corpus réel doit aboutir."""

    def setUp(self):
        self.ref = ref_id_de("2019-576")
        self.agent_analyse = A.nouvelle_analyse("TEST_CORPUS", [DOMAINE])

    def test_analyse_documentee_peut_conclure(self):
        analyse = self.agent_analyse
        A.ajouter_regle(analyse, self.ref,
                        "Le dépôt de garantie ne peut excéder deux mois de loyer.")
        A.ajouter_regle(analyse, self.ref,
                        "L'expulsion forcée peut être demandée devant le juge des référés "
                        "lorsque le locataire manque à ses obligations.")
        A.ajouter_application(analyse, "Ces règles s'appliquent aux faits déclarés.",
                              ref_ids=[self.ref], faits_ids=["F01"])
        references = {self.ref: base.obtenir_reference(self.ref)}
        violations = A.valider(analyse, references=references)
        self.assertEqual(violations, [], "violations : %s" % violations)
        ok, raisons = A.peut_conclure(analyse, references=references)
        self.assertTrue(ok, raisons)

    def test_analyse_sans_reference_ne_conclut_pas(self):
        analyse = A.nouvelle_analyse("TEST_CORPUS", [DOMAINE])
        ok, raisons = A.peut_conclure(analyse)
        self.assertFalse(ok)
        self.assertTrue(any("AUCUNE_REFERENCE_VERIFIEE" in r for r in raisons))

    def test_regle_fondee_sur_une_reference_non_verifiee_exige_une_incertitude(self):
        non_verifiee = ref_id_de("98-750", etat="PARTIELLEMENT_VERIFIE")
        self.assertIsNotNone(non_verifiee)
        analyse = A.nouvelle_analyse("TEST_CORPUS", [DOMAINE])
        A.ajouter_regle(analyse, non_verifiee, "Une règle tirée d'un texte non vérifié.")
        violations = A.valider(analyse, references={non_verifiee: base.obtenir_reference(non_verifiee)})
        self.assertIn("INCERTITUDE_NON_DECLAREE", [v["code"] for v in violations])

    def test_recherche_dans_le_corpus_remonte_des_articles_reels(self):
        resultats = corpus.chercher_articles("expulsion locataire loyer", domaine=DOMAINE, limite=10)
        self.assertTrue(resultats)
        for resultat in resultats:
            self.assertTrue(resultat["sha256"].startswith("sha256:"))
            self.assertTrue(resultat["url_source"].startswith("https://"))
            self.assertIn(resultat["etat_verification"], ("VERIFIE", "PARTIELLEMENT_VERIFIE"))

    def test_le_nombre_de_references_verifiees_est_exact(self):
        verifiees = base.lister_references(etat="VERIFIE", domaine=DOMAINE)
        self.assertEqual(len(verifiees), 2,
                         "attendu 2 références VERIFIE, obtenu %d" % len(verifiees))


class TestImportRefuse(unittest.TestCase):
    """Les portes d'entrée du corpus doivent refuser ce qui n'est pas prouvé."""

    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="mrc_corpus_")
        self.chemin_db = os.path.join(self.dossier, "base.sqlite3")
        self.fichier = os.path.join(self.dossier, "faux.pdf")
        with open(self.fichier, "wb") as f:
            f.write(b"%PDF-1.4 contenu de test")
        corpus.initialiser(self.chemin_db)
        base.initialiser(self.chemin_db)
        self.ref_id = base.ajouter_reference(
            titre_officiel="Référence de test (aucune valeur juridique)", type_texte="loi",
            source_nom="Test", source_url="https://www.cndj.ci/",
            date_consultation="2026-10-16", chemin=self.chemin_db)

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def _importer(self, **surcharges):
        parametres = dict(
            ref_id=self.ref_id, titre="Document de test", type_texte="loi",
            numero_texte="TEST-0000", date_texte="2020-01-01", domaine=DOMAINE,
            autorite="Test", url_source="https://www.cndj.ci/",
            chemin_local=self.fichier, licence_conditions="Conditions de test explicites.",
            pages=10, calque_texte=False, chemin=self.chemin_db)
        parametres.update(surcharges)
        return corpus.importer_document(**parametres)

    def test_hote_non_officiel_refuse(self):
        with self.assertRaises(ValueError) as ctx:
            self._importer(url_source="https://un-blog.example/loi.pdf")
        self.assertIn("non officielle", str(ctx.exception))

    def test_empreinte_incoherente_refusee(self):
        with self.assertRaises(ValueError) as ctx:
            self._importer(sha256_declare="sha256:" + "0" * 64)
        self.assertIn("incohérente", str(ctx.exception))

    def test_conditions_d_acces_obligatoires(self):
        with self.assertRaises(ValueError) as ctx:
            self._importer(licence_conditions="   ")
        self.assertIn("licence_conditions", str(ctx.exception))

    def test_fichier_absent_refuse(self):
        with self.assertRaises(FileNotFoundError):
            self._importer(chemin_local=os.path.join(self.dossier, "absent.pdf"))

    def test_pages_obligatoires(self):
        with self.assertRaises(ValueError):
            self._importer(pages=0)

    def test_calque_texte_exige_le_fichier_extrait(self):
        with self.assertRaises(ValueError):
            self._importer(calque_texte=True, fichier_texte=None)

    def test_couverture_insuffisante_refusee(self):
        # Trou volontaire : 1 et 3 présents, 2 manquant => couverture 2/3 < 85 %.
        articles = {"1": "a" * 50, "3": "c" * 50}
        with self.assertRaises(ValueError) as ctx:
            corpus.enregistrer_articles(self.ref_id, "DOC-INEXISTANT", articles,
                                        chemin=self.chemin_db)
        self.assertIn("couverture insuffisante", str(ctx.exception))


class TestChaineDePreuveJusquALArticle(unittest.TestCase):
    """Le dossier de traçabilité doit descendre jusqu'à l'article, pas seulement au document."""

    def test_le_dossier_porte_l_empreinte_des_articles_cites(self):
        from agent import MonRecoursCI
        dossier_id = "TEST_CORPUS_PREUVE"
        ref_id = ref_id_de("2019-576")
        try:
            agent = MonRecoursCI()
            agent.ouvrir_dossier(dossier_id, "Mon bailleur exige trois mois d'avance "
                                             "et menace de m'expulser.")
            analyse = A.nouvelle_analyse(dossier_id, [DOMAINE])
            A.ajouter_regle(analyse, ref_id,
                            "Le dépôt de garantie ne peut excéder deux mois de loyer.",
                            articles="Article 416")
            A.ajouter_application(analyse, "Application aux faits déclarés.",
                                  ref_ids=[ref_id], faits_ids=["F01"])
            cloture = agent.clore_dossier(dossier_id, analyse)
            trace = json.load(open(cloture["traceabilite"], encoding="utf-8"))
            entrees = trace["articles_effectivement_verifies"]
            self.assertEqual(len(entrees), 1)
            entree = entrees[0]
            self.assertEqual(entree["article"], "416")
            self.assertTrue(entree["indexe_dans_le_corpus"])
            self.assertRegex(entree["sha256_article"], r"^sha256:[0-9a-f]{64}$")
            article = corpus.obtenir_article_par_reference(ref_id, "416")
            self.assertEqual(entree["sha256_article"], article["sha256_article"])
            self.assertEqual(trace["statut_reponse"], "ANALYSE_CONFORME")
        finally:
            shutil.rmtree(str(config.dossier_utilisateur(dossier_id)), ignore_errors=True)


class TestExtractionDArticles(unittest.TestCase):
    def test_parseur_deterministe(self):
        texte = "Article 1. Premier.\nArticle 2. Deuxième.\nTITRE II\nArticle 3. Troisième.\n"
        articles = corpus.extraire_articles(texte)
        self.assertEqual(sorted(articles), ["1", "2", "3"])
        # Le corps d'un article court jusqu'au titre d'article suivant : les
        # intertitres (« TITRE II ») restent donc dans le chunk. C'est attendu :
        # le chunk est un bloc de texte, pas un article découpé au sens strict.
        self.assertTrue(articles["2"].startswith("Deuxième."))
        self.assertIn("TITRE II", articles["2"])

    def test_le_plus_long_chunk_gagne(self):
        texte = "Article 5. Court.\nArticle 5. Version beaucoup plus longue et complète.\n"
        self.assertIn("beaucoup plus longue", corpus.extraire_articles(texte)["5"])

    def test_numero_de_page_colle_au_titre(self):
        self.assertIn("1", corpus.extraire_articles("72Article 1.     Contenu réel.\n"))

    def test_article_bis_reconnu(self):
        articles = corpus.extraire_articles("Article 8 bis. Disposition ajoutée.\n")
        self.assertIn("8 bis", articles)

    def test_taux_de_couverture(self):
        articles = {"1": "x", "2": "x", "3": "x"}
        taux, maximum = corpus.taux_couverture(articles)
        self.assertEqual(maximum, 3)
        self.assertAlmostEqual(taux, 1.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
