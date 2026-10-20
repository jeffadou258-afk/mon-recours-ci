# -*- coding: utf-8 -*-
"""Qualité d'un calque texte — garde-fou ajouté le 20/10/2026.

Contexte mesuré : le JO OHADA du 4 février 2014 (AUSCGIE) possède une couche
texte produite par un mauvais encodeur — « Ie » pour « le », « Btat » pour
« État », « uniforrne », 0,21 % de caractères accentués contre 3,28 % pour un
calque sain. Il était pourtant classé `CALQUE_TEXTE`, indexé, puis promu
`VERIFIE` sur la seule couverture des numéros d'articles.

Ces tests fixent le seuil et empêchent sa suppression silencieuse.
"""

import importlib.util
import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _module():
    specification = importlib.util.spec_from_file_location(
        "integrer_collecte_calque", os.path.join(RACINE, "bin", "integrer_collecte.py"))
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


integrer = _module()


class TestTauxAccentue(unittest.TestCase):
    def test_texte_vide(self):
        self.assertEqual(integrer.taux_accentue(""), 0.0)
        self.assertEqual(integrer.taux_accentue(None), 0.0)

    def test_calque_sain(self):
        """Un texte français normal dépasse largement le seuil."""
        sain = ("Le contrat de location peut prévoir un dépôt de garantie à la charge du "
                "locataire qui ne peut excéder deux mois de loyer. L'état des lieux est "
                "établi contradictoirement ; les réparations locatives sont à la charge "
                "du locataire selon l'usage. Cette évaluation est nécessaire.")
        self.assertGreater(integrer.taux_accentue(sain), integrer.ACCENTS_MINIMAUX * 2)

    def test_calque_degrade_reel(self):
        """Extrait réel du JO OHADA 2014 : aucun accent, « Ie », « uniforrne »."""
        degrade = ("Toute societe commerciale, y compris celle dans laquelle un Btat ou une "
                   "personne morale de droit public est associe, est un commercant. Le present "
                   "Acte uniforrne sera publie au Journal Officiel dans un delai de soixante "
                   "jours. Ie cas echeant, les societes constituted anterieurement.")
        self.assertLess(integrer.taux_accentue(degrade), integrer.ACCENTS_MINIMAUX)

    def test_texte_technique_sans_accent_reste_sous_le_seuil(self):
        """Un texte sans aucun accent ne doit jamais passer pour un calque sain."""
        self.assertEqual(integrer.taux_accentue("ARTICLE 1 - LE PRESENT ACTE EST APPLICABLE"), 0.0)

    def test_seuil_documente(self):
        self.assertEqual(integrer.ACCENTS_MINIMAUX, 0.01)


class TestGardeFouDansLeControle(unittest.TestCase):
    """Le contrôle doit basculer un calque dégradé vers l'OCR."""

    def test_le_controle_bascule_vers_ocr_requis(self):
        with open(os.path.join(RACINE, "bin", "integrer_collecte.py"), encoding="utf-8") as flux:
            source = flux.read()
        self.assertIn('methode = "OCR_REQUIS"', source,
                      "le basculement d'un calque dégradé vers l'OCR a disparu du contrôle")
        self.assertIn("taux_accentue(natif)", source,
                      "le contrôle ne mesure plus la qualité du calque")

    def test_un_calque_degrade_n_est_pas_integre_par_la_voie_calque(self):
        """`officialiser` (voie calque) exige exactement CALQUE_TEXTE : OCR_REQUIS l'exclut."""
        with open(os.path.join(RACINE, "bin", "integrer_collecte.py"), encoding="utf-8") as flux:
            source = flux.read()
        self.assertIn('d["methode_extraction"] != "CALQUE_TEXTE"', source)
        self.assertIn('d["methode_extraction"].startswith("OCR")', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
