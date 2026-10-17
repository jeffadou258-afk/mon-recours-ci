# -*- coding: utf-8 -*-
"""Loi n° 2019-571 (filiation) indexée par segment d'un extrait du Journal officiel.

Ce que ces tests verrouillent :
  * l'extraction du fichier ENTIER reste refusée (trois textes mélangés) ;
  * seuls les articles 1 à 30 de la loi sur la filiation sont indexés, sans
    les articles 103-105 de la loi sur le mariage ni le décret qui suit ;
  * l'empreinte du calque est contrôlée, l'OCR est refusé par l'outil ;
  * l'état de vérification de la référence n'est pas promu ;
  * une citation inventée est rejetée, une citation exacte retrouvée.
"""

import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "bin"))

from core import base, corpus  # noqa: E402
import indexer_segment  # noqa: E402

FAMILLE = "famille_mariage_filiation"
DOC_FILIATION = "DOC-B722D1F51881"
DEBUT = "LOI n° 2019-571 du 26 juin 2019 relative à la filiation."
FIN = "DECRET n° 2019-590"


def textes_en_base():
    with corpus.connexion() as conn:
        return {l["numero"]: l["texte"] for l in conn.execute(
            "SELECT numero, texte FROM articles_corpus WHERE doc_id = ?", (DOC_FILIATION,))}


def reference_filiation():
    for r in base.lister_references(domaine=FAMILLE):
        if r.get("numero_texte") == "2019-571":
            return r
    return None


class TestSegmentFiliation(unittest.TestCase):

    def test_le_fichier_entier_reste_non_indexable(self):
        document = corpus.obtenir_document(DOC_FILIATION)
        with open(indexer_segment.chemin_local(document["fichier_texte"]), encoding="utf-8") as f:
            entier = corpus.extraire_articles(f.read())
        taux, _ = corpus.taux_couverture(entier)
        self.assertLess(taux, corpus.COUVERTURE_MINIMALE,
                        "le fichier mélange trois textes : son découpage doit rester refusé")

    def test_seuls_les_articles_1_a_30_sont_indexes(self):
        numeros = sorted(int(a["numero"]) for a in corpus.articles_dun_document(DOC_FILIATION))
        self.assertEqual(numeros, list(range(1, 31)))

    def test_aucun_texte_voisin_ne_contamine_les_articles(self):
        textes = " ".join(textes_en_base().values())
        for intrus in ("Cartes nationales d", "Le mariage se dissout", "JOURNAL OFFICIEL"):
            self.assertNotIn(intrus, textes)
        self.assertNotIn("­", textes, "les césures de fin de ligne doivent être recollées")

    def test_la_preparation_est_reproductible_et_conforme_a_la_base(self):
        preparation = indexer_segment.preparer(DOC_FILIATION, DEBUT, FIN)
        self.assertEqual(preparation["rapport"]["couverture"], 1.0)
        en_base = textes_en_base()
        self.assertEqual(en_base, preparation["articles"])

    def test_l_outil_refuse_un_document_ocr(self):
        ocr = [d for d in corpus.lister_documents(domaine=FAMILLE) if d["numero_texte"] == "2019-572"][0]
        with self.assertRaises(indexer_segment.RefusIndexation):
            indexer_segment.preparer(ocr["doc_id"], "Art. 1", "")

    def test_l_outil_refuse_un_marqueur_absent(self):
        with self.assertRaises(indexer_segment.RefusIndexation):
            indexer_segment.preparer(DOC_FILIATION, "LOI n° 9999-999", FIN)

    def test_la_reference_n_est_pas_promue_verifiee(self):
        self.assertNotEqual(reference_filiation()["etat_verification"], "VERIFIE")

    def test_citations(self):
        ref = reference_filiation()
        ok, details = corpus.verifier_citation_article(
            ref["ref_id"], "19", "A l’égard du père, la preuve de la filiation ne peut résulter "
                                 "que d’une reconnaissance ou d’un jugement.")
        self.assertTrue(ok, details)
        self.assertEqual(details["origine_texte"], "CALQUE_TEXTE")
        ok, details = corpus.verifier_citation_article(
            ref["ref_id"], "19", "Le père doit verser une pension alimentaire.")
        self.assertFalse(ok)


