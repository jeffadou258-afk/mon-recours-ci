# -*- coding: utf-8 -*-
"""Sauvegarde chiffrée et restauration — cycle complet sur données synthétiques.

Aucune donnée réelle n'est utilisée : tout est créé dans un répertoire
temporaire, puis supprimé. Le test vérifie le cycle entier — pas seulement la
création de l'archive — et les refus (mauvaise clé, archive altérée, clé absente).
"""

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
OUTIL = RACINE / "bin" / "sauvegarde.py"
MARQUEUR = "MARQUEUR_SECRET_FICTIF_42"
DOSSIER = "web-aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


def empreinte(chemin):
    return hashlib.sha256(Path(chemin).read_bytes()).hexdigest()


def contenu_logique(chemin):
    """Empreinte des données d'une base, indépendante de la disposition physique."""
    connexion = sqlite3.connect(str(chemin))
    resume = hashlib.sha256()
    for (table,) in sorted(connexion.execute(
            "select name from sqlite_master where type='table'")):
        resume.update(table.encode())
        for ligne in connexion.execute('select * from "%s" order by rowid' % table):
            resume.update(repr(ligne).encode())
    integrite = connexion.execute("pragma integrity_check").fetchone()[0]
    connexion.close()
    return resume.hexdigest(), integrite


