# -*- coding: utf-8 -*-
"""Cas juridiques — vérification des cinq exigences sur le corpus réel.

Sept situations du domaine logement / baux / foncier. Pour chacune, cinq
contrôles, exactement comme demandé :

  1. l'agent cite un article RÉELLEMENT présent dans le corpus ;
  2. la citation correspond EXACTEMENT au texte indexé ;
  3. l'explication ne dépasse pas ce que la source permet d'affirmer ;
  4. les incertitudes et modifications possibles sont SIGNALÉES ;
  5. l'agent REFUSE de conclure si les sources sont insuffisantes.

Aucun contenu de droit n'est inventé ici : chaque cas s'appuie sur le texte des
articles réellement indexés, lu dans les PDF officiels téléchargés.
"""

import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from agent import MonRecoursCI  # noqa: E402
from core import analyse as A  # noqa: E402
from core import base, corpus  # noqa: E402

DOMAINE = "logement_baux_foncier"

# numero_texte, état de la référence, article, énoncé fidèle, citation exacte,
# incertitude obligatoire (l'article vient d'un OCR non recoupé).
CAS = (
    {
        "nom": "caution — dépôt de garantie plafonné",
        "numero_texte": "2019-576", "etat": "VERIFIE", "article": "416",
        "enonce": ("Le contrat de location peut prévoir un dépôt de garantie à la charge du "
                   "locataire, qui ne peut excéder deux mois de loyer."),
        "citation": ("Le contrat de location peut prévoir un dépôt de garantie à la charge "
                     "du locataire qui ne peut excéder deux mois de loyer"),
        "incertitude_obligatoire": False,
    },
    {
        "nom": "loyers — avance plafonnée",
        "numero_texte": "2019-576", "etat": "VERIFIE", "article": "415",
        "enonce": ("Le bailleur ne peut exiger le paiement de plus de deux mois de loyers "
                   "d'avance au candidat à la location."),
        "citation": ("Le bailleur ne peut exiger le paiement de plus de deux mois de loyers "
                     "d'avance"),
        "incertitude_obligatoire": False,
    },
    {
        "nom": "loyers — révision triennale",
        "numero_texte": "2019-576", "etat": "VERIFIE", "article": "423",
        "enonce": "Le loyer peut être révisé à la hausse ou à la baisse, tous les trois ans.",
        "citation": ("Le loyer peut être révisé à la hausse ou à la baisse, tous les trois ans."),
        "incertitude_obligatoire": False,
    },
    {
        "nom": "bail — forme écrite et enregistrement",
        "numero_texte": "2019-576", "etat": "VERIFIE", "article": "414",
        "enonce": ("Le contrat de bail à usage d'habitation est écrit et fait obligatoirement "
                   "l'objet d'un enregistrement auprès de l'administration fiscale."),
        "citation": "Le contrat de bail à usage d'habitation est écrit.",
        "incertitude_obligatoire": False,
    },
    {
        "nom": "congé — reprise par le bailleur",
        "numero_texte": "2019-576", "etat": "VERIFIE", "article": "440",
        "enonce": ("Le bailleur qui souhaite reprendre son immeuble doit donner un congé au "
                   "locataire au moins trois mois avant la date de reprise indiquée."),
        "citation": ("doit donner un congé au locataire, au moins trois mois avant la date de "
                     "reprise indiquée par le bailleur"),
        "incertitude_obligatoire": False,
    },
    {
        "nom": "résiliation — lettre écrite et motivée",
        "numero_texte": "2019-576", "etat": "VERIFIE", "article": "443",
        "enonce": ("La lettre de demande de résiliation du contrat de bail doit être écrite, "
                   "motivée, et accompagnée le cas échéant de pièces justificatives."),
        "citation": ("La lettre de demande de résiliation du contrat de bail doit être écrite, "
                     "motivée"),
        "incertitude_obligatoire": False,
    },
    {
        "nom": "expulsion — juge des référés",
        "numero_texte": "2019-576", "etat": "VERIFIE", "article": "445",
        "enonce": ("Lorsque le locataire manque à ses obligations contractuelles, le bailleur "
                   "peut demander son expulsion forcée devant le juge des référés, après la "
                   "transmission de la lettre de demande de résiliation."),
        "citation": ("le bailleur peut demander son expulsion forcée devant le Juge des référés, "
                     "après la transmission de la lettre de demande de résiliation"),
        "incertitude_obligatoire": False,
    },
    {
        "nom": "propriété foncière — domaine public urbain",
        "numero_texte": "2020-624", "etat": "VERIFIE", "article": "181",
        "enonce": "Le domaine public urbain est inaliénable et imprescriptible.",
        "citation": "Le domaine public urbain est inaliénable et imprescriptible.",
        "incertitude_obligatoire": False,
    },
    {
        "nom": "conflit de terrain — expropriation",
        "numero_texte": "2020-624", "etat": "VERIFIE", "article": "238",
        "enonce": ("L'expropriation pour cause d'utilité publique est la procédure par laquelle "
                   "la puissance publique contraint une personne à la cession forcée de ses "
                   "droits de propriété sur un bien immobilier, moyennant une indemnité."),
        "citation": ("L'expropriation pour cause d'utilité publique est la procédure par laquelle "
                     "la puissance publique contraint"),
        "incertitude_obligatoire": False,
    },
    {
        "nom": "aménagement foncier — réserves foncières",
        "numero_texte": "2020-624", "etat": "VERIFIE", "article": "69",
        "enonce": "Tout aménagement foncier est précédé par la constitution de réserves foncières.",
        "citation": "Tout aménagement foncier est précédé par la constitution de réserves foncières.",
        "incertitude_obligatoire": False,
    },
    {
        "nom": "foncier rural — définition (texte OCR non recoupé)",
        "numero_texte": "98-750", "etat": "PARTIELLEMENT_VERIFIE", "article": "1",
        "enonce": ("Le domaine foncier rural est constitué par l'ensemble des terres mises en "
                   "valeur ou non, quelle que soit la nature de la mise en valeur."),
        "citation": ("Le Domaine Foncier Rural est constitué par l'ensemble des terres mises en "
                     "valeur ou non"),
        "incertitude_obligatoire": True,
    },
    {
        "nom": "suspension des expulsions (texte OCR non recoupé)",
        "numero_texte": "2020-623", "etat": "PARTIELLEMENT_VERIFIE", "article": "1",
        "enonce": ("Est ratifiée l'ordonnance portant suspension des procédures d'expulsion des "
                   "locataires et de révision à la hausse du loyer des baux d'habitation."),
        "citation": ("Est ratifiée l'ordonnance n°2020-386 du 15 avril 2020 portant suspension "
                     "des procédures d'expulsion des locataires"),
        "incertitude_obligatoire": True,
    },
)


