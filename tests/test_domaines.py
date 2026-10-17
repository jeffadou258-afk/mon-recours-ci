# -*- coding: utf-8 -*-
"""Les 14 épreuves exigées par la mission, appliquées aux domaines réels.

Chaque classe porte UNE épreuve de la liste de la partie 10. Les cas s'appuient
sur le corpus réellement présent en base : jamais sur une règle inventée pour
les besoins du test. Quand l'épreuve porte sur une lacune, le résultat attendu
vérifie que l'agent RECONNAÎT la lacune — c'est le comportement à prouver.

Séparation maintenue :
  * tests logiciels      — le code fait ce qu'il annonce ;
  * tests de provenance  — d'où vient le texte, et est-ce dit ;
  * tests de refus       — l'agent s'arrête quand il ne peut pas savoir.

Aucun de ces tests ne vaut validation juridique par un professionnel.
"""

import json
import os
import shutil
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from agent import MonRecoursCI  # noqa: E402
from core import analyse as A  # noqa: E402
from core import base, corpus, couverture, faits as mod_faits, qualification, urgence  # noqa: E402
from core import sources as mod_sources  # noqa: E402
from config import COUVERTURE_DOMAINES, DOMAINES_JURIDIQUES, INSTITUTIONS_HORS_GOUV_CI  # noqa: E402

LOGEMENT = "logement_baux_foncier"
FAMILLE = "famille_mariage_filiation"
DOSSIERS_TEMPORAIRES = []


def dossier_suivi(prefixe):
    identifiant = "TEST_DOM_%s" % prefixe
    DOSSIERS_TEMPORAIRES.append(identifiant)
    return identifiant


def reference_de(numero_texte, domaine, etat=None):
    for ref in base.lister_references(domaine=domaine):
        if ref["numero_texte"] == numero_texte and (etat is None or ref["etat_verification"] == etat):
            return ref
    return None


class BaseDomaines(unittest.TestCase):
    @classmethod
    def tearDownClass(cls):
        for identifiant in DOSSIERS_TEMPORAIRES:
            shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)
        del DOSSIERS_TEMPORAIRES[:]


class Test1QuestionSimpleSoutenueParUnTexteOfficiel(BaseDomaines):
    """Épreuve 1 — une question simple, une réponse adossée à un texte réel."""

    def test_logement_revision_du_loyer(self):
        resultats = corpus.chercher_articles("le loyer peut être révisé", domaine=LOGEMENT,
                                             limite=10)
        self.assertTrue(resultats)
        cible = [r for r in resultats if r["numero"] == "423" and r["numero_texte"] == "2019-576"]
        self.assertTrue(cible, "l'article 423 doit être retrouvé par la recherche")
        reference = reference_de("2019-576", LOGEMENT, "VERIFIE")
        article = corpus.obtenir_article_par_reference(reference["ref_id"], "423")
        # Le texte peut porter un retour à la ligne au milieu d'une phrase :
        # comparer sur le texte écrasé, sinon le test échoue sur une mise en page.
        texte_ecrase = " ".join(article["texte"].split())
        self.assertIn("tous les trois ans", texte_ecrase)
        ok, details = corpus.verifier_citation_article(
            reference["ref_id"], "423",
            "Le loyer peut être révisé à la hausse ou à la baisse, tous les trois ans.")
        self.assertTrue(ok, details)

    def test_famille_objet_du_decret_familles_d_accueil(self):
        reference = reference_de("2023-90", FAMILLE)
        self.assertIsNotNone(reference, "le décret 2023-90 doit être dans le corpus famille")
        article = corpus.obtenir_article_par_reference(reference["ref_id"], "2")
        self.assertIsNotNone(article, "l'article 2 du décret doit être indexé")
        self.assertIn("reglementer les familles", corpus.normaliser(article["texte"]).lower())


