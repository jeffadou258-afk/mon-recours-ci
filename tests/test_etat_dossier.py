# -*- coding: utf-8 -*-
"""Taille de l'état d'un dossier — ce qui est écrit sur disque, et ce qui n'y a pas sa place.

Constat mesuré avant correction : chaque `DOSSIER_EN_COURS.json` pesait ~2,5 Mo,
dont ~300 Ko PAR référence candidate, parce que le texte complet de l'acte était
recopié dans l'état. Sur 175 dossiers, cela faisait 404 Mo de journaux d'état,
pour un champ qu'aucune partie du code ne relisait ensuite.

Ce test construit une référence synthétique volumineuse (aucun contenu juridique
réel), ouvre un dossier, et vérifie l'état écrit : la référence reste traçable,
son texte n'y est plus, et le fichier reste petit.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from agent import MonRecoursCI  # noqa: E402
from core import base  # noqa: E402

DOSSIER = "TEST_TAILLE_ETAT"
TEXTE_ARTICLE = "Article 1 — " + ("le bailleur restitue la caution au locataire. " * 6000)
TAILLE_TEXTE = len(TEXTE_ARTICLE.encode("utf-8"))
DEMANDE = "Mon bailleur refuse de me rendre la caution que j'ai versée en quittant le logement."


class TestTailleEtatDossier(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="mrc_taille_")
        self.chemin_db = os.path.join(self.tmp, "corpus.sqlite3")
        self.chemin_sources = os.path.join(self.tmp, "verifs.json")
        base.initialiser(self.chemin_db)
        self.ref_id = base.ajouter_reference(
            "Loi synthétique sur le bail (test)",
            "loi",
            "Source de test (aucune valeur juridique)",
            "https://exemple.invalid/loi-synthetique-2099-001.pdf",
            "2026-10-21",
            numero_texte="2099-001",
            articles="1 article",
            domaine="logement_baux_foncier",
            extrait_texte=TEXTE_ARTICLE,
            texte_complet_present=True,
            chemin=self.chemin_db,
        )
        self.agent = MonRecoursCI(chemin_db=self.chemin_db, chemin_sources=self.chemin_sources)
        self.chemin_etat = config.dossier_utilisateur(DOSSIER) / "DOSSIER_EN_COURS.json"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)
        shutil.rmtree(config.dossier_utilisateur(DOSSIER), ignore_errors=True)

    def test_le_texte_de_l_acte_n_est_pas_recopie_dans_l_etat(self):
        dossier = self.agent.ouvrir_dossier(DOSSIER, DEMANDE)
        candidats = dossier["references_candidates"]
        self.assertTrue(candidats, "la référence synthétique aurait dû être trouvée")

        etat = json.loads(self.chemin_etat.read_text(encoding="utf-8"))
        for candidat in etat["references_candidates"]:
            self.assertNotIn("extrait_texte", candidat,
                             "le texte complet de l'acte ne doit pas être persisté")

    def test_l_etat_reste_petit_malgre_une_reference_volumineuse(self):
        self.assertGreater(TAILLE_TEXTE, 200000, "le test doit porter sur un texte volumineux")
        self.agent.ouvrir_dossier(DOSSIER, DEMANDE)
        taille = self.chemin_etat.stat().st_size
        self.assertLess(taille, 100000,
                        "état de dossier trop gros (%d octets) : le texte de l'acte y est revenu" % taille)

    def test_la_reference_reste_tracable(self):
        """Retirer le texte ne doit pas effacer ce qui identifie la référence."""
        dossier = self.agent.ouvrir_dossier(DOSSIER, DEMANDE)
        premier = dossier["references_candidates"][0]
        self.assertEqual(premier["ref_id"], self.ref_id)
        self.assertIn("titre_officiel", premier)
        self.assertIn("source_url", premier)
        self.assertIn("etat_verification", premier)


if __name__ == "__main__":
    unittest.main(verbosity=2)