def reference_de(numero_texte, etat):
    for ref in base.lister_references(domaine=DOMAINE):
        if ref["numero_texte"] == numero_texte and ref["etat_verification"] == etat:
            return ref
    return None


class TestCinqExigencesParCas(unittest.TestCase):
    """Les cinq contrôles, exécutés sur chaque cas du domaine."""

    def test_1_article_reellement_present_dans_le_corpus(self):
        for cas in CAS:
            with self.subTest(cas=cas["nom"]):
                reference = reference_de(cas["numero_texte"], cas["etat"])
                self.assertIsNotNone(reference, "référence absente : %s" % cas["numero_texte"])
                article = corpus.obtenir_article_par_reference(reference["ref_id"], cas["article"])
                self.assertIsNotNone(article, "article %s absent" % cas["article"])
                self.assertTrue(article["sha256_article"].startswith("sha256:"))

    def test_2_la_citation_correspond_exactement_au_texte_indexe(self):
        for cas in CAS:
            with self.subTest(cas=cas["nom"]):
                reference = reference_de(cas["numero_texte"], cas["etat"])
                ok, details = corpus.verifier_citation_article(
                    reference["ref_id"], cas["article"], cas["citation"])
                self.assertTrue(ok, "%s : %s" % (cas["nom"], details.get("raison")))

    def test_3_l_explication_ne_depasse_pas_la_source(self):
        for cas in CAS:
            with self.subTest(cas=cas["nom"]):
                reference = reference_de(cas["numero_texte"], cas["etat"])
                controle = corpus.verifier_enonce_contre_article(
                    reference["ref_id"], cas["article"], cas["enonce"])
                self.assertTrue(controle["ok"],
                                "%s : notions hors article %s (couverture %.0f%%)"
                                % (cas["nom"], controle["mots_absents"],
                                   100 * controle["part_couverte"]))

    def test_3bis_un_enonce_invente_est_refuse(self):
        """Témoin négatif : sans lui, le contrôle précédent ne prouve rien."""
        reference = reference_de("2019-576", "VERIFIE")
        controle = corpus.verifier_enonce_contre_article(
            reference["ref_id"], "423",
            "Le bailleur doit verser une indemnité de relogement et un préavis de licenciement.")
        self.assertFalse(controle["ok"])
        self.assertIn("indemnite", " ".join(controle["mots_absents"]).lower())

    def test_4_les_incertitudes_sont_signalees(self):
        """Un texte OCR non recoupé exige une incertitude — sinon l'analyse est refusée."""
        for cas in CAS:
            with self.subTest(cas=cas["nom"]):
                reference = reference_de(cas["numero_texte"], cas["etat"])
                analyse = A.nouvelle_analyse("TEST_CAS", [DOMAINE])
                A.ajouter_regle(analyse, reference["ref_id"], cas["enonce"],
                                articles="Article %s" % cas["article"])
                violations = corpus.verifier_provenance_analyse(analyse)
                if cas["incertitude_obligatoire"]:
                    self.assertEqual([v["code"] for v in violations],
                                     ["PROVENANCE_OCR_NON_DECLAREE"],
                                     "%s : la provenance OCR doit être exigée" % cas["nom"])
                    A.declarer_incertitude(analyse, reference["ref_id"],
                                           "Texte obtenu par OCR, non recoupé.")
                    self.assertEqual(corpus.verifier_provenance_analyse(analyse), [])
                else:
                    self.assertEqual(violations, [],
                                     "%s : aucune incertitude attendue" % cas["nom"])

    def test_4bis_la_loi_de_2020_porte_sa_limite_d_interpretation(self):
        """Une mesure temporaire ne doit pas pouvoir être présentée comme permanente."""
        reference = reference_de("2020-623", "PARTIELLEMENT_VERIFIE")
        limites = (reference.get("limites_interpretation") or "").lower()
        self.assertIn("temporaire", limites)
        self.assertIn("vérifi", limites)

    def test_4ter_toute_reference_porte_une_limite_de_vigueur(self):
        for reference in base.lister_references(domaine=DOMAINE):
            if reference["type_texte"] != "loi":
                continue
            limites = (reference.get("limites_interpretation") or "").lower()
            self.assertTrue(limites, "%s sans limite d'interprétation" % reference["ref_id"])
            self.assertTrue("vigueur" in limites or "vérifier" in limites or "temporaire" in limites,
                            "%s : limite d'interprétation trop vague" % reference["ref_id"])

    def test_5_refus_de_conclure_quand_les_sources_sont_insuffisantes(self):
        for cas in CAS:
            with self.subTest(cas=cas["nom"]):
                reference = reference_de(cas["numero_texte"], cas["etat"])
                analyse = A.nouvelle_analyse("TEST_CAS", [DOMAINE])
                A.ajouter_regle(analyse, reference["ref_id"], cas["enonce"],
                                articles="Article %s" % cas["article"])
                # 5.a — une règle sans application aux faits ne fonde aucune conclusion.
                ok, raisons = A.peut_conclure(analyse)
                self.assertFalse(ok, "%s : conclusion possible sans application aux faits"
                                 % cas["nom"])
                self.assertTrue(any("AUCUNE_APPLICATION" in r for r in raisons))
                A.ajouter_application(analyse, "Application aux faits déclarés.",
                                      ref_ids=[reference["ref_id"]], faits_ids=["F01"])
                references = {reference["ref_id"]: reference}
                codes = [v["code"] for v in A.valider(analyse, references=references)]
                if cas["incertitude_obligatoire"]:
                    # 5.b — une source non vérifiée impose une incertitude DÉCLARÉE.
                    self.assertIn("INCERTITUDE_NON_DECLAREE", codes, cas["nom"])
                    A.declarer_incertitude(analyse, reference["ref_id"], "Texte OCR non recoupé.")
                    codes = [v["code"] for v in A.valider(analyse, references=references)]
                    self.assertNotIn("INCERTITUDE_NON_DECLAREE", codes, cas["nom"])
                else:
                    self.assertEqual(codes, [], cas["nom"])
                ok, raisons = A.peut_conclure(analyse, references=references)
                self.assertTrue(ok, "%s : %s" % (cas["nom"], raisons))


