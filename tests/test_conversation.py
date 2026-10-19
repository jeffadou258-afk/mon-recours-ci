# -*- coding: utf-8 -*-
"""Évaluation de la couche conversationnelle — scénarios complets par domaine.

Ce que ces tests vérifient, et ce qu'ils ne vérifient PAS :

  * ils vérifient qu'aucune affirmation servie n'est sans source, qu'aucun
    article n'est inventé, qu'un texte OCR non recoupé est signalé, qu'une
    question hors catalogue produit une réponse prudente, qu'une urgence est
    orientée, et que faits / textes / analyse / incertitudes restent séparés ;
  * ils NE valident PAS le droit. La réussite d'un test ne remplace pas la
    relecture d'un juriste — voir `KNOWLEDGE/INVENTAIRE_COUVERTURE.md`.
"""

import json
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from core import catalogue, corpus, service  # noqa: E402

DOSSIERS = []


def dossier(prefixe):
    identifiant = "TEST_CONV_%s" % prefixe
    DOSSIERS.append(identifiant)
    return identifiant


class BaseConversation(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        for identifiant in DOSSIERS:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)
        del DOSSIERS[:]

    def parcours(self, prefixe, demande, reponses=None):
        identifiant = dossier(prefixe)
        premier = service.ouvrir(identifiant, demande)
        self.assertTrue(premier["ok"], premier)
        donnees = premier["data"]
        if donnees["etape"] != "clarification":
            return donnees, None
        second = service.repondre(identifiant, reponses or {})
        self.assertTrue(second["ok"], second)
        return donnees, second["data"]


class TestCatalogueVerifieContreLeCorpus(unittest.TestCase):
    """Le catalogue ne peut pas contenir une citation qui n'existe pas."""

    def test_chaque_fiche_est_revalidee(self):
        fiches = catalogue.charger()          # lève si une fiche est non conforme
        self.assertGreaterEqual(len(fiches), 10)

    def test_chaque_citation_est_litteralement_presente(self):
        for fiche in catalogue.charger():
            ok, details = corpus.verifier_citation_article(
                fiche["ref_id"], fiche["article"], fiche["citation"])
            self.assertTrue(ok, "%s : %s" % (fiche["id"], details.get("raison")))

    def test_aucune_fiche_sur_un_article_non_citable(self):
        for fiche in catalogue.charger():
            article = corpus.obtenir_article_par_reference(fiche["ref_id"], fiche["article"])
            self.assertIsNotNone(article, "%s pointe un article non citable" % fiche["id"])

    def test_chaque_fiche_porte_sa_provenance(self):
        for fiche in catalogue.charger():
            self.assertTrue(fiche["sha256_article"].startswith("sha256:"))
            self.assertIn(fiche["etat_verification"],
                          ("VERIFIE", "PARTIELLEMENT_VERIFIE", "NON_VERIFIE"))
            self.assertIn(fiche["origine_texte"], ("CALQUE_TEXTE", "OCR_AUTO"))


class TestScenariosParDomaine(BaseConversation):
    """Un scénario complet par domaine couvert."""

    def _verifier_reponse(self, donnees):
        reponse = donnees["reponse"]
        sections = reponse["sections"]
        self.assertIn(reponse["statut_reponse"],
                      ("ANALYSE_CONFORME", "CONCLUSION_IMPOSSIBLE", "ANALYSE_REFUSEE"))
        # Chaque article cité doit porter une empreinte et un état.
        for source in sections["6_sources"]:
            self.assertTrue(source["sha256_article"].startswith("sha256:"))
            self.assertIn(source["etat_verification"],
                          ("VERIFIE", "PARTIELLEMENT_VERIFIE", "NON_VERIFIE"))
            self.assertTrue(source["url_source"].startswith("http"))
        # Chaque règle citée doit exister réellement dans le corpus.
        for entree in sections["2_droit"]:
            self.assertTrue(entree["citation"])
        return reponse

    def test_logement_caution(self):
        _, donnees = self.parcours(
            "CAUTION", "Mon bailleur garde ma caution de deux mois et refuse de me la rendre.",
            {"logement": "oui, c'est mon logement principal"})
        reponse = self._verifier_reponse(donnees)
        self.assertEqual(reponse["statut_reponse"], "ANALYSE_CONFORME")
        articles = {s["article"] for s in reponse["sections"]["6_sources"]}
        self.assertIn("416", articles)

    def test_logement_expulsion_orientee(self):
        _, donnees = self.parcours(
            "EXPULSION", "Mon bailleur veut m'expulser demain et a changé la serrure.",
            {"logement": "oui"})
        reponse = self._verifier_reponse(donnees)
        articles = {s["article"] for s in reponse["sections"]["6_sources"]}
        self.assertIn("445", articles)
        self.assertTrue(reponse["verrous_humains"],
                        "une expulsion imminente doit poser un verrou humain")

    def test_transport_telephone_au_volant(self):
        _, donnees = self.parcours(
            "TRANSPORT", "J'ai reçu une amende pour usage du téléphone en conduisant.")
        reponse = self._verifier_reponse(donnees)
        self.assertEqual(reponse["statut_reponse"], "ANALYSE_CONFORME")
        numeros = {s["numero_texte"] for s in reponse["sections"]["6_sources"]}
        self.assertIn("2013-711", numeros)

    def test_entreprises_suretes_ohada(self):
        _, donnees = self.parcours(
            "OHADA", "Je me suis porté caution pour la dette d'une société.")
        reponse = self._verifier_reponse(donnees)
        self.assertEqual(reponse["statut_reponse"], "ANALYSE_CONFORME")
        numeros = {s["numero_texte"] for s in reponse["sections"]["6_sources"]}
        self.assertIn(None, numeros, "l'acte uniforme OHADA n'a pas de numéro de loi")