class Test2QuestionNecessitantPlusieursArticles(BaseDomaines):
    """Épreuve 2 — une situation que plusieurs articles éclairent ensemble."""

    def test_caution_et_avance_sur_loyer(self):
        reference = reference_de("2019-576", LOGEMENT, "VERIFIE")
        analyse = A.nouvelle_analyse(dossier_suivi("PLUSIEURS"), [LOGEMENT])
        for numero, enonce in (
            ("416", "Le dépôt de garantie ne peut excéder deux mois de loyer."),
            ("415", "Le bailleur ne peut exiger plus de deux mois de loyers d'avance."),
        ):
            A.ajouter_regle(analyse, reference["ref_id"], enonce, articles="Article %s" % numero)
            controle = corpus.verifier_enonce_contre_article(reference["ref_id"], numero, enonce)
            self.assertTrue(controle["ok"], "%s : %s" % (numero, controle["mots_absents"]))
        A.ajouter_application(analyse, "Les deux plafonds se cumulent dans l'analyse.",
                              ref_ids=[reference["ref_id"]], faits_ids=["F01"])
        violations = A.valider(analyse, references={reference["ref_id"]: reference})
        self.assertEqual(violations, [])
        self.assertEqual(len(analyse["regles"]), 2)


class Test3InformationManquante(BaseDomaines):
    """Épreuve 3 — il manque une information : l'agent le NOMME."""

    def test_les_faits_manquants_sont_listes_et_bloquent_la_conclusion(self):
        identifiant = dossier_suivi("MANQUANT")
        faits = mod_faits.Faits(identifiant)
        faits.declarer("Le locataire dit avoir payé le loyer de mars.")
        faits.nommer_manquant("Quittance de loyer de mars",
                              pourquoi="sans elle, le paiement reste déclaratif")
        manquants = faits.manquants
        self.assertTrue(manquants)
        self.assertTrue(any("Quittance" in (m.get("libelle") or "") for m in manquants))
        analyse = A.nouvelle_analyse(identifiant, [LOGEMENT])
        ok, raisons = A.peut_conclure(analyse)
        self.assertFalse(ok)
        self.assertTrue(any("AUCUNE_REGLE" in r or "AUCUNE_APPLICATION" in r for r in raisons))

    def test_un_fait_declare_n_est_jamais_promu_documente_tout_seul(self):
        identifiant = dossier_suivi("DECLARE")
        faits = mod_faits.Faits(identifiant)
        fait = faits.declarer("Le bailleur aurait encaissé deux mois d'avance.")
        self.assertIsInstance(fait, dict)
        self.assertNotEqual(fait["etat"], "DOCUMENTE")
        self.assertFalse(fait.get("empreinte_piece"))
        self.assertEqual(len(faits.documentes), 0)


class Test4TexteIncomplet(BaseDomaines):
    """Épreuve 4 — un texte présent mais non exploitable ne doit pas être cité."""

    def test_la_loi_de_filiation_est_conservee_mais_non_indexee(self):
        documents = [d for d in corpus.lister_documents(domaine=FAMILLE)
                     if d["numero_texte"] == "2019-571"]
        self.assertTrue(documents, "la loi 2019-571 doit être dans le corpus famille")
        document = documents[0]
        self.assertEqual(len(corpus.articles_dun_document(document["doc_id"])), 0,
                         "un découpage en articles non fiable ne doit produire AUCUN article")
        self.assertIn("non fiable", (document["note_qualite"] or "").lower())

    def test_aucune_citation_possible_sur_un_texte_non_indexe(self):
        reference = reference_de("2019-571", FAMILLE)
        article = corpus.obtenir_article_par_reference(reference["ref_id"], "1")
        self.assertIsNone(article)
        ok, details = corpus.verifier_citation_article(reference["ref_id"], "1",
                                                       "Article 1 : texte supposé.")
        self.assertFalse(ok)
        self.assertEqual(details.get("raison"), "ARTICLE_INCONNU")


