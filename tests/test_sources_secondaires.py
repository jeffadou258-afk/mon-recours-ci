"""Le régime des sources secondaires ne doit jamais ouvrir la porte au statut VERIFIE.

Décision du 22/10/2026 : FAOLEX (FAO, Nations unies) reproduit des numéros du
Journal officiel ivoirien. Ces copies entrent au corpus — sans elles, les
domaines travail, consommation et associations resteraient vides — mais elles
ne peuvent pas atteindre l'état VERIFIE, réservé au périmètre officiel.
"""
import os
import sys
import unittest

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import config
from core import sources


class SourcesSecondaires(unittest.TestCase):
    def test_faolex_n_est_pas_officiel(self):
        """La garde qui protège VERIFIE ne doit pas considérer FAOLEX comme officiel."""
        self.assertFalse(sources.est_hote_officiel("https://faolex.fao.org/docs/pdf/ivc210897.pdf"))

    def test_faolex_est_secondaire_declare(self):
        self.assertEqual(
            sources.est_source_secondaire("https://faolex.fao.org/docs/pdf/ivc210897.pdf"),
            "FAOLEX",
        )

    def test_un_blog_reste_refuse(self):
        """Un hôte inconnu n'est ni officiel ni secondaire : aucun des deux régimes."""
        for url in ("https://blog-juridique.example/loi.pdf",
                    "https://fr.scribd.com/document/123",
                    "https://www.droit-afrique.com/upload/doc/cote-divoire.pdf"):
            self.assertIsNone(sources.est_source_secondaire(url), url)
            self.assertFalse(sources.est_hote_officiel(url), url)

    def test_le_plafond_ne_peut_pas_etre_releve_sans_decision(self):
        """Si quelqu'un passe le plafond à VERIFIE, ce test tombe.

        C'est volontaire : relever le plafond change la nature de la preuve
        exigée du produit, pas un détail de configuration.
        """
        for entree in config.SOURCES_SECONDAIRES:
            self.assertEqual(entree["plafond"], "PARTIELLEMENT_VERIFIE")

    def test_les_domaines_du_journal_officiel_sont_declares(self):
        """Les deux numéros du JO utilisés sont bien des hôtes secondaires connus."""
        for url in ("https://faolex.fao.org/docs/pdf/ivc210897.pdf",
                    "https://faolex.fao.org/docs/pdf/ivc229657.pdf"):
            self.assertEqual(sources.est_source_secondaire(url), "FAOLEX")


if __name__ == "__main__":
    unittest.main()
