# -*- coding: utf-8 -*-
"""Génération de courriers : utilisable, sans invention, sans envoi.

Ce que ces tests protègent :

1. **Le PDF est réellement produit.** Il ne l'était plus : `multi_cell` laissait
   le curseur au bord droit et fpdf2 levait « Not enough horizontal space ».
   Tous les courriers échouaient silencieusement à l'export PDF.
2. **Rien n'est inventé.** Nom, adresse, destinataire, pièces : fournis par la
   personne ou signalés comme manquants. Jamais déduits.
3. **Un brouillon n'est pas un document final.** La mention reste en tête, l'envoi
   est impossible, et les champs incomplets restent visibles.
4. **Le fondement n'est cité que s'il est vérifié.** Une fiche `OCR_AUTO` ou
   `PARTIELLEMENT_VERIFIE` n'entre pas dans un courrier.

Ces tests sont techniques. Ils ne remplacent pas une relecture juridique humaine.
"""

import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from core import documents, service  # noqa: E402

DOSSIERS = []


def _fermer(identifiant):
    shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)


def _dossier(prefixe):
    identifiant = "%s_%d" % (prefixe, len(DOSSIERS) + 1)
    _fermer(identifiant)
    DOSSIERS.append(identifiant)
    return identifiant


def _mener(dossier_id, demande="Mon bailleur garde ma caution depuis deux mois."):
    """Mène la conversation jusqu'au bout. Retourne la réponse finale."""
    reponse = service.ouvrir(dossier_id, demande)
    donnees = reponse.get("data") or {}
    for _ in range(6):
        if donnees.get("etape") == "reponse":
            return donnees
        cles = [q["cle"] for q in (donnees.get("questions") or [])]
        # Une fiche sans question ouvre quand même un tour de clarification :
        # c'est `repondre` avec un dictionnaire vide qui clôt l'analyse.
        donnees = service.repondre(dossier_id, {c: "oui" for c in cles}).get("data") or {}
    return donnees


class TestExportPdf(unittest.TestCase):
    """L'export PDF doit produire un fichier, pas une erreur déclarée."""

    def test_le_pdf_est_produit(self):
        dossier = _dossier("PDF")
        resultat = documents.generer_brouillon(
            dossier, "reclamation",
            {"objet": "Test", "faits": ["Un fait"], "demande": "Une demande",
             "adresse_retour": "Awa KONE, Abidjan", "pieces": "Contrat"})
        self.assertTrue(resultat["pdf"]["tente"])
        self.assertTrue(resultat["pdf"]["ok"], resultat["pdf"].get("erreur"))
        self.assertTrue(os.path.isfile(resultat["fichier_pdf"]))
        self.assertGreater(resultat["pdf"]["octets"], 500)

    def test_un_texte_long_ne_casse_pas_l_export(self):
        """Le défaut venait de l'état du curseur, pas de la longueur : on vérifie
        les deux (ligne longue sans espace + texte multi-pages)."""
        dossier = _dossier("PDF_LONG")
        resultat = documents.generer_brouillon(
            dossier, "reclamation",
            {"objet": "A" * 300, "faits": ["x" * 400] * 30, "demande": "Demande",
             "adresse_retour": "Adresse", "pieces": "Pièce"})
        self.assertTrue(resultat["pdf"]["ok"], resultat["pdf"].get("erreur"))


class TestChampsUtilisateur(unittest.TestCase):
    """Ce que seul l'utilisateur peut fournir."""

    def test_les_trois_champs_sont_reclames(self):
        dossier = _dossier("CHAMPS")
        _mener(dossier)
        reponse = service.rediger_courrier(dossier)
        self.assertTrue(reponse["ok"])
        manquants = [c["champ"] for c in reponse["data"]["champs_a_completer"]]
        self.assertEqual(manquants, ["expediteur", "destinataire", "pieces"])
        for champ in reponse["data"]["champs_a_completer"]:
            self.assertTrue(champ["question"], champ)
            self.assertTrue(champ["exemple"], champ)

    def test_un_champ_inconnu_est_refuse(self):
        dossier = _dossier("CHAMP_INCONNU")
        _mener(dossier)
        reponse = service.rediger_courrier(dossier, {"numero_de_compte": "123"})
        self.assertFalse(reponse["ok"])
        self.assertEqual(reponse["erreur"]["code"], "ENTREE_INVALIDE")

    def test_une_valeur_vide_est_refusee(self):
        dossier = _dossier("CHAMP_VIDE")
        _mener(dossier)
        reponse = service.rediger_courrier(dossier, {"expediteur": "   "})
        self.assertFalse(reponse["ok"])
        self.assertEqual(reponse["erreur"]["code"], "ENTREE_INVALIDE")

    def test_une_valeur_non_textuelle_est_refusee(self):
        dossier = _dossier("CHAMP_TYPE")
        _mener(dossier)
        reponse = service.rediger_courrier(dossier, {"expediteur": 42})
        self.assertFalse(reponse["ok"])

    def test_le_placeholder_compte_comme_manquant(self):
        """Un champ rempli de « [À COMPLÉTER …] » n'est pas une information."""
        manquants = documents.champs_manquants(
            {"adresse_retour": "[À COMPLÉTER : vos nom, prénom et adresse]"})
        self.assertIn("expediteur", [c["champ"] for c in manquants])