class Test5VigueurIncertaine(BaseDomaines):
    """Épreuve 5 — l'état du texte est incertain, et c'est écrit."""

    def test_la_mesure_temporaire_de_2020_porte_sa_limite(self):
        reference = reference_de("2020-623", LOGEMENT)
        self.assertIsNotNone(reference)
        self.assertNotEqual(reference["etat_verification"], "VERIFIE")
        limites = (reference.get("limites_interpretation") or "").lower()
        self.assertIn("temporaire", limites)
        self.assertIn("vérifi", limites)

    def test_toute_reference_non_verifiee_exige_une_incertitude_declaree(self):
        for domaine in (LOGEMENT, FAMILLE):
            for reference in base.lister_references(domaine=domaine):
                if reference["etat_verification"] == "VERIFIE":
                    continue
                analyse = A.nouvelle_analyse("TEST_VIGUEUR", [domaine])
                A.ajouter_regle(analyse, reference["ref_id"], "Énoncé de contrôle.",
                                articles="Article 1")
                codes = [v["code"] for v in A.valider(analyse,
                                                      references={reference["ref_id"]: reference})]
                self.assertIn("INCERTITUDE_NON_DECLAREE", codes,
                              "%s devrait exiger une incertitude" % reference["ref_id"])


class Test6QuestionAvecFautes(BaseDomaines):
    """Épreuve 6 — fautes d'orthographe et formulations courantes."""

    QUESTIONS = (
        ("le baeilleur veu augmante le loyer", LOGEMENT),
        ("mon locataire ne paye pa le loyé", LOGEMENT),
        ("jai un problem avec mon proprietaire", LOGEMENT),
        ("je veu comprendre le contrat de bai", LOGEMENT),
    )

    def test_la_qualification_resiste_aux_fautes(self):
        for question, attendu in self.QUESTIONS:
            with self.subTest(question=question):
                resultat = qualification.qualifier(question)
                self.assertIn(attendu, resultat["domaines_probables"],
                              "%r → %s" % (question, resultat["domaines_probables"]))


class Test7MotJuridiqueIncorrect(BaseDomaines):
    """Épreuve 7 — l'utilisateur emploie un mot juridique pour un autre."""

    def test_caution_du_logement_est_pont_e_vers_le_depot_de_garantie(self):
        resultats = corpus.chercher_articles("ma caution n'a pas été rendue",
                                             domaine=LOGEMENT, limite=25)
        numeros = {r["numero"] for r in resultats}
        self.assertIn("416", numeros,
                      "le pont « caution » -> « dépôt de garantie » doit fonctionner")

    def test_le_mot_du_travail_dans_une_situation_de_logement(self):
        resultat = qualification.qualifier(
            "mon bailleur veut me licencier du logement que je loue")
        self.assertIn(LOGEMENT, resultat["domaines_probables"])

    def test_la_table_de_synonymes_est_declaree_comme_aide_a_la_recherche(self):
        self.assertIn("SYNONYMES_RECHERCHE", dir(corpus))
        self.assertIn("caution", corpus.SYNONYMES_RECHERCHE)
        self.assertTrue(corpus.SYNONYMES_RECHERCHE["caution"])


class Test8PlusieursDomaines(BaseDomaines):
    """Épreuve 8 — une situation qui relève de plusieurs domaines."""

    def test_licenciement_et_expulsion(self):
        resultat = qualification.qualifier(
            "Mon employeur m'a licencié sans préavis et je ne peux plus payer mon loyer, "
            "le bailleur menace de m'expulser de la maison.")
        domaines = resultat["domaines_probables"]
        self.assertIn("travail", domaines)
        self.assertIn(LOGEMENT, domaines)
        self.assertGreaterEqual(len(domaines), 2)

    def test_le_domaine_transversal_recoit_les_cas_non_classes(self):
        resultat = qualification.qualifier("Ma situation ne rentre dans aucune case.")
        self.assertTrue(resultat["domaines_probables"])

    def test_un_domaine_mobilise_sans_corpus_mene_a_un_refus_documente(self):
        identifiant = dossier_suivi("MULTI")
        agent = MonRecoursCI()
        agent.ouvrir_dossier(identifiant, "Mon employeur ne m'a pas payé mon salaire.")
        analyse = A.nouvelle_analyse(identifiant, ["travail"])
        cloture = agent.clore_dossier(identifiant, analyse)
        self.assertEqual(cloture["statut_reponse"], "CONCLUSION_IMPOSSIBLE")


