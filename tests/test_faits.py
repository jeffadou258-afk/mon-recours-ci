# -*- coding: utf-8 -*-
"""Faits : un fait déclaré n'est jamais promu sans pièce réelle."""

import hashlib
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.faits import Faits, empreinte_fichier  # noqa: E402


class TestFaits(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="mrc_faits_")
        self.collecte = Faits("TEST_FAITS")

    def tearDown(self):
        shutil.rmtree(self.dossier, ignore_errors=True)

    def _piece(self, nom, contenu=b"piece de test"):
        chemin = os.path.join(self.dossier, nom)
        with open(chemin, "wb") as f:
            f.write(contenu)
        return chemin

    def test_un_fait_declare_est_declare(self):
        fait = self.collecte.declarer("Le bail a été signé en janvier.", date_fait="2026-01-10")
        self.assertEqual(fait["etat"], "DECLARE_PAR_L_UTILISATEUR")
        self.assertIsNone(fait["empreinte_piece"])
        self.assertEqual(len(self.collecte.declares), 1)

    def test_fait_vide_refuse(self):
        with self.assertRaises(ValueError):
            self.collecte.declarer("   ")

    def test_documenter_exige_une_piece_existante(self):
        fait = self.collecte.declarer("Le bail a été signé en janvier.")
        with self.assertRaises(FileNotFoundError):
            self.collecte.documenter(fait["fait_id"], os.path.join(self.dossier, "inexistant.pdf"))

    def test_documenter_calcule_l_empreinte_reelle(self):
        chemin = self._piece("bail.txt", b"contenu du bail")
        fait = self.collecte.declarer("Le bail a été signé en janvier.")
        self.collecte.documenter(fait["fait_id"], chemin)
        attendu = "sha256:" + hashlib.sha256(b"contenu du bail").hexdigest()
        self.assertEqual(fait["etat"], "DOCUMENTE")
        self.assertEqual(fait["empreinte_piece"], attendu)

    def test_documenter_sans_chemin_refuse(self):
        fait = self.collecte.declarer("Un fait.")
        with self.assertRaises(ValueError):
            self.collecte.documenter(fait["fait_id"], "")

    def test_une_information_manquante_ne_se_documente_pas(self):
        manquant = self.collecte.nommer_manquant("Date exacte de la mise en demeure")
        with self.assertRaises(ValueError):
            self.collecte.documenter(manquant["fait_id"], self._piece("x.txt"))

    def test_informations_manquantes_nommees(self):
        self.collecte.declarer("Un fait.")
        self.collecte.nommer_manquant("Date de signature", pourquoi="non fournie")
        self.assertEqual(len(self.collecte.manquants), 1)
        resume = self.collecte.resume()
        self.assertTrue(resume["informations_manquantes"])
        self.assertEqual(resume["informations_manquantes"][0]["libelle"], "Date de signature")
        self.assertIn("non fournie", resume["informations_manquantes"][0]["pourquoi"])

    def test_resume_compte_tous_les_etats(self):
        self.collecte.declarer("Fait déclaré.")
        self.collecte.nommer_manquant("Élément absent")
        resume = self.collecte.resume()
        for etat in ("DECLARE_PAR_L_UTILISATEUR", "DOCUMENTE", "A_CONFIRMER", "MANQUANT"):
            self.assertIn(etat, resume["tous_les_etats_nommes"])

    def test_ecarter_conserve_la_trace(self):
        fait = self.collecte.declarer("Déclaration retirée.")
        self.collecte.ecarter(fait["fait_id"], "l'utilisateur s'est rétracté")
        self.assertEqual(self.collecte.tous(), [])
        self.assertEqual(len(self.collecte.tous(inclure_ecartes=True)), 1)
        self.assertTrue(self.collecte.tous(inclure_ecartes=True)[0]["ecarte"])

    def test_etat_inconnu_refuse(self):
        with self.assertRaises(ValueError):
            self.collecte.par_etat("PEUT_ETRE")

    def test_reconstruction_preserve_les_statuts(self):
        chemin = self._piece("quittance.txt")
        fait = self.collecte.declarer("Loyer payé.")
        self.collecte.documenter(fait["fait_id"], chemin)
        self.collecte.nommer_manquant("Montant exact")
        reconstruit = Faits.depuis_dict(self.collecte.to_dict())
        self.assertEqual(len(reconstruit.documentes), 1)
        self.assertEqual(len(reconstruit.manquants), 1)
        self.assertEqual(reconstruit.documentes[0]["empreinte_piece"],
                         self.collecte.documentes[0]["empreinte_piece"])

    def test_empreinte_fichier_absente(self):
        with self.assertRaises(FileNotFoundError):
            empreinte_fichier(os.path.join(self.dossier, "absent.bin"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
