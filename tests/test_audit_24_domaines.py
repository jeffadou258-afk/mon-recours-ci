# -*- coding: utf-8 -*-
"""Audit des 24 domaines — un sous-test par domaine et par type de cas.

Les attendus décrivent le comportement voulu du service (routage, prudence,
urgence, abstention). Un test vert ne valide pas le droit.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from evaluation_24_domaines import evaluer  # noqa: E402
from scenarios_24_domaines import SCENARIOS, TYPES  # noqa: E402


class TestAudit24Domaines(unittest.TestCase):
    def test_les_24_domaines_ont_les_7_types(self):
        self.assertEqual(sorted(SCENARIOS), list(range(1, 25)))
        for code, cas in SCENARIOS.items():
            self.assertEqual(set(cas), set(TYPES), "domaine %d" % code)

    def test_scenarios(self):
        for code, cas in sorted(SCENARIOS.items()):
            for type_cas in TYPES:
                scenario = cas[type_cas]
                if "sans_objet" in scenario:
                    continue
                with self.subTest(domaine=code, cas=type_cas, recit=scenario["recit"]):
                    resultat = evaluer(code, type_cas, scenario)
                    self.assertTrue(resultat["ok"], "%s — observé : %s"
                                    % ("; ".join(resultat["ecarts"]), resultat["observe"]))


if __name__ == "__main__":
    unittest.main()