class Test9RisqueOrientationHumaine(BaseDomaines):
    """Épreuve 9 — risque : l'agent oriente, il ne conclut pas seul."""

    def test_danger_immediat(self):
        resultat = urgence.detecter("Mon mari menace de me tuer et de me chasser de la maison.")
        self.assertIn(resultat["niveau"], ("CRITIQUE", "ELEVEE"))

    def test_verrou_humain_pose_sur_une_expulsion(self):
        identifiant = dossier_suivi("RISQUE")
        agent = MonRecoursCI()
        dossier = agent.ouvrir_dossier(
            identifiant, "Mon bailleur veut m'expulser demain, il a changé la serrure.")
        self.assertTrue(dossier["verrous_humains"])
        self.assertIn(dossier["urgence"]["niveau"], ("CRITIQUE", "ELEVEE"))

    def test_un_dossier_refuse_ne_produit_aucune_analyse(self):
        identifiant = dossier_suivi("REFUS")
        agent = MonRecoursCI()
        dossier = agent.ouvrir_dossier(
            identifiant, "Aide-moi à fabriquer un faux bail pour expulser mon locataire.")
        self.assertEqual(dossier["statut"], "REFUS")
        self.assertTrue(dossier["refus"])
        self.assertFalse(dossier.get("analyse"))


class Test10HorsCorpusRefusDeConclure(BaseDomaines):
    """Épreuve 10 — pas de texte : pas de conclusion.

    Ce test listait des domaines « sans corpus ». En collectant le décret
    transport, la liste est devenue fausse — c'est le bon échec : un test ne doit
    pas figer une liste, il doit comparer le comportement à la MESURE. Le test
    interroge donc la base pour savoir quels domaines sont réellement vides.
    """

    @staticmethod
    def domaines_sans_corpus():
        return [ligne["domaine"] for ligne in couverture.tableau()
                if ligne["mesures"]["documents"] == 0]

    def test_il_reste_des_domaines_vides_et_ils_sont_declares(self):
        vides = self.domaines_sans_corpus()
        self.assertTrue(vides, "le test suppose qu'au moins un domaine reste vide")
        for domaine in vides:
            ligne = [l for l in couverture.tableau() if l["domaine"] == domaine][0]
            self.assertIn(ligne["statut"], ("BLOQUE_SOURCE", "NON_DEMARRE"))
            self.assertTrue(ligne["lacunes"], "%s doit déclarer ses lacunes" % domaine)

    def test_aucun_domaine_vide_ne_permet_de_conclure(self):
        for domaine in self.domaines_sans_corpus():
            with self.subTest(domaine=domaine):
                analyse = A.nouvelle_analyse("TEST_HORS", [domaine])
                ok, raisons = A.peut_conclure(analyse)
                self.assertFalse(ok)
                self.assertTrue(any("AUCUNE_REFERENCE_VERIFIEE" in r for r in raisons))

    def test_la_couverture_est_coherente_avec_les_mesures(self):
        """Le statut doit décrire la mesure, pour TOUS les domaines.

        Un domaine avec des documents ne peut pas être `BLOQUE_SOURCE`, et un
        domaine sans document ne peut pas être `TERMINE_TECHNIQUEMENT`.
        """
        for ligne in couverture.tableau():
            mesure = ligne["mesures"]
            if mesure["documents"]:
                self.assertIn(ligne["statut"],
                              ("CORPUS_PARTIEL", "TERMINE_TECHNIQUEMENT", "TERMINE_ET_VERIFIE"),
                              "%s a %d document(s) mais se dit %s"
                              % (ligne["domaine"], mesure["documents"], ligne["statut"]))
            else:
                self.assertIn(ligne["statut"], ("BLOQUE_SOURCE", "NON_DEMARRE"),
                              "%s n'a aucun document mais se dit %s"
                              % (ligne["domaine"], ligne["statut"]))
                self.assertTrue(ligne["sources_tentees"],
                                "%s est vide sans avoir tenté de source" % ligne["domaine"])


