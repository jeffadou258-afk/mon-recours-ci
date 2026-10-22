# -*- coding: utf-8 -*-
"""Les fiches préparées doivent rester inoffensives tant qu'un juriste ne les a pas lues.

Trois propriétés sont verrouillées ici :

1. la citation est EXACTEMENT l'article indexé — même texte, même empreinte ;
2. aucune fiche ne porte un statut de validation, et le moteur ne les charge pas ;
3. une question hors sujet ne les déclenche pas (naissance ≠ consommation,
   saisie ≠ associations) : c'est le contrôle négatif qui manquait quand le
   moteur citait « l'État garantit les besoins des personnes vulnérables » pour
   une déclaration de naissance.
"""
import json
import os
import re
import sqlite3
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import config
from core import catalogue

CHEMIN_FICHES = os.path.join(RACINE, "KNOWLEDGE", "catalogue_a_valider.json")
STATUT = "A_VALIDER_PAR_JURISTE"


def _normaliser(texte):
    return " ".join((texte or "").split())


def _sans_tiret(texte):
    return re.sub(r"^[\s\u2010-\u2015\-]+", "", _normaliser(texte))


def charger_fiches():
    with open(CHEMIN_FICHES, encoding="utf-8") as flux:
        return json.load(flux)


def correspond(fiche, question):
    q = _normaliser(question).lower()
    return any(_normaliser(d).lower() in q for d in fiche["declencheurs"])


class FichesAValider(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.document = charger_fiches()
        cls.fiches = cls.document["fiches"]
        cls.conn = sqlite3.connect(config.CHEMIN_DB)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    # ------------------------------------------------------------------ provenance
    def test_chaque_citation_est_l_article_indexe(self):
        for fiche in self.fiches:
            ligne = self.conn.execute(
                """SELECT a.texte, a.sha256_article
                     FROM articles_corpus a
                     JOIN documents d ON d.doc_id = a.doc_id
                     JOIN references_juridiques j ON j.ref_id = d.ref_id
                    WHERE j.numero_texte = ? AND a.numero = ?""",
                (fiche["numero_texte"], fiche["article"]),
            ).fetchone()
            self.assertIsNotNone(
                ligne, "%s : article %s introuvable dans %s" % (fiche["id"], fiche["article"], fiche["numero_texte"])
            )
            if fiche.get("citation_tronquee"):
                # Troncature DÉCLARÉE : la citation doit être un préfixe EXACT du texte
                # indexé, et le reste ne doit contenir que des en-têtes de section que
                # l'OCR a fusionnés dans le corps de l'article. Aucun mot inventé n'est
                # toléré ; aucune troncature silencieuse non plus.
                self.assertTrue(fiche.get("motif_troncature"), "%s : troncature non motivée" % fiche["id"])
                indexe = _sans_tiret(ligne[0])
                self.assertTrue(
                    indexe.startswith(fiche["citation"]),
                    "%s : la citation n'est pas le début du texte indexé" % fiche["id"],
                )
                reste = indexe[len(fiche["citation"]):].strip()
                self.assertRegex(
                    reste, r"^(TITRE|CHAPITRE|Section|LIVRE)\b",
                    "%s : le texte écarté n'est pas un en-tête de section : %r" % (fiche["id"], reste[:80]),
                )
            else:
                self.assertEqual(
                    _sans_tiret(ligne[0]), fiche["citation"],
                    "%s : la citation ne correspond pas au texte indexé" % fiche["id"],
                )
            self.assertEqual(fiche["sha256_article"], ligne[1], "%s : empreinte divergente" % fiche["id"])

    def test_aucune_citation_vide_ou_tronquee(self):
        for fiche in self.fiches:
            self.assertGreater(len(fiche["citation"]), 80, fiche["id"])
            self.assertFalse(fiche["citation"].startswith("…"), fiche["id"])

    # ------------------------------------------------------------------ statut
    def test_toutes_les_fiches_sont_a_valider(self):
        for fiche in self.fiches:
            self.assertEqual(fiche["etat_verification"], STATUT, fiche["id"])

    def test_aucune_fiche_ne_se_declare_validee(self):
        charge = json.dumps(self.document, ensure_ascii=False)
        self.assertNotIn('"VERIFIE"', charge)
        self.assertNotIn("TERMINE_ET_VERIFIE", charge)

    def test_le_moteur_ne_charge_pas_ces_fiches(self):
        """Elles ne doivent répondre à aucun citoyen : elles vivent hors du catalogue."""
        moteur = {f["id"] for f in catalogue.charger()}
        ajoutees = {f["id"] for f in self.fiches}
        self.assertEqual(moteur & ajoutees, set(),
                         "une fiche A_VALIDER a été introduite dans le catalogue du moteur")

    # ------------------------------------------------------------------ pertinence
    def test_chaque_fiche_repond_a_sa_propre_question(self):
        for fiche in self.fiches:
            question = "Bonjour, %s. Que dit la loi ?" % fiche["declencheurs"][0]
            self.assertTrue(correspond(fiche, question), fiche["id"])

    def test_naissance_ne_declenche_aucune_fiche_consommation(self):
        question = ("Je veux déclarer la naissance de mon enfant à l'état civil, "
                    "il n'a pas d'acte de naissance.")
        declenchees = [f["id"] for f in self.fiches
                       if f["domaine"] == "consommation" and correspond(f, question)]
        self.assertEqual(declenchees, [], "une question de naissance a déclenché une fiche consommation")

    def test_saisie_bancaire_ne_declenche_aucune_fiche_association(self):
        question = "Je veux saisir le compte bancaire de mon débiteur qui ne paie pas."
        declenchees = [f["id"] for f in self.fiches
                       if f["domaine"] == "associations_organisations_religieuses" and correspond(f, question)]
        self.assertEqual(declenchees, [], "une saisie bancaire a déclenché une fiche associations")

    def test_chaque_constat_renvoie_a_un_article_du_domaine(self):
        for fiche in self.fiches:
            domaine = self.conn.execute(
                "SELECT domaine FROM references_juridiques WHERE numero_texte = ?",
                (fiche["numero_texte"],),
            ).fetchone()
            self.assertIsNotNone(domaine, fiche["id"])
            self.assertEqual(domaine[0], fiche["domaine"], fiche["id"])

    # ------------------------------------------------------------------ honnêteté
    def test_les_informations_non_etablies_sont_explicites(self):
        """Quand le texte renvoie à un décret absent, la fiche doit le dire."""
        for fiche in self.fiches:
            self.assertIsInstance(fiche["informations_non_etablies"], list, fiche["id"])
            for mention in fiche["informations_non_etablies"]:
                self.assertIn("INFORMATION_NON_ETABLIE", mention, fiche["id"])

    def test_aucune_demarche_inventee(self):
        """L'étape de plan est un constat, pas une procédure administrative inventée."""
        interdits = ("adressez-vous au tribunal", "saisissez le tribunal", "déposez plainte",
                     "payez l'amende", "formulaire CERFA")
        for fiche in self.fiches:
            texte = fiche["etape_plan"].lower()
            for interdit in interdits:
                self.assertNotIn(interdit, texte, "%s : démarche inventée" % fiche["id"])


if __name__ == "__main__":
    unittest.main()