@unittest.skipUnless(shutil.which("openssl"), "openssl requis")
class TestSauvegardeEtRestauration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.base = Path(tempfile.mkdtemp(prefix="test-sauvegarde-"))
        os.chmod(cls.base, 0o700)

        cls.dossiers = cls.base / "DOSSIERS"
        (cls.dossiers / DOSSIER / "BROUILLONS").mkdir(parents=True)
        (cls.dossiers / DOSSIER / "CONVERSATION.json").write_text(
            '{"recit": "%s"}' % MARQUEUR, encoding="utf-8")
        (cls.dossiers / DOSSIER / "BROUILLONS" / "note.txt").write_text(
            "brouillon fictif " + MARQUEUR, encoding="utf-8")

        cls.pdf = cls.dossiers / DOSSIER / "BROUILLONS" / "20260101-000000_reclamation.pdf"
        try:
            from fpdf import FPDF
            document = FPDF()
            document.add_page()
            document.set_font("Helvetica", size=11)
            document.multi_cell(0, 7, "COURRIER FICTIF " + MARQUEUR)
            document.output(str(cls.pdf))
            cls.pdf_reel = True
        except Exception:
            cls.pdf.write_bytes(b"%PDF-1.4\n% fictif\n%%EOF\n")
            cls.pdf_reel = False

        cls.base_sqlite = cls.base / "corpus.sqlite3"
        connexion = sqlite3.connect(str(cls.base_sqlite))
        connexion.execute("create table articles(numero text, texte text)")
        connexion.execute("insert into articles values (?, ?)", ("416", MARQUEUR))
        connexion.commit()
        connexion.close()

        cls.cle = cls.base / "cle"
        cls.cle.write_text(os.urandom(32).hex(), encoding="utf-8")
        os.chmod(cls.cle, 0o600)
        cls.mauvaise_cle = cls.base / "mauvaise"
        cls.mauvaise_cle.write_text(os.urandom(32).hex(), encoding="utf-8")
        os.chmod(cls.mauvaise_cle, 0o600)

        cls.sortie = cls.base / "sauvegardes"
        resultat = cls.executer("sauvegarder", "--sortie", str(cls.sortie),
                                "--dossiers", str(cls.dossiers),
                                "--base", str(cls.base_sqlite),
                                "--cle", str(cls.cle))
        assert resultat.returncode == 0, resultat.stderr
        cls.archive = next(cls.sortie.glob("*.enc"))
        cls.entete = cls.archive.with_suffix(".json")

        cls.avant = {p.relative_to(cls.dossiers).as_posix(): empreinte(p)
                     for p in cls.dossiers.rglob("*") if p.is_file()}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.base, ignore_errors=True)

    @classmethod
    def executer(cls, *arguments):
        return subprocess.run([sys.executable, str(OUTIL), *arguments],
                              capture_output=True, text=True)

    # -- création ---------------------------------------------------------

    def test_archive_et_entete_en_600(self):
        for chemin in (self.archive, self.entete):
            self.assertEqual(os.stat(chemin).st_mode & 0o777, 0o600, chemin.name)

    def test_archive_ne_revele_aucun_contenu(self):
        octets = self.archive.read_bytes()
        self.assertNotIn(MARQUEUR.encode(), octets)
        self.assertNotIn(b"CONVERSATION.json", octets)
        self.assertNotIn(b"reclamation", octets)

    def test_entete_sans_donnee_personnelle(self):
        entete = json.loads(self.entete.read_text(encoding="utf-8"))
        self.assertEqual(sorted(entete), sorted([
            "version", "cree_le", "algorithme", "iv", "mac", "octets_chiffre",
            "sha256_chiffre", "nb_fichiers", "contient"]))
        texte = self.entete.read_text(encoding="utf-8")
        self.assertNotIn(DOSSIER, texte)
        self.assertNotIn("DOSSIERS", texte)

    def test_nom_archive_sans_donnee(self):
        self.assertNotIn(DOSSIER, self.archive.name)
        self.assertRegex(self.archive.name, r"^sauvegarde-\d{8}-\d{6}-[0-9a-f]{8}\.enc$")

    # -- restauration -----------------------------------------------------

    def test_restauration_fidele_et_permissions(self):
        cible = Path(tempfile.mkdtemp(prefix="restau-")) / "DOSSIERS"
        base_cible = cible.parent / "base.sqlite3"
        resultat = self.executer("restaurer", "--archive", str(self.archive),
                                 "--sortie", str(cible),
                                 "--base-destination", str(base_cible),
                                 "--cle", str(self.cle))
        try:
            self.assertEqual(resultat.returncode, 0, resultat.stderr)
            apres = {p.relative_to(cible).as_posix(): empreinte(p)
                     for p in cible.rglob("*") if p.is_file()}
            self.assertEqual(apres, self.avant)

            self.assertEqual(os.stat(cible).st_mode & 0o777, 0o700)
            for chemin in cible.rglob("*"):
                attendu = 0o700 if chemin.is_dir() else 0o600
                self.assertEqual(os.stat(chemin).st_mode & 0o777, attendu, str(chemin))

            self.assertEqual(os.stat(base_cible).st_mode & 0o777, 0o600)
            self.assertEqual(contenu_logique(base_cible), contenu_logique(self.base_sqlite))
        finally:
            shutil.rmtree(cible.parent, ignore_errors=True)

    def test_pdf_restaure_lisible(self):
        if not self.pdf_reel:
            self.skipTest("fpdf2 absent : PDF non généré")
        cible = Path(tempfile.mkdtemp(prefix="restau-pdf-")) / "DOSSIERS"
        self.executer("restaurer", "--archive", str(self.archive), "--sortie", str(cible),
                      "--cle", str(self.cle))
        try:
            restaure = next(cible.rglob("*.pdf"))
            octets = restaure.read_bytes()
            self.assertTrue(octets.startswith(b"%PDF-"), "en-tête PDF attendu")
            self.assertGreater(len(octets), 200)
        finally:
            shutil.rmtree(cible.parent, ignore_errors=True)

    # -- refus ------------------------------------------------------------

    def test_mauvaise_cle_refusee(self):
        cible = self.base / "refus-mauvaise-cle"
        resultat = self.executer("restaurer", "--archive", str(self.archive),
                                 "--sortie", str(cible), "--cle", str(self.mauvaise_cle))
        self.assertEqual(resultat.returncode, 3)
        self.assertIn("MAC invalide", resultat.stderr)
        self.assertFalse(cible.exists(), "aucun répertoire ne doit être créé")

    def test_archive_alteree_refusee(self):
        alteree = self.base / "alteree.enc"
        octets = bytearray(self.archive.read_bytes())
        octets[len(octets) // 2] ^= 0xFF
        alteree.write_bytes(bytes(octets))
        shutil.copy2(self.entete, alteree.with_suffix(".json"))
        cible = self.base / "refus-alteree"
        resultat = self.executer("restaurer", "--archive", str(alteree),
                                 "--sortie", str(cible), "--cle", str(self.cle))
        self.assertEqual(resultat.returncode, 3)
        self.assertIn("altérée", resultat.stderr)

    def test_cle_absente_refusee(self):
        resultat = self.executer("sauvegarder", "--sortie", str(self.base / "sans-cle"),
                                 "--dossiers", str(self.dossiers),
                                 "--base", str(self.base_sqlite))
        self.assertEqual(resultat.returncode, 2)
        self.assertIn("clé absente", resultat.stderr)

    def test_cle_trop_courte_refusee(self):
        courte = self.base / "courte"
        courte.write_text("abcd", encoding="utf-8")
        resultat = self.executer("sauvegarder", "--sortie", str(self.base / "sans-cle"),
                                 "--dossiers", str(self.dossiers),
                                 "--base", str(self.base_sqlite), "--cle", str(courte))
        self.assertEqual(resultat.returncode, 2)
        self.assertFalse((self.base / "sans-cle").exists())

    def test_destination_non_vide_refusee(self):
        occupee = self.base / "occupee"
        occupee.mkdir(exist_ok=True)
        (occupee / "tresor.txt").write_text("ne pas écraser", encoding="utf-8")
        resultat = self.executer("restaurer", "--archive", str(self.archive),
                                 "--sortie", str(occupee), "--cle", str(self.cle))
        self.assertEqual(resultat.returncode, 5)
        self.assertTrue((occupee / "tresor.txt").exists())

    def test_origineaux_inchanges(self):
        apres = {p.relative_to(self.dossiers).as_posix(): empreinte(p)
                 for p in self.dossiers.rglob("*") if p.is_file()}
        self.assertEqual(apres, self.avant)
        self.assertTrue(self.archive.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