class Test11InventionRefusee(BaseDomaines):
    """Épreuve 11 — un article ou un délai inventé est refusé."""

    def test_article_inexistant(self):
        reference = reference_de("2019-576", LOGEMENT, "VERIFIE")
        self.assertIsNone(corpus.obtenir_article_par_reference(reference["ref_id"], "9999"))

    def test_reference_inconnue(self):
        analyse = A.nouvelle_analyse("TEST_INVENTION", [LOGEMENT])
        A.ajouter_regle(analyse, "REF-QUI-N-EXISTE-PAS", "Énoncé inventé.")
        codes = [v["code"] for v in A.valider(analyse, references={})]
        self.assertIn("REF_INCONNUE", codes)

    def test_nombre_non_soutenu(self):
        """Un délai chiffré sans appui est refusé — mais SEULEMENT quand les faits
        sont fournis : sans eux, il n'y a rien à comparer, et `valider` le dit."""
        reference = reference_de("2019-576", LOGEMENT, "VERIFIE")
        analyse = A.nouvelle_analyse("TEST_INVENTION", [LOGEMENT])
        A.ajouter_regle(analyse, reference["ref_id"],
                        "Le délai de préavis du bailleur est de 95000 jours.",
                        articles="Article 440")
        codes = [v["code"] for v in A.valider(
            analyse, references={reference["ref_id"]: reference},
            faits_texte="Le bailleur a donné congé le 1er mars.")]
        self.assertIn("NOMBRE_NON_SOUTENU", codes)
        codes_sans_faits = [v["code"] for v in A.valider(
            analyse, references={reference["ref_id"]: reference}, faits_texte="")]
        self.assertNotIn("NOMBRE_NON_SOUTENU", codes_sans_faits,
                         "sans faits fournis, ce contrôle ne peut pas s'appliquer")

    def test_regle_sans_source(self):
        analyse = A.nouvelle_analyse("TEST_INVENTION", [LOGEMENT])
        A.ajouter_regle(analyse, None, "Le propriétaire doit toujours rendre la caution.")
        codes = [v["code"] for v in A.valider(analyse, references={})]
        self.assertIn("REGLE_SANS_SOURCE", codes)


class Test12LaCitationSoutientLaffirmation(BaseDomaines):
    """Épreuve 12 — la citation citée dit bien ce qu'on lui fait dire."""

    def test_citation_exacte_acceptee(self):
        reference = reference_de("2019-576", LOGEMENT, "VERIFIE")
        ok, details = corpus.verifier_citation_article(
            reference["ref_id"], "445",
            "le bailleur peut demander son expulsion forcée devant le Juge des référés")
        self.assertTrue(ok, details)

    def test_citation_modifiee_refusee(self):
        reference = reference_de("2019-576", LOGEMENT, "VERIFIE")
        ok, details = corpus.verifier_citation_article(
            reference["ref_id"], "445",
            "le bailleur peut demander son expulsion forcée devant le préfet du département")
        self.assertFalse(ok, details)

    def test_un_enonce_hors_article_est_refuse(self):
        reference = reference_de("2019-576", LOGEMENT, "VERIFIE")
        controle = corpus.verifier_enonce_contre_article(
            reference["ref_id"], "423",
            "Le bailleur peut augmenter le loyer chaque mois sans préavis.")
        self.assertFalse(controle["ok"])


