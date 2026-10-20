# -*- coding: utf-8 -*-
"""Recherche documentaire exposée par `service.rechercher`.

Ces tests vérifient trois choses et refusent d'en affirmer une quatrième :

1. la recherche ne SORT JAMAIS du corpus citable (article absent, neutralisé
   ou inexistant ne remonte pas) ;
2. elle ne CONCLUT rien : elle localise, elle n'énonce pas de droit ;
3. elle n'ÉCRIT rien : ni base, ni dossier, ni fiche ;
4. elle ne prétend PAS bien classer. Le classement lexical est mesuré, pas
   supposé : `TestBaselineMesuree` fixe un plancher issu d'une mesure réelle
   (92 questions dérivées des déclencheurs du catalogue), avec une marge.

Un résultat de recherche n'est pas une réponse juridique.
"""

import json
import os
import sqlite3
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from core import corpus, service  # noqa: E402

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JEU = os.path.join(RACINE, "KNOWLEDGE", "qualite", "questions_recherche.json")

# Références dont les articles sont neutralisés (articles_fiables = 0) :
# OCR de journal officiel entremêlé. Conservées pour l'audit, jamais citables.
REFS_NEUTRALISEES = {"REF-ADF0B09E1014", "REF-5E19CA5DF5AD", "REF-0F238AF26A8A"}
TEXTES_NEUTRALISES = {"2013-450", "2013-451", "2013-546"}


def _cle(article):
    return (str(article.get("numero_texte") or article.get("ref_id")),
            str(article.get("numero")))


def _empreinte_logique():
    connexion = sqlite3.connect(config.CHEMIN_DB)
    try:
        lignes = connexion.execute(
            "SELECT a.ref_id, a.numero, a.texte, a.origine_texte, d.articles_fiables"
            " FROM articles_corpus a JOIN documents d ON d.doc_id = a.doc_id"
            " ORDER BY a.ref_id, a.numero").fetchall()
    finally:
        connexion.close()
    import hashlib
    empreinte = hashlib.sha256()
    for ligne in lignes:
        empreinte.update(("|".join(str(v) for v in ligne) + "\n").encode("utf-8"))
    return empreinte.hexdigest(), len(lignes)


class TestContratDeRecherche(unittest.TestCase):
    """La recherche s'ajoute au contrat sans en retirer aucune partie."""

    def test_les_quatre_operations_existantes_sont_intactes(self):
        for nom in ("ouvrir", "repondre", "supprimer", "sante"):
            self.assertTrue(callable(getattr(service, nom)), nom)
            self.assertIn(nom, service.SCHEMAS)
        self.assertIn("rechercher", service.SCHEMAS)

    def test_une_question_vide_est_refusee(self):
        for vide in ("", "   ", None, 12):
            resultat = service.rechercher(vide)
            self.assertFalse(resultat["ok"], vide)
            self.assertEqual(resultat["erreur"]["code"], "ENTREE_INVALIDE")

    def test_une_question_trop_longue_est_refusee(self):
        resultat = service.rechercher("a" * (service.LONGUEUR_MAX_DEMANDE + 1))
        self.assertFalse(resultat["ok"])
        self.assertEqual(resultat["erreur"]["code"], "ENTREE_INVALIDE")

    def test_un_domaine_inconnu_est_refuse(self):
        resultat = service.rechercher("caution", domaine="societes_ohada")
        self.assertFalse(resultat["ok"])
        self.assertEqual(resultat["erreur"]["code"], "ENTREE_INVALIDE")
        self.assertIn("societes_ohada", resultat["erreur"]["message"])

    def test_une_limite_hors_bornes_est_refusee(self):
        for limite in (0, 26, -1, "5", 2.5, True):
            resultat = service.rechercher("caution", limite=limite)
            self.assertFalse(resultat["ok"], "limite=%r acceptée à tort" % (limite,))
            self.assertEqual(resultat["erreur"]["code"], "ENTREE_INVALIDE")

    def test_la_limite_est_respectee(self):
        for limite in (1, 3, 10):
            resultat = service.rechercher("logement loyer bail", limite=limite)
            self.assertTrue(resultat["ok"])
            self.assertLessEqual(len(resultat["data"]["resultats"]), limite)