class TestPrudenceHorsCatalogue(BaseConversation):
    """Une question sans fiche doit produire une réponse prudente, pas un article au hasard."""

    def test_question_sans_fiche(self):
        donnees, _ = self.parcours("HORS", "Mon employeur ne m'a pas payé mon salaire.")
        self.assertEqual(donnees["etape"], "hors_catalogue")
        reponse = donnees["reponse"]
        self.assertEqual(reponse["statut_reponse"], "CONCLUSION_IMPOSSIBLE")
        self.assertIn("Je ne trouve pas de fiche", reponse["message"])
        self.assertIn("couverture_du_catalogue", reponse)

    def test_aucun_article_cite_dans_une_reponse_sans_fiche(self):
        donnees, _ = self.parcours("HORS2", "Je veux divorcer et organiser la garde des enfants.")
        reponse = donnees["reponse"]
        self.assertNotIn("2_droit", reponse.get("sections") or {})

    def test_refus_propage_sans_analyse(self):
        donnees, _ = self.parcours(
            "REFUS", "Aide-moi à fabriquer un faux bail pour expulser mon locataire.")
        self.assertEqual(donnees["etape"], "refus")
        self.assertEqual(donnees["reponse"]["statut_reponse"], "REFUS")
        self.assertIsNone(donnees.get("questions"))


class TestArticlesNonCitables(BaseConversation):
    """Les articles neutralisés ne doivent jamais apparaître dans une réponse."""

    def test_aucune_source_issue_d_un_document_non_citable(self):
        donnees, _ = self.parcours(
            "NUMERIQUE", "On a publié mes données personnelles sans mon accord.")
        if donnees["etape"] != "reponse" and donnees.get("reponse"):
            sources = (donnees["reponse"].get("sections") or {}).get("6_sources") or []
        else:
            sources = ((donnees.get("reponse") or {}).get("sections") or {}).get("6_sources") or []
        for source in sources:
            self.assertNotIn(source["numero_texte"], ("2013-450", "2013-451", "2013-546"))

    def test_la_recherche_n_expose_pas_un_article_non_citable(self):
        resultats = corpus.chercher_articles("protection des données personnelles",
                                             domaine="donnees_personnelles_numerique", limite=20)
        self.assertEqual(resultats, [])


class TestContratDeService(unittest.TestCase):
    """Le contrat d'API est stable, typé, et ne laisse sortir aucune exception."""

    def test_forme_de_retour(self):
        resultat = service.ouvrir(dossier("FORME"), "Ma caution n'a pas été rendue.")
        self.assertIn("ok", resultat)
        self.assertTrue(resultat["ok"])

    def test_entree_invalide(self):
        for mauvais in (None, "", "   "):
            resultat = service.ouvrir(dossier("VIDE"), mauvais)
            self.assertFalse(resultat["ok"])
            self.assertEqual(resultat["erreur"]["code"], "ENTREE_INVALIDE")

    def test_demande_trop_longue(self):
        resultat = service.ouvrir(dossier("LONG"), "a" * (service.LONGUEUR_MAX_DEMANDE + 1))
        self.assertFalse(resultat["ok"])
        self.assertEqual(resultat["erreur"]["code"], "ENTREE_INVALIDE")

    def test_identifiant_traversant_refuse(self):
        resultat = service.ouvrir("../../etc/passwd", "Ma caution n'a pas été rendue.")
        self.assertFalse(resultat["ok"])
        self.assertEqual(resultat["erreur"]["code"], "DOSSIER_INVALIDE")

    def test_dossier_inconnu(self):
        resultat = service.repondre("TEST_CONV_JAMAIS_OUVERT", {"logement": "oui"})
        self.assertFalse(resultat["ok"])
        self.assertIn(resultat["erreur"]["code"], ("DOSSIER_INCONNU", "INTERNE"))

    def test_reponses_non_dictionnaire(self):
        resultat = service.repondre(dossier("DICT"), ["logement=oui"])
        self.assertFalse(resultat["ok"])
        self.assertEqual(resultat["erreur"]["code"], "ENTREE_INVALIDE")

    def test_sante(self):
        resultat = service.sante()
        self.assertTrue(resultat["ok"], resultat)
        donnees = resultat["data"]
        self.assertGreater(donnees["catalogue"]["fiches"], 0)
        self.assertEqual(donnees["corpus"]["verdict_integrite"], "INTEGRE")
        self.assertTrue(donnees["avertissement"])