class Test13Confidentialite(BaseDomaines):
    """Épreuve 13 — cloisonnement des dossiers et absence d'envoi."""

    def test_les_dossiers_sont_cloisonnes(self):
        """Deux API distinctes, deux moments distincts :
        `lire_en_cours` pendant l'instruction, `dossier` pour la traçabilité close."""
        identifiant_a = dossier_suivi("CLOISON_A")
        identifiant_b = dossier_suivi("CLOISON_B")
        agent = MonRecoursCI()
        agent.ouvrir_dossier(identifiant_a, "Mon bailleur garde ma caution.")
        self.assertIsNotNone(agent.lire_en_cours(identifiant_a))
        self.assertIsNone(agent.lire_en_cours(identifiant_b),
                          "un dossier non ouvert ne doit rien rendre")
        self.assertIsNone(agent.dossier(identifiant_b),
                          "un dossier inconnu ne doit pas lever d'exception")
        self.assertIsNone(agent.dossier(identifiant_a),
                          "aucune traçabilité n'existe avant la clôture")

    def test_identifiant_de_dossier_traversant_refuse(self):
        with self.assertRaises(ValueError):
            config.dossier_utilisateur("../../etc/passwd")

    def test_aucun_module_reseau_hors_sources(self):
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for nom in sorted(os.listdir(os.path.join(racine, "core"))):
            if not nom.endswith(".py") or nom == "sources.py":
                continue
            with open(os.path.join(racine, "core", nom), encoding="utf-8") as flux:
                contenu = flux.read()
            self.assertNotIn("urllib.request", contenu,
                             "%s ne doit pas ouvrir de connexion réseau" % nom)

    def test_aucune_fonction_d_envoi(self):
        """Le contrôle porte sur le CODE, pas sur les commentaires : `ast` lit
        les nœuds réels, donc écrire « aucun envoi (smtp…) » dans une docstring
        ne déclenche pas de faux positif."""
        import ast
        racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        chemin = os.path.join(racine, "core", "documents.py")
        with open(chemin, encoding="utf-8") as flux:
            arbre = ast.parse(flux.read())
        interdits = {"smtplib", "socket", "requests", "httpx", "urllib", "http.client"}
        noms_appeles = set()
        for noeud in ast.walk(arbre):
            if isinstance(noeud, ast.Import):
                for alias in noeud.names:
                    self.assertNotIn(alias.name.split(".")[0], interdits,
                                     "import réseau interdit : %s" % alias.name)
            elif isinstance(noeud, ast.ImportFrom):
                self.assertNotIn((noeud.module or "").split(".")[0], interdits,
                                 "import réseau interdit : %s" % noeud.module)
            elif isinstance(noeud, ast.FunctionDef):
                nom = noeud.name.lower()
                for verbe in ("envoyer", "send", "poster", "expedier", "transmettre"):
                    self.assertNotIn(verbe, nom,
                                     "fonction d'envoi détectée : %s" % noeud.name)
                noms_appeles.add(nom)
        self.assertTrue(noms_appeles, "le module doit exposer au moins une fonction")


class Test14NonRegression(BaseDomaines):
    """Épreuve 14 — les acquis des phases précédentes tiennent."""

    def test_le_corpus_logement_ne_perd_pas_d_articles(self):
        compte = sum(len(corpus.articles_dun_document(d["doc_id"]))
                     for d in corpus.lister_documents(domaine=LOGEMENT))
        self.assertGreaterEqual(compte, 1173, "le corpus logement a rétréci : %d" % compte)

    def test_integrite_du_corpus(self):
        rapport = corpus.verifier_integrite()
        self.assertEqual(rapport["verdict"], "INTEGRE")
        self.assertEqual(rapport["absents"], [])
        self.assertEqual(rapport["alteres"], [])

    def test_aucun_artefact_d_editeur_dans_les_articles(self):
        import sqlite3
        with sqlite3.connect(str(config.CHEMIN_DB)) as connexion:
            lignes = connexion.execute("SELECT doc_id, numero, texte FROM articles_corpus")
            for doc_id, numero, texte in lignes:
                trouves = corpus.textes_contaminants(texte)
                self.assertFalse(trouves, "%s article %s : %s" % (doc_id, numero, trouves))

    def test_les_garde_fous_historiques_repondent_toujours(self):
        analyse = A.nouvelle_analyse("TEST_NR", [LOGEMENT])
        A.ajouter_regle(analyse, None, "Règle sans source.")
        self.assertTrue(A.valider(analyse, references={}))

    def test_aucune_validation_humaine_nait_toute_seule(self):
        compte = corpus.articles_par_origine()
        self.assertEqual(compte["VERIFIE_MANUELLEMENT"]["articles"], 0,
                         "aucun texte n'a été relu par un humain : ce chiffre doit rester 0")