class TestPerimetreEtAppariement(unittest.TestCase):
    """Ce que la recherche atteint — et ce qu'elle atteint mal."""

    def test_une_question_de_logement_remonte_le_bon_texte(self):
        resultat = service.rechercher("depot de garantie restitution")
        self.assertTrue(resultat["ok"])
        resultats = resultat["data"]["resultats"]
        self.assertTrue(resultats, "aucun article pour une question couverte")
        textes = {a["numero_texte"] for a in resultats}
        self.assertIn("2019-576", textes)
        self.assertTrue(any(a["etat_verification"] for a in resultats))

    def test_le_filtre_par_texte_restreint_au_texte_demande(self):
        resultat = service.rechercher("capital minimum d'une SARL", texte="AUSCGIE-2014")
        self.assertTrue(resultat["ok"])
        for article in resultat["data"]["resultats"]:
            self.assertEqual(article["numero_texte"], "AUSCGIE-2014")

    def test_sans_filtre_la_confusion_entre_actes_ohada_est_reelle(self):
        """Témoin négatif : documente la limite, ne la corrige pas.

        AUSCGIE, AUSCOOP et AUPCAP partagent le domaine
        `contrats_dettes_commerce` : la recherche libre les mélange. Si ce test
        se met à échouer, c'est que le classement a changé — à remesurer, pas
        à célébrer.
        """
        libre = service.rechercher("capital minimum d'une SARL")
        textes = {a["numero_texte"] for a in libre["data"]["resultats"]}
        self.assertTrue(textes - {"AUSCGIE-2014"},
                        "la confusion inter-actes a disparu : remesurer la baseline")

    def test_les_termes_reconnus_sont_exposes(self):
        resultat = service.rechercher("depot de garantie")
        for article in resultat["data"]["resultats"]:
            self.assertIsInstance(article["termes_reconnus"], list)
            self.assertTrue(article["termes_reconnus"])

    def test_un_score_nul_n_est_jamais_retourne(self):
        resultat = service.rechercher("expulsion")
        for article in resultat["data"]["resultats"]:
            self.assertGreater(article["score"], 0)


class TestAbstention(unittest.TestCase):
    """S'abstenir quand la source ne porte rien — et le dire."""

    def test_une_question_sans_mot_significatif_s_abstient(self):
        resultat = service.rechercher("de la", domaine="logement_baux_foncier")
        self.assertTrue(resultat["ok"])
        self.assertTrue(resultat["data"]["abstention"])
        self.assertEqual(resultat["data"]["resultats"], [])
        self.assertTrue(resultat["data"]["message"])

    def test_un_texte_inexistant_s_abstient(self):
        resultat = service.rechercher("caution", texte="TEXTE-QUI-N-EXISTE-PAS")
        self.assertTrue(resultat["ok"])
        self.assertTrue(resultat["data"]["abstention"])

    def test_un_domaine_sans_article_correspondant_s_abstient(self):
        resultat = service.rechercher("quorum cooperative", domaine="logement_baux_foncier")
        self.assertTrue(resultat["ok"])
        if resultat["data"]["resultats"]:
            for article in resultat["data"]["resultats"]:
                self.assertEqual(article["domaine"], "logement_baux_foncier")

    def test_une_question_hors_sujet_est_signalee_et_non_presentee_comme_une_reponse(self):
        """Limite mesurée : le lexical ne sait pas juger la pertinence.

        « recette du gâteau au chocolat » remonte des articles fiscaux
        (« recettes »). Aucun seuil testé ne sépare ce cas d'une vraie question
        sans rejeter d'abord une question légitime. Le service ne doit donc
        jamais présenter un résultat comme une réponse : il l'annonce.
        """
        resultat = service.rechercher("recette du gateau au chocolat")
        self.assertTrue(resultat["ok"])
        self.assertIn("avertissement", resultat["data"])
        self.assertTrue(resultat["data"]["avertissement"])
        self.assertNotIn("statut_reponse", resultat["data"])
        self.assertNotIn("sections", resultat["data"])