class TestCourrierComplet(unittest.TestCase):
    """Fourni, le courrier ne contient plus aucun trou."""

    def test_les_informations_fournies_apparaissent(self):
        dossier = _dossier("COMPLET")
        _mener(dossier)
        reponse = service.rediger_courrier(dossier, {
            "expediteur": "Awa KONE, 12 rue des Jardins, Cocody, Abidjan",
            "destinataire": "Monsieur le Bailleur, 5 rue du Marche, Yopougon",
            "pieces": "Contrat de bail\nRecu du depot de garantie"})
        self.assertTrue(reponse["ok"])
        donnees = reponse["data"]
        self.assertEqual(donnees["champs_a_completer"], [])
        texte = donnees["texte"]
        self.assertIn("12 rue des Jardins", texte)
        self.assertIn("Monsieur le Bailleur", texte)
        self.assertIn("Contrat de bail", texte)
        self.assertNotIn("COMPLÉTER", texte)
        self.assertTrue(donnees["genere"]["pdf"]["ok"])

    def test_la_mention_brouillon_reste_en_tete(self):
        dossier = _dossier("MENTION")
        _mener(dossier)
        texte = service.rediger_courrier(dossier, {"expediteur": "Awa KONE, Abidjan"})["data"]["texte"]
        self.assertTrue(texte.startswith(documents.MENTION_BROUILLON))
        self.assertIn("n'est ni avocat", texte)

    def test_aucune_fonction_d_envoi_n_est_annoncee(self):
        dossier = _dossier("ENVOI")
        _mener(dossier)
        genere = service.rediger_courrier(dossier)["data"]["genere"]
        self.assertIn("AUCUN", genere["envoi"])


class TestFondement(unittest.TestCase):
    """Le fondement juridique suit le statut de la référence."""

    def test_une_reference_verifiee_est_citee(self):
        dossier = _dossier("FONDEMENT_OK")
        _mener(dossier)  # dépôt de garantie : 2019-576, VERIFIE
        donnees = service.rediger_courrier(dossier)["data"]
        self.assertIsNotNone(donnees["fondement"])
        self.assertIn("article", donnees["fondement"])
        self.assertIn("2019-576", donnees["fondement"])
        self.assertIn("Fondement :", donnees["texte"])

    def test_une_reference_non_verifiee_n_est_pas_citee(self):
        """Un texte OCR ne doit jamais servir de fondement à un courrier."""
        dossier = _dossier("FONDEMENT_OCR")
        _mener(dossier, "On m'a volé mon téléphone dans la rue.")
        donnees = service.rediger_courrier(dossier)["data"]
        self.assertIsNone(donnees["fondement"])
        self.assertNotIn("Fondement :", donnees["texte"])

    def test_un_modele_generique_n_a_pas_de_fondement(self):
        dossier = _dossier("GENERIQUE")
        texte = documents.rendre_texte(
            dossier, "demande_amiable",
            {"objet": "Objet", "faits": ["Fait"], "demande": "Demande",
             "adresse_retour": "Awa KONE, Abidjan", "pieces": "Pièce"})
        self.assertNotIn("Fondement :", texte)
        self.assertNotIn("COMPLÉTER", texte)


class TestGardeFous(unittest.TestCase):
    """On ne rédige pas un courrier n'importe quand, ni pour n'importe qui."""

    def test_un_dossier_inconnu_est_refuse(self):
        reponse = service.rediger_courrier("DOSSIER_QUI_N_EXISTE_PAS")
        self.assertFalse(reponse["ok"])
        self.assertIn(reponse["erreur"]["code"], ("ANALYSE_INCOMPLETE", "DOSSIER_INCONNU"))

    def test_avant_l_analyse_le_courrier_est_refuse(self):
        dossier = _dossier("AVANT")
        service.ouvrir(dossier, "Mon bailleur garde ma caution depuis deux mois.")
        reponse = service.rediger_courrier(dossier, {"expediteur": "Awa KONE, Abidjan"})
        self.assertFalse(reponse["ok"])
        self.assertEqual(reponse["erreur"]["code"], "ANALYSE_INCOMPLETE")

    def test_la_traversee_de_chemin_est_refusee(self):
        for mauvais in ("../secret", "/etc/passwd", "a/b"):
            reponse = service.rediger_courrier(mauvais)
            self.assertFalse(reponse["ok"], mauvais)
            self.assertEqual(reponse["erreur"]["code"], "DOSSIER_INVALIDE", mauvais)

    def test_hors_catalogue_aucun_courrier(self):
        dossier = _dossier("HORS")
        _mener(dossier, "Quelle est la recette du gateau au chocolat ?")
        reponse = service.rediger_courrier(dossier, {"expediteur": "Awa KONE, Abidjan"})
        self.assertFalse(reponse["ok"])
        self.assertEqual(reponse["erreur"]["code"], "ANALYSE_INCOMPLETE")


def tearDownModule():
    for identifiant in DOSSIERS:
        _fermer(identifiant)


if __name__ == "__main__":
    unittest.main(verbosity=2)