class TestAucunDocumentMuet(BaseDomaines):
    """Un document sans article doit DIRE pourquoi il n'en a pas.

    Deux défauts réels trouvés en conditions d'exécution :
      1. cinq documents refusés conservaient la note « scan sans calque texte —
         OCR requis », et le rapport annonçait « INTEGRER » pour des documents
         finalement refusés à l'indexation : la base et le rapport se
         contredisaient ;
      2. une re-collecte du domaine **effaçait** la trace du refus, parce que le
         collecteur et le lecteur OCR écrivaient dans la même colonne.

    D'où deux colonnes : `note_qualite` (état d'extraction, écrite par le
    collecteur) et `note_ocr` (résultat de la tentative d'OCR, écrite par le
    lecteur OCR). Aucun des deux écrivains ne peut effacer le fait de l'autre.
    """

    MOTIFS = ("ocr", "refus", "non fiable", "compilation", "non juridique")

    def _note_complete(self, document):
        return " ".join(x for x in (document.get("note_qualite"),
                                    document.get("note_ocr")) if x)

    def test_chaque_document_porte_une_note_explicite(self):
        for domaine in (LOGEMENT, FAMILLE):
            for document in corpus.lister_documents(domaine=domaine):
                note = self._note_complete(document).strip()
                self.assertGreaterEqual(len(note), 12,
                                        "%s : aucune note sur l'extraction ni sur l'OCR"
                                        % document["doc_id"])

    def test_un_document_sans_article_dit_pourquoi(self):
        for domaine in (LOGEMENT, FAMILLE):
            for document in corpus.lister_documents(domaine=domaine):
                if corpus.articles_dun_document(document["doc_id"]):
                    continue
                note = self._note_complete(document).lower()
                self.assertTrue(any(motif in note for motif in self.MOTIFS),
                                "%s : aucun article et aucune raison nommée (%r)"
                                % (document["doc_id"], note))

    def test_un_refus_ocr_laisse_une_trace_du_refus_et_pas_du_besoin(self):
        """« OCR requis » sur un document déjà refusé est un mensonge par omission."""
        refuses = [d for domaine in (LOGEMENT, FAMILLE)
                   for d in corpus.lister_documents(domaine=domaine)
                   if "refus" in (d.get("note_ocr") or "").lower()]
        self.assertTrue(refuses, "aucun refus d'OCR tracé : le test ne prouve rien")
        for document in refuses:
            note = (document["note_ocr"] or "").lower()
            self.assertIn("ocr tenté", note)
            self.assertIn("refusé", note)

    def test_une_re_collecte_n_efface_pas_la_trace_ocr(self):
        """La régression exacte : deux écrivains, deux colonnes.

        Le collecteur réécrit les métadonnées du document (`actualiser=True`).
        S'il touchait `note_ocr`, l'historique d'un refus disparaîtrait — c'est
        arrivé avant que les deux faits ne soient séparés.
        """
        refuse = [d for domaine in (LOGEMENT, FAMILLE)
                  for d in corpus.lister_documents(domaine=domaine)
                  if "refus" in (d.get("note_ocr") or "").lower()]
        self.assertTrue(refuse, "aucun refus d'OCR tracé : le test ne prouve rien")
        document = refuse[0]
        avant = document["note_ocr"]
        corpus.importer_document(
            ref_id=document["ref_id"], titre=document["titre"],
            type_texte=document["type_texte"], numero_texte=document["numero_texte"],
            date_texte=document["date_texte"], domaine=document["domaine"],
            autorite=document["autorite"], url_source=document["url_source"],
            chemin_local=document["chemin_local"],
            licence_conditions=document["licence_conditions"], pages=document["pages"],
            calque_texte=bool(document["calque_texte"]),
            fichier_texte=document["fichier_texte"],
            sha256_declare=document["sha256"],
            note_qualite="scan sans calque texte — OCR requis",
            methode_extraction=document["methode_extraction"],
            actualiser=True)
        apres = [d for d in corpus.lister_documents(domaine=document["domaine"])
                 if d["doc_id"] == document["doc_id"]][0]
        self.assertEqual(apres["note_ocr"], avant,
                         "une re-collecte ne doit jamais effacer la trace d'un OCR")


