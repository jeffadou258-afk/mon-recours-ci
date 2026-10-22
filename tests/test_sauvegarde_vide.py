# -*- coding: utf-8 -*-
"""Sauvegarde prise alors que `DOSSIERS/` est vide.

Cas réel rencontré lors de l'installation sur le serveur : une sauvegarde faite
avant la première consultation ne contient aucune entrée `dossiers/`, et la
restauration échouait sur `FileNotFoundError` — un défaut qui n'apparaît qu'au
moment où l'on a le plus besoin de la sauvegarde.

Une archive valide doit toujours pouvoir être restaurée : la destination devient
un répertoire vide, et la base se restaure normalement.
"""

import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

OUTIL = Path(__file__).resolve().parent.parent / "bin" / "sauvegarde.py"


class TestSauvegardeSansRecits(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = Path(tempfile.mkdtemp(prefix="mrc_vide_"))
        cls.dossiers = cls.base / "DOSSIERS"
        cls.dossiers.mkdir()  # volontairement vide

        cls.base_sqlite = cls.base / "corpus.sqlite3"
        connexion = sqlite3.connect(str(cls.base_sqlite))
        connexion.execute("create table articles(numero text, texte text)")
        connexion.execute("insert into articles values (?, ?)", ("416", "texte de controle"))
        connexion.commit()
        connexion.close()

        cls.cle = cls.base / "cle"
        cls.cle.write_text(os.urandom(32).hex(), encoding="utf-8")
        os.chmod(cls.cle, 0o600)

        cls.sortie = cls.base / "sauvegardes"
        resultat = cls.executer("sauvegarder", "--sortie", str(cls.sortie),
                                "--dossiers", str(cls.dossiers),
                                "--base", str(cls.base_sqlite), "--cle", str(cls.cle))
        assert resultat.returncode == 0, resultat.stderr
        cls.archive = next(cls.sortie.glob("*.enc"))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    @classmethod
    def executer(cls, *arguments):
        return subprocess.run([sys.executable, str(OUTIL), *arguments],
                              capture_output=True, text=True)

    def test_restauration_reussit_sans_recits(self):
        cible = self.base / "restaure"
        base_cible = self.base / "corpus-restaure.sqlite3"
        resultat = self.executer("restaurer", "--archive", str(self.archive),
                                 "--sortie", str(cible),
                                 "--base-destination", str(base_cible),
                                 "--cle", str(self.cle))
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertIn("restauration", resultat.stdout)

    def test_repertoire_cible_existe_et_est_vide(self):
        cible = self.base / "restaure-vide"
        resultat = self.executer("restaurer", "--archive", str(self.archive),
                                 "--sortie", str(cible), "--cle", str(self.cle))
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        self.assertTrue(cible.is_dir(), "la destination doit exister après restauration")
        self.assertEqual(list(cible.iterdir()), [], "aucun récit à restaurer ici")
        self.assertEqual(os.stat(cible).st_mode & 0o777, 0o700, "permissions privées restaurées")

    def test_base_restauree_identique(self):
        cible = self.base / "restaure-base"
        base_cible = self.base / "verif.sqlite3"
        resultat = self.executer("restaurer", "--archive", str(self.archive),
                                 "--sortie", str(cible),
                                 "--base-destination", str(base_cible),
                                 "--cle", str(self.cle))
        self.assertEqual(resultat.returncode, 0, resultat.stderr)
        connexion = sqlite3.connect(str(base_cible))
        lignes = connexion.execute("select numero, texte from articles").fetchall()
        connexion.close()
        self.assertEqual(lignes, [("416", "texte de controle")])


if __name__ == "__main__":
    unittest.main(verbosity=2)