if __name__ == "__main__":
    unittest.main()


class TestNormalisationCesure(unittest.TestCase):

    def test_le_trait_d_union_conditionnel_ne_coupe_plus_le_mot(self):
        from core.base import normaliser
        self.assertEqual(normaliser("filia­\ntion"), "filiation")
        self.assertEqual(normaliser("présomp­\r\n  tions"), "presomptions")
        # Un vrai trait d'union reste intact.
        self.assertEqual(normaliser("quatre-vingt"), "quatre-vingt")


class TestFichesFamille(unittest.TestCase):
    """Les fiches famille sont servies, validées, et n'élargissent pas le périmètre."""

    @classmethod
    def setUpClass(cls):
        import shutil
        import uuid
        import config
        from core import service
        cls.service = service
        cls.shutil = shutil
        cls.config = config
        cls.uuid = uuid
        cls.crees = []

    @classmethod
    def tearDownClass(cls):
        for dossier in cls.crees:
            cls.shutil.rmtree(str(cls.config.dossier_utilisateur(dossier)), ignore_errors=True)

    def _parcours(self, demande):
        dossier = "TEST-FAMILLE-" + self.uuid.uuid4().hex[:10]
        self.crees.append(dossier)
        ouverture = self.service.ouvrir(dossier, demande)
        self.assertTrue(ouverture["ok"], ouverture)
        return dossier, ouverture["data"]

    def test_les_fiches_famille_sont_chargees_et_validees(self):
        from core import catalogue
        fiches = [f for f in catalogue.charger() if f["domaine"] == FAMILLE]
        self.assertEqual(len(fiches), 11)
        for fiche in fiches:
            self.assertEqual(fiche["numero_texte"], "2019-571")
            self.assertEqual(fiche["origine_texte"], "CALQUE_TEXTE")
            self.assertNotEqual(fiche["etat_verification"], "VERIFIE")

    def test_reconnaissance_d_un_enfant_reponse_conforme_avec_incertitude(self):
        dossier, data = self._parcours("Je veux reconnaître mon enfant né hors mariage.")
        self.assertEqual(data["etape"], "clarification")
        articles = {f["article"] for f in data["fiches_identifiees"]}
        self.assertTrue({"19", "20"} <= articles, articles)
        reponse = self.service.repondre(dossier, {})["data"]["reponse"]
        self.assertEqual(reponse["statut_reponse"], "ANALYSE_CONFORME")
        for source in reponse["sections"]["6_sources"]:
            self.assertEqual(source["etat_verification"], "PARTIELLEMENT_VERIFIE")
            self.assertTrue(source["url_source"].startswith("https://famille.gouv.ci/"))

    def test_pension_alimentaire_et_divorce_restent_sans_conclusion(self):
        for demande in ("Le père de mon enfant refuse de payer la pension alimentaire.",
                        "Mon mari veut divorcer, quels sont mes droits ?"):
            _, data = self._parcours(demande)
            self.assertEqual(data["etape"], "hors_catalogue", demande)
            self.assertEqual(data["reponse"]["statut_reponse"], "CONCLUSION_IMPOSSIBLE")

    def test_le_logement_n_est_pas_perturbe(self):
        dossier, data = self._parcours("Mon bailleur garde ma caution.")
        self.assertIn("416", {f["article"] for f in data["fiches_identifiees"]})
        reponse = self.service.repondre(dossier, {"logement": "oui"})["data"]["reponse"]
        self.assertEqual(reponse["statut_reponse"], "ANALYSE_CONFORME")