class TestBoutEnBoutSurUneSituationReelle(unittest.TestCase):
    """Une situation complète, du récit à la conclusion documentée."""

    DOSSIER = "TEST_CAS_EXPULSION"

    def tearDown(self):
        shutil.rmtree(str(config.dossier_utilisateur(self.DOSSIER)), ignore_errors=True)

    def test_situation_impaye_et_menace_d_expulsion(self):
        agent = MonRecoursCI()
        demande = ("Mon bailleur dit que je dois partir parce que j'ai deux mois de retard et "
                   "il veut me faire expulser sans passer par le tribunal. Que dit la loi ?")
        dossier = agent.ouvrir_dossier(self.DOSSIER, demande)
        self.assertEqual(dossier["statut"], "EN_COURS")
        self.assertIn("logement_baux_foncier", dossier["qualification"]["domaines_probables"])
        self.assertEqual(dossier["urgence"]["niveau"], "ELEVEE")

        reference = reference_de("2019-576", "VERIFIE")
        analyse = A.nouvelle_analyse(self.DOSSIER, [DOMAINE])
        A.ajouter_regle(analyse, reference["ref_id"],
                        "Lorsque le locataire manque à ses obligations contractuelles, le "
                        "bailleur peut demander son expulsion forcée devant le juge des référés, "
                        "après la transmission de la lettre de demande de résiliation.",
                        articles="Article 445",
                        citation=("« le bailleur peut demander son expulsion forcée devant le Juge "
                                  "des référés »"))
        A.ajouter_regle(analyse, reference["ref_id"],
                        "La lettre de demande de résiliation du contrat de bail doit être "
                        "écrite et motivée.", articles="Article 443")
        A.ajouter_application(analyse,
                              "L'expulsion suppose une demande de résiliation écrite puis une "
                              "décision de justice ; elle ne peut pas être décidée par le "
                              "bailleur seul.", ref_ids=[reference["ref_id"]], faits_ids=["F01"])
        cloture = agent.clore_dossier(self.DOSSIER, analyse)
        self.assertEqual(cloture["statut_reponse"], "ANALYSE_CONFORME")
        codes = [v["code"] for v in cloture["controles_qualite"]["violations"]]
        self.assertEqual(codes, [])
        import json
        contenu = json.load(open(cloture["traceabilite"], encoding="utf-8"))
        articles = contenu["articles_effectivement_verifies"]
        numeros = {e.get("article") for e in articles}
        self.assertIn("445", numeros)
        self.assertIn("443", numeros)
        for entree in articles:
            self.assertTrue(entree["indexe_dans_le_corpus"],
                            "article %s non tracé dans le corpus" % entree.get("article"))
            self.assertRegex(entree["sha256_article"], r"^sha256:[0-9a-f]{64}$")

    def test_conclusion_impossible_sur_un_domaine_absent_du_corpus(self):
        """Le corpus ne couvre pas tout : il doit le dire."""
        agent = MonRecoursCI()
        dossier_id = "TEST_CAS_HORS_CORPUS"
        try:
            agent.ouvrir_dossier(dossier_id, "Mon employeur ne m'a pas payé mon salaire.")
            analyse = A.nouvelle_analyse(dossier_id, ["travail"])
            cloture = agent.clore_dossier(dossier_id, analyse)
            self.assertEqual(cloture["statut_reponse"], "CONCLUSION_IMPOSSIBLE")
            raisons = cloture["controles_qualite"]["raisons_absence_de_conclusion"]
            self.assertTrue(any("AUCUNE_REFERENCE_VERIFIEE" in r for r in raisons))
        finally:
            shutil.rmtree(str(config.dossier_utilisateur(dossier_id)), ignore_errors=True)


