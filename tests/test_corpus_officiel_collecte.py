# -*- coding: utf-8 -*-
"""Textes officiels intégrés depuis la collecte (octobre 2026) et fiches qui s'y appuient.

Ce que ces tests garantissent — et ce qu'ils ne garantissent pas :
  * un texte lu par OCR reste marqué comme tel (origine OCR_AUTO, aucun recoupement
    officiel prétendu, référence PARTIELLEMENT_VERIFIE) ;
  * les fiches OHADA sont servies pour les bons récits et n'inventent aucun nombre ;
  * AUCUN de ces tests ne vaut validation juridique.
"""

import os
import shutil
import sqlite3
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402
from core import catalogue, service  # noqa: E402
from tests import evaluation_24_domaines as evaluation  # noqa: E402

TEXTES_OCR = ("AUPSRVE-2023", "2016-1111", "2016-886")


def _connexion():
    return sqlite3.connect(str(config.CHEMIN_DB))


class TestProvenanceDesTextesOCR(unittest.TestCase):
    def test_references_partiellement_verifiees(self):
        with _connexion() as conn:
            for numero in TEXTES_OCR:
                etats = {r[0] for r in conn.execute(
                    "SELECT etat_verification FROM references_juridiques WHERE numero_texte = ?", (numero,))}
                self.assertEqual(etats, {"PARTIELLEMENT_VERIFIE"}, numero)

    def test_articles_marques_ocr_et_non_recoupes(self):
        with _connexion() as conn:
            for numero in TEXTES_OCR:
                lignes = conn.execute(
                    "SELECT a.origine_texte, a.recoupe, d.calque_texte FROM articles_corpus a"
                    " JOIN documents d ON d.doc_id = a.doc_id WHERE d.numero_texte = ?", (numero,)).fetchall()
                self.assertTrue(lignes, numero)
                self.assertEqual({(o, r, c) for o, r, c in lignes}, {("OCR_AUTO", 0, 0)}, numero)

    def test_aupsrve_mesure_contre_une_reproduction_declaree(self):
        with _connexion() as conn:
            lignes = conn.execute(
                "SELECT a.confiance_ocr, a.doc_reference FROM articles_corpus a JOIN documents d"
                " ON d.doc_id = a.doc_id WHERE d.numero_texte = 'AUPSRVE-2023'").fetchall()
        self.assertTrue(all(c is not None and c >= 0.80 for c, _ in lignes))
        self.assertTrue(all(r.startswith("SECONDAIRE:") for _, r in lignes))

    def test_aucun_marqueur_de_page_dans_les_articles(self):
        with _connexion() as conn:
            for numero in TEXTES_OCR:
                for (texte,) in conn.execute(
                        "SELECT a.texte FROM articles_corpus a JOIN documents d ON d.doc_id = a.doc_id"
                        " WHERE d.numero_texte = ?", (numero,)):
                    self.assertNotIn("[OCR conf=", texte)
                    self.assertNotIn("Journal officiel OHADA 2023 Az", texte)

    def test_document_officiel_de_l_ohada(self):
        with _connexion() as conn:
            (url,) = conn.execute("SELECT url_source FROM documents WHERE numero_texte = 'AUPSRVE-2023'").fetchone()
        self.assertTrue(url.startswith("https://www.ohada.org/"))


class TestFichesOHADA(unittest.TestCase):
    IDS = {"OHADA_8", "OHADA_10", "OHADA_13", "OHADA_16", "OHADA_28", "OHADA_50", "OHADA_153",
           "OHADA_173", "OHADA_177"}

    def test_fiches_chargees_et_revalidees(self):
        fiches = {f["id"]: f for f in catalogue.charger()}
        self.assertTrue(self.IDS <= set(fiches))
        for identifiant in self.IDS:
            self.assertEqual(fiches[identifiant]["origine_texte"], "OCR_AUTO")
            self.assertEqual(fiches[identifiant]["etat_verification"], "PARTIELLEMENT_VERIFIE")

    def test_la_quotite_saisissable_n_est_pas_inventee(self):
        fiche = {f["id"]: f for f in catalogue.charger()}["OHADA_177"]
        self.assertFalse(any(c.isdigit() for c in fiche["lecture"]))

    def _scenario(self, recit, **attendu):
        return evaluation.evaluer(23, "collecte", {"recit": recit, "attendu": attendu}, prefixe="COLLECTE")

    def test_injonction_de_payer(self):
        r = self._scenario("J'ai reçu une ordonnance d'injonction de payer et je veux faire opposition",
                           etape="clarification", fiches={"OHADA_10"}, questions_min=1,
                           urgence_min="ELEVEE", abstention=True)
        self.assertTrue(r["ok"], r)

    def test_saisie_sur_salaire_sans_chiffre_invente(self):
        r = self._scenario("Combien peut-on saisir sur mon salaire ? Mon créancier veut faire une saisie sur salaire",
                           etape="clarification", fiches={"OHADA_177"}, abstention=True)
        self.assertTrue(r["ok"], r)

    def test_saisie_sur_compte(self):
        r = self._scenario("L'huissier a fait une saisie sur mon compte bancaire",
                           etape="clarification", fiches={"OHADA_153"}, interdites={"LOGEME_416"},
                           urgence_min="ELEVEE")
        self.assertTrue(r["ok"], r)

    def test_parcours_complet_conforme(self):
        identifiant = "COLLECTE_PARCOURS"
        try:
            service.ouvrir(identifiant, "J'ai reçu une ordonnance d'injonction de payer, l'huissier m'a remis "
                                        "l'acte hier, je conteste la dette.")
            resultat = service.repondre(identifiant, {"ohada_signification_recue": "oui"})
            self.assertTrue(resultat["ok"], resultat)
            reponse = resultat["data"]["reponse"]
            self.assertEqual(reponse["statut_reponse"], "ANALYSE_CONFORME")
            for source in reponse["sections"]["6_sources"]:
                self.assertEqual(source["origine_texte"], "OCR_AUTO")
                self.assertFalse(source["recoupe"])
        finally:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