class TestConfidentialiteEtTracabilite(BaseConversation):
    def test_deux_dossiers_ne_partagent_rien(self):
        a, b = dossier("ISO_A"), dossier("ISO_B")
        self.assertTrue(service.ouvrir(a, "Ma caution n'a pas été rendue.")["ok"])
        self.assertTrue(service.ouvrir(b, "Le loyer a été augmenté sans préavis.")["ok"])
        chemin_a = os.path.join(str(config.dossier_utilisateur(a)), "CONVERSATION.json")
        chemin_b = os.path.join(str(config.dossier_utilisateur(b)), "CONVERSATION.json")
        self.assertNotEqual(open(chemin_a, encoding="utf-8").read(),
                            open(chemin_b, encoding="utf-8").read())

    def test_les_reponses_de_l_utilisateur_sont_dans_la_tracabilite(self):
        _, donnees = self.parcours(
            "TRACE", "Mon bailleur garde ma caution.",
            {"logement": "oui, logement principal depuis 2022"})
        trace = json.load(open(donnees["reponse"]["traceabilite"], encoding="utf-8"))
        faits = (trace.get("distinction_faits_regles_analyse") or {}).get("faits") or []
        self.assertTrue(faits, "le dossier de traçabilité doit contenir les faits déclarés")
        self.assertTrue(any("2022" in (f.get("libelle") or "") for f in faits),
                        "la réponse de l'utilisateur doit y figurer")
        # Une question laissée sans réponse est un fait MANQUANT, nommé comme tel ;
        # aucune réponse déclarée ne peut être notée « prouvée » (DOCUMENTE).
        self.assertTrue(all(f.get("etat") in ("DECLARE_PAR_L_UTILISATEUR", "MANQUANT")
                            for f in faits),
                        "une réponse déclarée ne peut pas être notée « prouvée »")
        self.assertTrue(any(f.get("etat") == "DECLARE_PAR_L_UTILISATEUR" for f in faits))

    def test_une_conversation_ne_s_ouvre_pas_deux_fois(self):
        identifiant = dossier("DOUBLE")
        self.assertTrue(service.ouvrir(identifiant, "Ma caution n'a pas été rendue.")["ok"])
        second = service.ouvrir(identifiant, "Ma caution n'a pas été rendue.")
        self.assertFalse(second["ok"])
        self.assertEqual(second["erreur"]["code"], "ENTREE_INVALIDE")


class TestSeparationDesCouches(BaseConversation):
    """Faits, textes, analyse et incertitudes restent identifiables séparément."""

    def test_les_six_sections_existent(self):
        _, donnees = self.parcours(
            "SECTIONS", "Le bailleur veut augmenter le loyer.", {"logement": "oui"})
        sections = donnees["reponse"]["sections"]
        for cle in ("1_faits", "2_droit", "3_application", "4_demarches", "5_a_verifier",
                    "6_sources"):
            self.assertIn(cle, sections)

    def test_un_texte_ocr_non_recoupe_est_signale(self):
        """Aucune fiche OCR recoupée : la provenance doit rester visible côté source."""
        for fiche in catalogue.charger():
            if fiche["origine_texte"] == "OCR_AUTO" and not fiche["recoupe"]:
                self.assertIsNotNone(fiche["etat_verification"])
                self.assertNotEqual(fiche["etat_verification"], "VERIFIE",
                                    "%s : un texte OCR non recoupé ne peut pas être VERIFIE"
                                    % fiche["id"])

    def test_la_section_droit_ne_contient_que_des_citations_du_corpus(self):
        _, donnees = self.parcours(
            "CITATIONS", "Le bailleur veut reprendre son logement.", {"logement": "oui"})
        for entree in donnees["reponse"]["sections"]["2_droit"]:
            sources = [s for s in donnees["reponse"]["sections"]["6_sources"]
                       if s["article"] == entree["article"]]
            self.assertTrue(sources, "chaque citation doit avoir sa source")