class TestRechercheParSituation(unittest.TestCase):
    """Retrouver les bons articles depuis une question en langage courant.

    Chaque attente est MESURÉE sur le corpus livré. Deux cas documentent une
    limite réelle du vocabulaire :
      * « caution » : le Code dit « dépôt de garantie » pour le logement ; le
        pont lexical (SYNONYMES_RECHERCHE) fait le lien — c'est une table de
        recherche, jamais une règle de droit ;
      * « terrain exproprié » : l'article 238 parle d'« expropriation » et
        d'« utilité publique » sans les mots « terrain » ni « Etat ». La question
        doit donc reprendre le vocabulaire du texte.
    """

    QUESTIONS = (
        ("ma caution n'a pas été rendue", "2019-576", "416"),
        ("le bailleur veut augmenter le loyer", "2019-576", "423"),
        ("il veut reprendre le logement", "2019-576", "440"),
        ("il va me faire expulser", "2019-576", "445"),
        ("expropriation pour cause d'utilité publique", "2020-624", "238"),
        ("le domaine public", "2020-624", "181"),
        ("tout aménagement foncier", "2020-624", "69"),
    )

    def test_la_recherche_remonte_l_article_attendu(self):
        for question, numero_texte, article in self.QUESTIONS:
            with self.subTest(question=question):
                resultats = corpus.chercher_articles(question, domaine=DOMAINE, limite=25)
                self.assertTrue(resultats, "aucun résultat pour %r" % question)
                couples = {(r["numero_texte"], r["numero"]) for r in resultats}
                self.assertIn((numero_texte, article), couples,
                              "%r : (%s, %s) absent du top 25 — obtenu %s"
                              % (question, numero_texte, article, sorted(couples)[:12]))
                for resultat in resultats:
                    self.assertTrue(resultat["sha256"].startswith("sha256:"))
                    self.assertTrue(resultat["url_source"].startswith("https://"))
                    self.assertIn(resultat["origine_texte"], ("CALQUE_TEXTE", "OCR_AUTO"))
                    self.assertGreaterEqual(resultat["exemplaires"], 1)

    def test_les_doublons_d_exemplaires_sont_resolus(self):
        """Le même article ne doit pas s'afficher plusieurs fois."""
        resultats = corpus.chercher_articles("le domaine public", domaine=DOMAINE, limite=50)
        couples = [(r["numero_texte"], r["numero"]) for r in resultats]
        self.assertEqual(len(couples), len(set(couples)), "doublons non résolus")
        multiples = [r for r in resultats if r["exemplaires"] > 1]
        self.assertTrue(multiples, "aucun exemplaire multiple : le test ne prouve rien")
        for resultat in multiples:
            self.assertEqual(len(resultat["references_exemplaires"]), resultat["exemplaires"])

    def test_un_terme_ambigu_du_citoyen_est_ponté_par_la_table_de_vocabulaire(self):
        """« caution » seul ne dit pas « dépôt de garantie » dans le Code."""
        brut = [r for r in corpus.chercher_articles("cautionnement", domaine=DOMAINE, limite=10)]
        self.assertTrue(brut, "le mot « cautionnement » doit exister dans le corpus")
        ponte = corpus.chercher_articles("ma caution n'a pas été rendue",
                                         domaine=DOMAINE, limite=25)
        self.assertIn("416", {r["numero"] for r in ponte},
                      "le pont « caution » -> « dépôt de garantie » ne fonctionne plus")

    def test_une_question_hors_corpus_ne_remonte_pas_l_article_du_domaine(self):
        resultats = corpus.chercher_articles("licenciement économique plan social",
                                             domaine=DOMAINE, limite=5)
        numeros = {r["numero"] for r in resultats}
        self.assertNotIn("423", numeros)


if __name__ == "__main__":
    unittest.main(verbosity=2)