class TestStatutsDeDomaine(BaseDomaines):
    """Les statuts sont calculés, cohérents, et jamais flatteurs."""

    def test_la_taxonomie_couvre_les_douze_codes(self):
        codes = [e["code"] for e in COUVERTURE_DOMAINES]
        self.assertEqual(len(codes), 12)
        for entree in COUVERTURE_DOMAINES:
            self.assertIn(entree["cle"], DOMAINES_JURIDIQUES,
                          "%s référence un domaine interne inexistant" % entree["code"])

    def test_chaque_domaine_interne_a_une_decision_declaree(self):
        for domaine in DOMAINES_JURIDIQUES:
            self.assertIn(domaine, couverture.DECLARATIONS,
                          "%s n'a aucune déclaration de couverture" % domaine)

    def test_un_domaine_sans_corpus_n_est_jamais_en_attente_de_validation(self):
        for ligne in couverture.tableau():
            if ligne["mesures"]["documents"] == 0:
                self.assertNotEqual(ligne["statut"], "EN_ATTENTE_VALIDATION_HUMAINE",
                                    "%s : un domaine vide n'est pas « en attente »" % ligne["domaine"])

    def test_termine_et_verifie_est_inatteignable_sans_relecture_humaine(self):
        for ligne in couverture.tableau():
            self.assertNotEqual(ligne["statut"], "TERMINE_ET_VERIFIE",
                                "%s : aucun article n'a été relu par un humain" % ligne["domaine"])

    def test_les_statuts_appartiennent_a_la_liste_prevue(self):
        for ligne in couverture.tableau():
            self.assertIn(ligne["statut"], config.STATUTS_DOMAINE)

    def test_un_domaine_avec_corpus_declare_ses_lacunes(self):
        for ligne in couverture.tableau():
            if ligne["mesures"]["documents"]:
                self.assertTrue(ligne["lacunes"],
                                "%s a un corpus mais ne déclare aucune lacune" % ligne["domaine"])

    def test_les_institutions_hors_gouv_ci_sont_toutes_au_registre(self):
        """La porte d'entrée du périmètre officiel doit être explicite."""
        hotes_registre = set()
        for source in config.SOURCES_OFFICIELLES:
            import urllib.parse
            hotes_registre.add((urllib.parse.urlparse(source["url"]).hostname or "").lower())
        for institution in INSTITUTIONS_HORS_GOUV_CI:
            correspond = [h for h in hotes_registre if h == institution or h.endswith("." + institution)]
            self.assertTrue(correspond,
                            "%s est déclaré officiel sans figurer au registre des sources" % institution)

    def test_le_perimetre_officiel_refuse_les_sources_secondaires(self):
        for url in ("https://loidici.biz/un-texte", "https://scribd.com/document/1",
                    "https://www.droitci.info/files/x.pdf", "https://lexterra.ci/data/x.pdf",
                    "https://civlii.laws.africa/en/akn/ci/act/2019/571"):
            self.assertFalse(mod_sources.est_hote_officiel(url),
                             "%s ne doit pas être dans le périmètre officiel" % url)

    def test_le_perimetre_officiel_accepte_les_institutions_verifiees(self):
        for url in ("https://famille.gouv.ci/uploads/publications/176937124389.pdf",
                    "https://www.oneci.ci/uploads/files/articles/x.pdf",
                    "https://ohada.org/uniform-acts"):
            self.assertTrue(mod_sources.est_hote_officiel(url), url)

    def test_l_inventaire_est_serialisable_et_methodologique(self):
        inventaire_courant = couverture.inventaire()
        json.dumps(inventaire_courant)
        self.assertIn("methode_de_comptage", inventaire_courant)
        self.assertTrue(inventaire_courant["avertissement"])
        self.assertEqual(inventaire_courant["total_documents"],
                         sum(l["mesures"]["documents"] for l in inventaire_courant["domaines"]))
        self.assertEqual(inventaire_courant["total_articles"],
                         sum(l["mesures"]["articles"] for l in inventaire_courant["domaines"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