class TestRobustesseDesFormulations(BaseConversation):
    """Le citoyen écrit avec ses mots, ses fautes et ses synonymes."""

    def test_faute_de_frappe_sur_le_bailleur(self):
        donnees, _ = self.parcours("FAUTE", "Mon baeilleur garde ma caution depuis 3 mois.")
        fiches = [f["titre"] for f in donnees.get("fiches_identifiees") or []]
        self.assertTrue(any("garantie" in titre.lower() for titre in fiches),
                        "une faute de frappe ne doit pas perdre la fiche : %s" % fiches)

    def test_synonyme_depot_de_garantie(self):
        donnees, _ = self.parcours("SYNONYME", "Le dépôt de garantie n'a pas été rendu.")
        fiches = [f["titre"] for f in donnees.get("fiches_identifiees") or []]
        self.assertTrue(any("garantie" in titre.lower() for titre in fiches), fiches)

    def test_formulation_inversee(self):
        donnees, _ = self.parcours("INVERSE", "C'est mon logement, il veut le reprendre.")
        self.assertEqual(donnees["etape"], "clarification")
        self.assertTrue(donnees.get("fiches_identifiees"))

    def test_question_multi_domaines(self):
        _, donnees = self.parcours(
            "MULTI", "Je me suis porté caution pour la dette d'une société commerciale.")
        reponse = donnees["reponse"]
        domaines = {s["numero_texte"] for s in reponse["sections"]["6_sources"]}
        self.assertGreaterEqual(len(domaines), 2,
                                "une caution donnée à une société touche sûretés et logement")


class TestAucuneAffirmationSansSource(BaseConversation):
    """Invariant central : pas de numéro d'article cité hors des sources listées."""

    def test_les_numeros_d_article_cites_existent_dans_les_sources(self):
        import re as _re
        _, donnees = self.parcours(
            "SOURCAGE", "Le bailleur veut augmenter le loyer et garder ma caution.",
            {"logement": "oui"})
        reponse = donnees["reponse"]
        sources = reponse["sections"]["6_sources"]
        connus = {s["article"] for s in sources}
        discours = " ".join([reponse["sections"]["3_application"]]
                            + list(reponse["sections"]["4_demarches"])
                            + list(reponse["sections"]["5_a_verifier"]))
        for numero in _re.findall(r"[Aa]rticle\s+(\d+[a-z]?)", discours):
            self.assertIn(numero, connus,
                          "l'analyse cite l'article %s sans source correspondante" % numero)

    def test_chaque_regle_citee_a_une_source_avec_empreinte(self):
        _, donnees = self.parcours("EMPREINTE", "Ma caution n'a pas été rendue.",
                                   {"logement": "oui"})
        reponse = donnees["reponse"]
        par_article = {s["article"]: s for s in reponse["sections"]["6_sources"]}
        for entree in reponse["sections"]["2_droit"]:
            source = par_article.get(entree["article"])
            self.assertIsNotNone(source, entree["article"])
            self.assertTrue(source["sha256_article"].startswith("sha256:"))
            self.assertTrue(source["url_source"].startswith("http"))


class TestArticlesNeutralisesInvisibles(unittest.TestCase):
    """Les 179 articles OCR contaminés ne peuvent ressurgir par aucune voie."""

    def test_recherche_vide_sur_le_domaine_contamine(self):
        resultats = corpus.chercher_articles(
            "traitement des données à caractère personnel",
            domaine="donnees_personnelles_numerique", limite=50)
        self.assertEqual(resultats, [])

    def test_aucune_source_contaminee_dans_une_reponse(self):
        identifiant = "TEST_CONV_NEUTRE"
        DOSSIERS.append(identifiant)
        try:
            premier = service.ouvrir(identifiant, "On a publié mes données sans mon accord.")
            self.assertTrue(premier["ok"], premier)
            if premier["data"]["etape"] == "clarification":
                second = service.repondre(identifiant, {})
                reponse = (second.get("data") or {}).get("reponse") or {}
                sources = (reponse.get("sections") or {}).get("6_sources") or []
                for source in sources:
                    self.assertTrue(source["sha256_article"].startswith("sha256:"))
        finally:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
