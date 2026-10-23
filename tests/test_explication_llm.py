# -*- coding: utf-8 -*-
"""Explication en langage simple des articles cités (après la citation).

Aucun appel réseau : le fournisseur est un faux objet local. On vérifie que
l'explication n'ajoute rien au droit (articles, nombres, promesses), qu'elle
n'existe pas sans fournisseur ni pendant un incident, et qu'elle arrive bien
dans la réponse finale d'une vraie consultation.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
import uuid

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import config  # noqa: E402
from core import incident_llm, llm, llm_budget  # noqa: E402
from core.conversation import Conversation  # noqa: E402

FICHE = {"article": 416, "numero_texte": "2019-576", "titre": "Dépôt de garantie (caution)",
         "citation": "Le contrat de location peut prévoir un dépôt de garantie à la charge du "
                     "locataire qui ne peut excéder deux mois de loyer pour garantir l'exécution "
                     "de ses obligations en fin de contrat."}
DEMARCHES = ["Réunir le bail, la preuve du dépôt versé et l'état des lieux"]
RECIT = "Mon bailleur refuse de me rendre ma caution depuis que j'ai quitté le logement."


class Faux(object):
    """Faux fournisseur : renvoie un texte fixé, compte les appels."""
    nom = "deepseek"

    def __init__(self, reponses):
        self.reponses = list(reponses)
        self.appels = []
        self.derniere_consommation = {"entree": 100, "sortie": 50}

    def completer(self, systeme, message, delai=None, max_tokens=800):
        self.appels.append((systeme, message))
        r = self.reponses.pop(0) if len(self.reponses) > 1 else self.reponses[0]
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, str) else json.dumps(r, ensure_ascii=False)


class Base(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.mkdtemp(prefix="explication-")
        os.environ[incident_llm.NOM_VARIABLE_FICHIER] = os.path.join(self.dossier, "incident.json")
        os.environ[llm_budget.NOM_VARIABLE_REGISTRE] = os.path.join(self.dossier, "registre.json")

    def tearDown(self):
        os.environ.pop(incident_llm.NOM_VARIABLE_FICHIER, None)
        os.environ.pop(llm_budget.NOM_VARIABLE_REGISTRE, None)
        shutil.rmtree(self.dossier, ignore_errors=True)


class Validation(Base):
    def valider(self, brut):
        return llm.valider_explication(brut, RECIT, [("S'agit-il d'un bail ?", "oui")], [FICHE], DEMARCHES)

    def test_explication_fidele_retenue(self):
        retenu, rejets = self.valider({
            "explications": [{"article": "416", "en_clair": "Le bailleur ne peut pas demander plus de deux mois de loyer comme caution."}],
            "pour_vous": "Si ce que vous décrivez est exact, la caution sert à couvrir les dégâts ou les loyers impayés.",
            "etapes": [{"numero": 1, "en_clair": "Rassemblez votre bail et la preuve que vous avez payé la caution."}]})
        self.assertEqual(rejets, [])
        self.assertEqual(retenu["explications"][0]["article"], "416")
        self.assertTrue(retenu["pour_vous"])
        self.assertEqual(retenu["etapes"][0]["numero"], 1)

    def test_nombre_invente_rejete(self):
        retenu, rejets = self.valider({"explications": [
            {"article": "416", "en_clair": "Le bailleur doit vous rendre la caution sous trente jours."}]})
        self.assertEqual(retenu["explications"], [])
        self.assertIn("nombre absent", rejets[0]["raison"])

    def test_article_non_retenu_rejete(self):
        retenu, rejets = self.valider({"pour_vous": "Selon l'article 420, vous pourriez saisir le juge."})
        self.assertIsNone(retenu["pour_vous"])
        self.assertTrue(any("nombre absent" in r["raison"] or "article non retenu" in r["raison"] for r in rejets))

    def test_article_inconnu_dans_la_liste_ignore(self):
        retenu, rejets = self.valider({"explications": [{"article": "999", "en_clair": "Texte."}]})
        self.assertEqual(retenu["explications"], [])
        self.assertEqual(rejets[0]["raison"], "article non retenu")

    def test_promesse_rejetee(self):
        retenu, rejets = self.valider({"pour_vous": "Vous allez gagner, c'est garanti."})
        self.assertIsNone(retenu["pour_vous"])
        self.assertEqual(rejets[0]["raison"], "promesse de résultat")

    def test_etape_inventee_rejetee(self):
        retenu, rejets = self.valider({"etapes": [{"numero": 4, "en_clair": "Allez au tribunal."}]})
        self.assertEqual(retenu["etapes"], [])
        self.assertEqual(rejets[0]["raison"], "démarche inconnue")

    def test_trop_long_rejete(self):
        retenu, _ = self.valider({"explications": [{"article": "416", "en_clair": "mot " * 400}]})
        self.assertEqual(retenu["explications"], [])


class Expliquer(Base):
    def test_sans_fournisseur_rien_n_est_produit(self):
        rapport = llm.expliquer(RECIT, [], [FICHE], DEMARCHES, fournisseur=None)
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertEqual(rapport["explications"], [])

    def test_incident_ouvert_aucun_appel(self):
        incident_llm.declarer("deepseek", "Insufficient Balance", 402)
        faux = Faux([{"explications": []}])
        rapport = llm.expliquer(RECIT, [], [FICHE], DEMARCHES, fournisseur=faux)
        self.assertEqual(faux.appels, [])
        self.assertEqual(rapport["mode"], "deterministe")

    def test_reponse_illisible_repli(self):
        faux = Faux(["pas du json"])
        rapport = llm.expliquer(RECIT, [], [FICHE], DEMARCHES, fournisseur=faux)
        self.assertEqual(rapport["mode"], "deterministe")
        self.assertIsNotNone(rapport["erreur"])

    def test_coordonnees_masquees_avant_envoi(self):
        faux = Faux([{"explications": []}])
        llm.expliquer("Appelez-moi au 07 07 07 07 07, moi@exemple.ci", [], [FICHE], DEMARCHES, fournisseur=faux)
        envoye = faux.appels[0][1]
        self.assertNotIn("07 07 07 07 07", envoye)
        self.assertNotIn("moi@exemple.ci", envoye)
        self.assertIn("« %s »" % FICHE["citation"], envoye)

    def test_explication_valide(self):
        faux = Faux([{"explications": [{"article": "416", "en_clair": "La caution ne peut pas dépasser deux mois de loyer."}],
                      "pour_vous": "Si ce que vous décrivez est exact, le bailleur devrait justifier toute retenue."}])
        rapport = llm.expliquer(RECIT, [], [FICHE], DEMARCHES, fournisseur=faux)
        self.assertEqual(rapport["mode"], "llm")
        self.assertEqual(len(rapport["explications"]), 1)


class ConsultationComplete(Base):
    """Vraie conversation (catalogue réel) : l'explication arrive dans la réponse."""

    def jusqu_au_resultat(self, conv):
        etape = conv.demarrer(self.identifiant, RECIT)
        for _ in range(5):
            if etape["etape"] != "clarification":
                break
            etape = conv.repondre(self.identifiant, {q["cle"]: "oui" for q in etape["questions"]})
        self.assertEqual(etape["etape"], "reponse", etape)
        return etape

    def setUp(self):
        super().setUp()
        self.identifiant = "TEST_EXPLICATION_" + uuid.uuid4().hex[:10]

    def tearDown(self):
        shutil.rmtree(str(config.dossier_utilisateur(self.identifiant)), ignore_errors=True)
        super().tearDown()

    def test_section_explication_dans_la_reponse(self):
        comprehension = {"fiches": [], "suggestions": [], "resume": None}

        class FauxConversation(Faux):
            def completer(self, systeme, message, delai=None, max_tokens=800):
                self.appels.append((systeme, message))
                if systeme == llm._SYSTEME_EXPLICATION:
                    return json.dumps({
                        "explications": [{"article": "416", "en_clair": "La caution ne peut pas dépasser deux mois de loyer."}],
                        "pour_vous": "Si ce que vous décrivez est exact, le bailleur devrait vous rendre la caution ou justifier une retenue."})
                return json.dumps(comprehension)

        faux = FauxConversation([None])
        fin = self.jusqu_au_resultat(Conversation(fournisseur_langage=faux))
        sections = fin["reponse"]["sections"]
        explication = sections["7_explication"]
        if any(str(d["article"]) == "416" for d in sections["2_droit"]):
            self.assertEqual(explication["mode"], "llm")
            self.assertTrue(explication["explications"])
        self.assertIn("Seul le texte de loi fait foi", explication["note"])
        # Les citations restent celles du catalogue, inchangées.
        for d in sections["2_droit"]:
            self.assertNotIn("deux mois de loyer comme caution", d["citation"])

    def test_sans_fournisseur_section_deterministe(self):
        fin = self.jusqu_au_resultat(Conversation())
        self.assertEqual(fin["reponse"]["sections"]["7_explication"]["mode"], "deterministe")


if __name__ == "__main__":
    unittest.main()