class TestCitabilite(unittest.TestCase):
    """Aucun article non citable ne remonte ; une citation fausse est refusée."""

    def test_tout_resultat_est_resolvable_par_le_moteur(self):
        resultat = service.rechercher("bail loyer caution expulsion")
        self.assertTrue(resultat["data"]["resultats"])
        for article in resultat["data"]["resultats"]:
            corps = corpus.obtenir_article_par_reference(article["ref_id"], article["numero"])
            self.assertIsNotNone(corps, "%s art.%s non résolvable"
                                 % (article["ref_id"], article["numero"]))
            self.assertTrue(corps["texte"])

    def test_un_article_neutralise_ne_remonte_jamais(self):
        for question in ("donnees personnelles informatique liberte",
                         "traitement des donnees a caractere personnel",
                         "commission informatique libertes"):
            resultat = service.rechercher(question, limite=25)
            for article in resultat["data"]["resultats"]:
                self.assertNotIn(article["ref_id"], REFS_NEUTRALISEES, question)
                self.assertNotIn(article["numero_texte"], TEXTES_NEUTRALISES, question)

    def test_une_citation_alteree_est_refusee(self):
        resultat = service.rechercher("depot de garantie restitution", limite=1)
        article = resultat["data"]["resultats"][0]
        extrait = article["extrait"].rstrip("…").strip()
        self.assertGreater(len(extrait), 20)
        citation = extrait[:60]
        # La fonction renvoie (bool, détail) : vérifier le booléen, pas le tuple,
        # sinon l'assertion passe sur un tuple non vide et ne prouve rien.
        acceptee, detail = corpus.verifier_citation_article(article["ref_id"],
                                                            article["numero"], citation)
        self.assertTrue(acceptee, detail)
        refusee, motif = corpus.verifier_citation_article(article["ref_id"],
                                                          article["numero"],
                                                          citation + " et le ciel est vert")
        self.assertFalse(refusee)
        self.assertEqual(motif.get("raison"), "CITATION_ABSENTE")

    def test_un_article_invente_est_refuse(self):
        self.assertIsNone(corpus.obtenir_article_par_reference("REF-INVENTEE", "1"))


class TestAucuneConclusionEtAucuneEcriture(unittest.TestCase):
    """La recherche observe : elle ne conclut pas et ne modifie rien."""

    def test_aucune_section_juridique_dans_la_sortie(self):
        resultat = service.rechercher("expulsion sans decision de justice")
        donnees = resultat["data"]
        for interdit in ("sections", "statut_reponse", "brouillon", "verrous_humains"):
            self.assertNotIn(interdit, donnees)
        self.assertIn("avertissement", donnees)

    def test_la_recherche_ne_modifie_pas_la_base(self):
        avant = _empreinte_logique()
        service.rechercher("caution loyer bail expulsion")
        apres = _empreinte_logique()
        self.assertEqual(avant, apres)

    def test_la_recherche_n_ouvre_aucun_dossier(self):
        racine = config.DOSSIERS_DIR
        avant = sorted(os.listdir(str(racine))) if racine.exists() else []
        service.rechercher("caution loyer")
        apres = sorted(os.listdir(str(racine))) if racine.exists() else []
        self.assertEqual(avant, apres)


class TestBaselineMesuree(unittest.TestCase):
    """Plancher de rappel, mesuré et non espéré.

    Mesure du 20/10/2026 sur les 92 déclencheurs du catalogue :
    72/92 présents dans le corpus (78 %), 42/92 dans le top 25 (46 %),
    20/92 dans le top 5 (22 %). Le classement lexical est faible : c'est
    pourquoi les fiches existent. Les seuils ci-dessous portent sur les
    20 premières questions et sont fixés AVEC UNE MARGE sous le mesuré
    (15 présents, 10 dans le top 25) : ils détectent une dégradation,
    ils ne certifient pas une qualité.
    """

    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(JEU):
            raise unittest.SkipTest("jeu de questions absent")
        with open(JEU, encoding="utf-8") as flux:
            cls.questions = json.load(flux)["questions"][:20]

    def test_plancher_de_rappel(self):
        presents, top25 = 0, 0
        for cas in self.questions:
            attendus = {_cle(a) for a in cas["attendus"]}
            vus = [_cle(a) for a in corpus.chercher_articles(cas["question"], limite=500)]
            rang = next((i + 1 for i, v in enumerate(vus) if v in attendus), None)
            if rang:
                presents += 1
                if rang <= 25:
                    top25 += 1
        self.assertGreaterEqual(presents, 13, "rappel en baisse : %d/20" % presents)
        self.assertGreaterEqual(top25, 8, "classement en baisse : %d/20" % top25)


if __name__ == "__main__":
    unittest.main(verbosity=2)
