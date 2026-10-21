# -*- coding: utf-8 -*-
"""Conservation des consultations — purge à 90 jours, sur dates fixes.

Le script testé est celui qui sera installé (`web/scripts/purger-consultations.mjs`).
Les dossiers sont créés dans un répertoire temporaire, avec des dates de
modification imposées : aucun dossier réel n'est lu ni touché.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SCRIPT = RACINE / "web" / "scripts" / "purger-consultations.mjs"
JOUR = 86400

IDENTIFIANTS = {
    "recent": "web-aaaaaaaa-1111-4111-8111-111111111111",
    "limite": "web-bbbbbbbb-2222-4222-8222-222222222222",
    "ancien": "web-cccccccc-3333-4333-8333-333333333333",
    "hors_motif": "CLI_DEMO",
}


@unittest.skipUnless(shutil.which("node"), "node requis")
class TestPurge(unittest.TestCase):

    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="test-purge-"))
        os.chmod(self.base, 0o700)
        self.racine = self.base / "DOSSIERS"
        self.racine.mkdir()
        self.journal = self.base / "purge.jsonl"

        maintenant = time.time()
        # 89 jours : encore dans la période -> conservé.
        self._dossier(IDENTIFIANTS["recent"], maintenant - 89 * JOUR)
        # 90 jours + 1 h : juste au-delà -> éligible.
        self._dossier(IDENTIFIANTS["limite"], maintenant - 90 * JOUR - 3600)
        # 91 jours -> éligible.
        self._dossier(IDENTIFIANTS["ancien"], maintenant - 91 * JOUR)
        # Nom hors motif, très ancien -> jamais touché.
        self._dossier(IDENTIFIANTS["hors_motif"], maintenant - 400 * JOUR)

    def tearDown(self):
        shutil.rmtree(self.base, ignore_errors=True)

    def _dossier(self, nom, horodatage):
        chemin = self.racine / nom
        chemin.mkdir()
        (chemin / "CONVERSATION.json").write_text('{"recit": "fictif"}', encoding="utf-8")
        os.utime(chemin, (horodatage, horodatage))

    def _lancer(self, *arguments):
        environnement = dict(os.environ,
                             MONRECOURS_DOSSIERS=str(self.racine),
                             MONRECOURS_JOURNAL_PURGE=str(self.journal))
        return subprocess.run(["node", str(SCRIPT), *arguments],
                              capture_output=True, text=True, env=environnement)

    def _restants(self):
        return sorted(p.name for p in self.racine.iterdir())

    # -- période de conservation -------------------------------------------

    def test_89_jours_conserve(self):
        self._lancer("--jours", "90", "--confirmer")
        self.assertIn(IDENTIFIANTS["recent"], self._restants())

    def test_90_jours_depasses_et_91_jours_supprimes(self):
        self._lancer("--jours", "90", "--confirmer")
        restants = self._restants()
        self.assertNotIn(IDENTIFIANTS["limite"], restants)
        self.assertNotIn(IDENTIFIANTS["ancien"], restants)

    def test_hors_motif_jamais_touche(self):
        self._lancer("--jours", "90", "--confirmer")
        self.assertIn(IDENTIFIANTS["hors_motif"], self._restants())

    # -- simulation par défaut ---------------------------------------------

    def test_simulation_ne_supprime_rien(self):
        resultat = self._lancer("--jours", "90")
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertEqual(len(self._restants()), 4)
        self.assertIn("simulation", resultat.stdout)

    def test_confirmation_necessaire(self):
        self._lancer("--jours", "90")
        self.assertTrue((self.racine / IDENTIFIANTS["ancien"]).exists())

    # -- confinement --------------------------------------------------------

    def test_lien_symbolique_ignore(self):
        dehors = self.base / "dehors"
        dehors.mkdir()
        (dehors / "precieux.txt").write_text("à ne pas supprimer", encoding="utf-8")
        lien = self.racine / "web-dddddddd-4444-4444-8444-444444444444"
        lien.symlink_to(dehors)
        vieux = time.time() - 200 * JOUR
        os.utime(dehors, (vieux, vieux))

        self._lancer("--jours", "90", "--confirmer")
        self.assertTrue((dehors / "precieux.txt").exists(), "la cible du lien doit survivre")
        self.assertTrue(lien.is_symlink())

    def test_racine_absente_ne_plante_pas(self):
        environnement = dict(os.environ,
                             MONRECOURS_DOSSIERS=str(self.base / "inexistant"),
                             MONRECOURS_JOURNAL_PURGE=str(self.journal))
        resultat = subprocess.run(["node", str(SCRIPT), "--jours", "90"],
                                  capture_output=True, text=True, env=environnement)
        self.assertEqual(resultat.returncode, 0)

    # -- paramètres et journal ---------------------------------------------

    def test_duree_invalide_refusee(self):
        for valeur in ("0", "-5", "abc", ""):
            with self.subTest(valeur=valeur):
                resultat = self._lancer("--jours", valeur)
                self.assertEqual(resultat.returncode, 2)

    def test_journal_sans_donnee_personnelle(self):
        self._lancer("--jours", "90", "--confirmer")
        lignes = [json.loads(l) for l in self.journal.read_text(encoding="utf-8").splitlines() if l.strip()]
        self.assertEqual(len(lignes), 1)
        entree = lignes[0]
        self.assertEqual(sorted(entree), sorted([
            "horodatage", "mode", "jours", "eligibles", "conserves",
            "supprimes", "echecs", "duree_ms"]))
        texte = json.dumps(entree)
        for identifiant in IDENTIFIANTS.values():
            self.assertNotIn(identifiant, texte)
        self.assertNotIn("recit", texte)
        self.assertEqual(entree["supprimes"], 2)
        self.assertEqual(entree["conserves"], 1)

    def test_journal_ecrit_aussi_en_simulation(self):
        self._lancer("--jours", "90")
        entree = json.loads(self.journal.read_text(encoding="utf-8").splitlines()[0])
        self.assertEqual(entree["mode"], "simulation")
        self.assertEqual(entree["supprimes"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
