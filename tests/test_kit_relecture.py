# -*- coding: utf-8 -*-
"""Kit de relecture juridique : complet, fidèle au corpus, et sans effet sur les statuts."""

import csv
import hashlib
import io
import json
import sys
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))
sys.path.insert(0, str(RACINE / "bin"))

import config  # noqa: E402
import kit_relecture  # noqa: E402


def _empreinte(chemin):
    return hashlib.sha256(Path(chemin).read_bytes()).hexdigest()


class TestKitRelecture(unittest.TestCase):
    DOMAINE = "logement_baux_foncier"

    def test_chaque_fiche_du_domaine_a_son_article_integral(self):
        md, _ = kit_relecture.construire(self.DOMAINE)
        fiches = [f for f in json.loads((RACINE / "KNOWLEDGE" / "catalogue.json").read_text(encoding="utf-8"))["fiches"]
                  if f["domaine"] == self.DOMAINE]
        self.assertGreater(len(fiches), 0)
        for fiche in fiches:
            self.assertIn("`%s`" % fiche["id"], md)
            self.assertIn(fiche["citation"], md, "l'extrait cité doit être repris mot pour mot")
        self.assertNotIn("Article introuvable", md)

    def test_la_grille_a_une_ligne_par_fiche_et_aucune_decision_pre_remplie(self):
        md, tableau = kit_relecture.construire(self.DOMAINE)
        lignes = list(csv.reader(io.StringIO(tableau), delimiter=";"))
        self.assertEqual(lignes[0], kit_relecture.COLONNES_DECISION)
        self.assertEqual(len(lignes) - 1, md.count("**Décision** :"))
        for ligne in lignes[1:]:
            self.assertTrue(all(c == "" for c in ligne[3:]), "aucune décision ne doit être pré-remplie")

    def test_aucun_statut_ni_fichier_source_n_est_modifie(self):
        sources = [config.CHEMIN_DB, RACINE / "KNOWLEDGE" / "catalogue.json",
                   RACINE / "KNOWLEDGE" / "questions_clarification.json"]
        avant = [_empreinte(p) for p in sources]
        kit_relecture.construire(self.DOMAINE)
        self.assertEqual(avant, [_empreinte(p) for p in sources])

    def test_le_document_dit_qu_il_ne_valide_rien(self):
        md, _ = kit_relecture.construire(self.DOMAINE)
        self.assertIn("ne valide rien", md)
        self.assertIn("A_RELIRE_PAR_UN_JURISTE", md)

    def test_domaine_inconnu_refuse(self):
        with self.assertRaises(SystemExit):
            kit_relecture.construire("domaine_qui_n_existe_pas")


if __name__ == "__main__":
    unittest.main()
