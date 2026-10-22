# -*- coding: utf-8 -*-
"""Couche conversationnelle de Mon Recours CI — machine à états déterministe.

Ce module ne raisonne PAS à la place du moteur : il orchestre. Il :

  1. qualifie la demande (core.qualification, via l'orchestrateur) ;
  2. choisit des FICHES du catalogue qui pointent vers des articles réels ;
  3. pose les questions de fait indispensables (et seulement celles-là) ;
  4. construit une analyse avec `core.analyse` — donc soumise à `valider()` ;
  5. la fait clore par `MonRecoursCI.clore_dossier` — donc soumise aux verrous ;
  6. restitue la réponse en distinguant faits, textes, analyse et incertitudes.

Séparation tenue :
    conversation  -> ce module (état, questions, restitution)
    recherche     -> core.corpus (articles réels)
    analyse       -> core.analyse (validation anti-invention)
    provenance    -> champs `origine_texte`, `etat_verification`, `sha256_article`
    restitution   -> `_restituer()` (aucune décision juridique n'y est prise)

Ce qui n'est PAS fait : aucune génération de texte libre, aucun modèle de
langage. Une question sans fiche reçoit une réponse honnête, pas une réponse
inventée.
"""

import json
import os

import config
from agent import MonRecoursCI
from core import analyse as A
from core import base, catalogue, clarification, corpus, documents as mod_documents
from core import faits as mod_faits
from core import aiguillage, domaines_vision, llm

FICHIER_ETAT = "CONVERSATION.json"

# Ce que la couche ne sait pas faire, dit à l'utilisateur avant toute réponse.
# Trois tentatives de sélection au plus. Au-delà, on conclut prudemment : une
# question reposée indéfiniment est une panne déguisée en dialogue.
SEUIL_AIGUILLAGE = 3

AVERTISSEMENT = (
    "Je suis un service d'information juridique, pas un avocat. Je ne réponds que "
    "sur les textes enregistrés dans mon corpus, et je dis quand je ne peux pas."
)


class Conversation(object):
    """Une conversation = un dossier. L'état est écrit sur disque, jamais en mémoire."""

    def __init__(self, chemin_db=None, chemin_sources=None, fiches=None,
                 fournisseur_langage=None):
        # None : le fournisseur est lu dans l'environnement (désactivé par défaut).
        self.fournisseur_langage = fournisseur_langage
        self._suggestions_llm = {}
        self.agent = MonRecoursCI(chemin_db=chemin_db, chemin_sources=chemin_sources)
        self.chemin_db = path = (chemin_db or str(config.CHEMIN_DB))
        self.fiches = fiches if fiches is not None else catalogue.charger(chemin_db=path)
        self.catalogue = {f["id"]: f for f in self.fiches}
        # Guide de clarification : validé contre le corpus. Non conforme -> il
        # n'est PAS servi (les fiches restent utilisables, sans ses questions),
        # et l'anomalie est exposée par `guide_erreur`.
        self.guide_erreur = None
        try:
            self.guide = clarification.charger(self.fiches, chemin_db=path)
        except clarification.GuideInvalide as erreur:
            self.guide = {"statut_validation": None, "questions": []}
            self.guide_erreur = str(erreur)

    # -- état ------------------------------------------------------------
    def _chemin_etat(self, dossier_id):
        return str(config.dossier_utilisateur(dossier_id) / FICHIER_ETAT)

    def _lire_etat(self, dossier_id):
        chemin = self._chemin_etat(dossier_id)
        if not os.path.isfile(chemin):
            return None
        with open(chemin, encoding="utf-8") as flux:
            return json.load(flux)

    def _ecrire_etat(self, dossier_id, etat):
        chemin = self._chemin_etat(dossier_id)
        config.ecrire_fichier_prive(chemin, json.dumps(etat, ensure_ascii=False, indent=1))
        return etat

    # -- tour 1 ----------------------------------------------------------
    def demarrer(self, dossier_id, demande):
        """Ouvre un dossier, qualifie, choisit les fiches, pose les questions utiles."""
        dossier = self.agent.ouvrir_dossier(dossier_id, demande)
        if dossier.get("statut") == "REFUS":
            return {"etape": "refus", "dossier_id": dossier_id,
                    "reponse": self._restituer_refus(dossier)}

        qualification = dossier.get("qualification") or {}
        domaines = qualification.get("domaines_probables") or ["indetermine"]
        retenues, du_domaine = catalogue.pour_demande(
            demande, domaines, fiches=self.fiches, chemin_db=self.chemin_db,
            scores=qualification.get("scores_domaines"))
        # Ce que le moteur a établi SANS le modèle : la référence pour décider
        # plus bas si plusieurs procédures restent réellement candidates.
        deterministes = [f["id"] for f in retenues]

        # Compréhension assistée par un modèle de langage, SI elle est activée
        # (fournisseur + clé + accord sur l'envoi des données). Ce qu'il propose
        # est revalidé DEUX fois : `llm.valider_comprehension` (identifiants
        # connus, extraits recopiés mot pour mot) puis
        # `catalogue.valider_fiches_proposees`, qui rejoue la décision SANS le
        # modèle. Le modèle ne peut donc pas IMPOSER une fiche : il confirme ou
        # complète la sélection déterministe, jamais il ne la remplace.
        # Sans la seconde validation, un modèle hors sujet faisait entrer sa
        # fiche préférée — le défaut exact observé sur « naissance » et « saisie ».
        comprehension = llm.comprendre(demande, self.fiches, self.guide,
                                       fournisseur=self.fournisseur_langage)
        if comprehension["mode"] == "llm" and comprehension["fiches"]:
            proposees = [self.catalogue[i] for i in comprehension["fiches"]
                         if i in self.catalogue]
            validees, rejets_pertinence = catalogue.valider_fiches_proposees(
                proposees, demande, fiches=self.fiches, domaines=domaines,
                scores=qualification.get("scores_domaines"))
            if rejets_pertinence:
                comprehension["rejets"] = list(comprehension.get("rejets") or []) + rejets_pertinence
            if validees:
                # Le modèle peut RESSERRER la sélection — après contrôle — jamais
                # l'élargir hors des domaines qualifiés. S'il ne reste aucune fiche
                # validée, la sélection déterministe est conservée telle quelle.
                retenues = validees
        self._suggestions_llm = comprehension["suggestions"]

        # Aiguillage : plusieurs procédures restent candidates. On ne les présente
        # pas toutes comme applicables — on demande au citoyen laquelle est la
        # sienne. Le modèle ne tranche jamais : il propose, la table nomme les
        # situations, le citoyen choisit.
        #
        # Deux conditions, pas une :
        #   * plusieurs fiches restent candidates ;
        #   * le modèle en a AJOUTÉ au-delà de ce que le moteur avait établi
        #     (sinon les paires complémentaires trouvées par le moteur — désaveu
        #     et délai de désaveu — seraient cassées).
        # Et si aucune entrée de table ne couvre ce cas, on ne présente RIEN :
        # plusieurs procédures voisines ne valent pas une couverture juridique.
        if len(retenues) > 1 and len(deterministes) < len(retenues):
            entree = aiguillage.situation_pour(retenues, catalogue=self.fiches)
            if entree is not None:
                return self._ouvrir_aiguillage(dossier_id, demande, domaines, entree,
                                               comprehension, dossier, deterministes)
            # Amplification non vérifiable : la démarche n'est pas couverte par
            # une fiche identifiable. On retombe sur le comportement prudent.
            retenues = []

        if not retenues:
            # Aucun déclencheur ne tombe : on ne sert PAS d'articles au hasard.
            etat = {"dossier_id": dossier_id, "demande": demande, "tour": 1,
                    "fiches": [], "questions": [], "etape": "hors_catalogue",
                    "domaines": domaines,
                    "comprehension": self._vue_comprehension(comprehension)}
            self._ecrire_etat(dossier_id, etat)
            # L'urgence et les verrous humains sont TOUJOURS restitués, même sans
            # fiche : une situation de violence hors catalogue doit être orientée.
            return {"etape": "hors_catalogue", "dossier_id": dossier_id,
                    "reponse": self._restituer_sans_fiche(demande, domaines, du_domaine),
                    "domaines": domaines, "comprehension": etat["comprehension"],
                    "urgence": dossier.get("urgence"),
                    "verrous_humains": dossier.get("verrous_humains")}

        questions, deja = [], set()
        for fiche in retenues:
            for cle, question in fiche.get("faits_requis", []):
                if cle not in deja:
                    deja.add(cle)
                    questions.append({"cle": cle, "question": question})
        guide = clarification.questions_pour(retenues, self.guide, deja_posees=deja)
        questions.extend(self._question_guide(q, demande) for q in guide)
        etat = {"dossier_id": dossier_id, "demande": demande, "tour": 1,
                "fiches": [f["id"] for f in retenues], "questions": questions,
                "guide_posees": [q["cle"] for q in guide], "reponses": {},
                "confirmations": [],
                "etape": "clarification", "domaines": domaines,
                "comprehension": self._vue_comprehension(comprehension),
                "suggestions_llm": comprehension["suggestions"],
                "urgence": dossier.get("urgence"),
                "verrous_humains": dossier.get("verrous_humains"),
                "note_corpus": dossier.get("note_corpus")}
        self._ecrire_etat(dossier_id, etat)
        return self._vue_clarification(dossier_id, etat, retenues, questions)

    def _question_guide(self, q, demande, confirmation=None):
        suggestion = (clarification.suggestion(q, demande)
                      or (self._suggestions_llm or {}).get(q["cle"]))
        vue = {"cle": q["cle"], "question": q["question"], "pourquoi": q["pourquoi"],
               "type": "oui_non", "suggestion": suggestion}
        if confirmation:
            vue["confirmation"] = confirmation
        return vue

    @staticmethod
    def _vue_comprehension(rapport):
        """Ce qui est montré de la compréhension : le mode, toujours ; le résumé, si validé."""
        return {"mode": rapport["mode"], "fournisseur": rapport.get("fournisseur"),
                "resume": rapport.get("resume") if rapport["mode"] == "llm" else None,
                "elements_rejetes": len(rapport.get("rejets") or []),
                "coordonnees_masquees": rapport.get("masquages", 0)}

    def _vue_clarification(self, dossier_id, etat, retenues, questions, contradictions=()):
        return {"etape": "clarification", "dossier_id": dossier_id,
                "tour": etat.get("tour", 1),
                "avertissement": AVERTISSEMENT,
                "urgence": etat.get("urgence"),
                "verrous_humains": etat.get("verrous_humains"),
                "fiches_identifiees": [
                    {"titre": f["titre"], "article": f["article"],
                     "numero_texte": f.get("numero_texte"),
                     "etat_verification": f["etat_verification"]} for f in retenues],
                "questions": questions,
                "contradictions": list(contradictions),
                "statut_questions": self.guide.get("statut_validation"),
                "comprehension": etat.get("comprehension"),
                "note_corpus": etat.get("note_corpus")}

    # -- tours suivants --------------------------------------------------
    def repondre(self, dossier_id, reponses):
        """Enregistre les réponses, construit l'analyse, la fait valider, restitue."""
        etat = self._lire_etat(dossier_id)
        if etat is None:
            return {"etape": "erreur", "erreur": "DOSSIER_INCONNU",
                    "message": "Aucune conversation ouverte pour ce dossier."}
        if etat.get("etape") == "repondu":
            return {"etape": "repondu", "reponse": etat.get("reponse"),
                    "message": "Cette conversation a déjà reçu sa réponse."}

        if etat.get("etape") == "aiguillage":
            return self._traiter_aiguillage(dossier_id, etat, reponses)

        fiches = [self.catalogue[i] for i in etat["fiches"] if i in self.catalogue]
        if not fiches:
            return {"etape": "erreur", "erreur": "AUCUNE_FICHE",
                    "message": "Aucune fiche n'est associée à ce dossier."}

        # Réponses cumulées sur les tours. Seules les questions posées sont lues.
        posees = {q["cle"] for q in etat.get("questions", [])}
        cumul = dict(etat.get("reponses") or {})
        for cle, valeur in (reponses or {}).items():
            if cle in posees:
                cumul[cle] = valeur
        reponses = cumul
        etat["reponses"] = cumul

        relance = self._relance(etat, fiches, reponses)
        if relance is not None:
            return relance

        faits = mod_faits.Faits(dossier_id)
        fait_ids = []
        for fiche in fiches:
            for cle, question in fiche.get("faits_requis", []):
                reponse = (reponses or {}).get(cle)
                if reponse in (None, "", []):
                    fait = faits.nommer_manquant(question, pourquoi="réponse non fournie")
                else:
                    fait = faits.declarer("%s : %s" % (question, reponse))
                fait_ids.append(fait["fait_id"])
        for q in self._questions_guide(etat):
            valeur = clarification.lire_valeur(reponses.get(q["cle"]))
            if valeur is None:
                fait = faits.nommer_manquant(q["question"], pourquoi=q["pourquoi"])
            else:
                fait = faits.declarer("%s : %s" % (q["question"], reponses.get(q["cle"])))
            fait_ids.append(fait["fait_id"])
        if not fait_ids:
            fait_ids.append(faits.declarer(etat["demande"])["fait_id"])
        # Persistance : sans elle, les réponses de l'utilisateur ne figureraient
        # jamais dans le dossier de traçabilité.
        self.agent.enregistrer_faits(dossier_id, faits)

        analyse = self._construire_analyse(dossier_id, fiches, fait_ids)
        try:
            cloture = self.agent.clore_dossier(dossier_id, analyse)
        except ValueError as erreur:
            etat.update(etape="repondu",
                        reponse={"statut_reponse": "ANALYSE_REFUSEE",
                                 "erreur": str(erreur)})
            self._ecrire_etat(dossier_id, etat)
            return {"etape": "erreur", "erreur": "ANALYSE_REFUSEE",
                    "message": str(erreur)}

        reponse = self._restituer(cloture, fiches, etat)
        etat.update(etape="repondu", reponse=reponse)
        self._ecrire_etat(dossier_id, etat)
        return {"etape": "reponse", "dossier_id": dossier_id, "reponse": reponse}

    def _questions_guide(self, etat):
        index = {q["cle"]: q for q in self.guide.get("questions", [])}
        return [index[c] for c in etat.get("guide_posees", []) if c in index]

    def _relance(self, etat, fiches, reponses):
        """Tour suivant si une réponse contredit le récit, ou ouvre une question.

        Au plus `clarification.TOURS_MAX` tours : au-delà, la réponse est
        construite avec ce qui est connu, contradictions et manques nommés.
        """
        if etat.get("tour", 1) >= clarification.TOURS_MAX:
            return None
        dossier_id = etat["dossier_id"]
        self._suggestions_llm = etat.get("suggestions_llm") or {}
        posees_guide = self._questions_guide(etat)
        deja_confirmees = set(etat.get("confirmations") or [])
        a_confirmer = [c for c in clarification.contradictions(
            posees_guide, reponses, etat.get("demande")) if c["cle"] not in deja_confirmees]
        nouvelles = clarification.questions_pour(
            fiches, self.guide, deja_posees=set(etat.get("guide_posees") or []),
            reponses=reponses)
        if not a_confirmer and not nouvelles:
            return None
        index = {q["cle"]: q for q in self.guide.get("questions", [])}
        questions = [self._question_guide(index[c["cle"]], etat.get("demande"),
                                          confirmation=c["message"]) for c in a_confirmer]
        questions.extend(self._question_guide(q, etat.get("demande")) for q in nouvelles)
        etat["tour"] = etat.get("tour", 1) + 1
        etat["confirmations"] = sorted(deja_confirmees | {c["cle"] for c in a_confirmer})
        etat["guide_posees"] = list(etat.get("guide_posees") or []) + [q["cle"] for q in nouvelles]
        etat["questions"] = list(etat.get("questions") or []) + [
            q for q in questions if q["cle"] not in {x["cle"] for x in etat.get("questions", [])}]
        self._ecrire_etat(dossier_id, etat)
        return self._vue_clarification(dossier_id, etat, fiches, questions, a_confirmer)

    # -- aiguillage ------------------------------------------------------
    def _ouvrir_aiguillage(self, dossier_id, demande, domaines, entree,
                           comprehension, dossier, deterministes):
        """Ouvre l'étape de choix : plusieurs procédures, une seule question."""
        etat = {"dossier_id": dossier_id, "demande": demande, "tour": 1,
                "fiches": [o["fiche"] for o in entree["options"]],
                "questions": [], "reponses": {}, "etape": "aiguillage",
                "situation": entree["cle"], "aiguillage_essais": 0,
                "aiguillage_deterministes": list(deterministes),
                "domaines": domaines,
                "comprehension": self._vue_comprehension(comprehension),
                "suggestions_llm": comprehension["suggestions"],
                "urgence": dossier.get("urgence"),
                "verrous_humains": dossier.get("verrous_humains"),
                "note_corpus": dossier.get("note_corpus")}
        self._ecrire_etat(dossier_id, etat)
        return self._vue_aiguillage(etat, entree)

    def _vue_aiguillage(self, etat, entree):
        table = aiguillage.charger()
        return {
            "etape": "aiguillage",
            "dossier_id": etat["dossier_id"],
            "situation": entree["cle"],
            "question": entree["question"],
            "pourquoi": entree.get("pourquoi"),
            "message": ("Plusieurs situations peuvent correspondre à ce que vous décrivez. "
                        "Je ne peux pas déterminer laquelle est la vôtre : la loi ne prévoit "
                        "pas les mêmes règles pour chacune."),
            "options": aiguillage.options(entree, self.fiches),
            "option_aucune": "Aucune de ces situations ne correspond à la mienne",
            "avertissement": AVERTISSEMENT,
            "urgence": etat.get("urgence"),
            "verrous_humains": etat.get("verrous_humains"),
            "comprehension": etat.get("comprehension"),
            "statut_table": table.get("statut"),
        }

    def _traiter_aiguillage(self, dossier_id, etat, reponses):
        """Valide la sélection du citoyen. Sélection invalide => jamais de conclusion."""
        table = aiguillage.charger()
        entree = None
        for candidate in table.get("situations") or []:
            if candidate.get("cle") == etat.get("situation"):
                entree = candidate
                break
        if entree is None:
            return self._conclure_prudemment(
                dossier_id, etat,
                "La situation à préciser n'est plus disponible. Je ne peux pas conclure.")

        choix = aiguillage.choix_valide((reponses or {}).get("aiguillage"), entree)
        if choix is None:
            # Sélection absente ou hors des options : on repose la question, sans
            # conclure. Trois tentatives au plus, puis réponse prudente : une
            # boucle de questions serait une panne déguisée en dialogue.
            essais = int(etat.get("aiguillage_essais") or 0) + 1
            etat["aiguillage_essais"] = essais
            if essais > SEUIL_AIGUILLAGE:
                return self._conclure_prudemment(
                    dossier_id, etat,
                    "Je n'ai pas pu établir laquelle de ces situations est la vôtre. "
                    "Je préfère ne rien conclure plutôt que de répondre à côté.")
            self._ecrire_etat(dossier_id, etat)
            vue = self._vue_aiguillage(etat, entree)
            vue["erreur_selection"] = ("Choisissez l'une des situations proposées, "
                                       "ou « aucune ».")
            return vue

        if choix == "aucune":
            return self._conclure_prudemment(
                dossier_id, etat,
                "Aucune des situations proposées ne correspond à la vôtre. Je ne peux "
                "donc pas déterminer quelle règle s'applique : je préfère vous le dire.")

        fiche = self.catalogue.get(choix)
        if fiche is None:
            return self._conclure_prudemment(
                dossier_id, etat,
                "La fiche retenue n'est plus disponible. Je ne peux pas conclure.")
        questions = []
        deja = set()
        for cle, question in fiche.get("faits_requis") or []:
            if cle not in deja:
                deja.add(cle)
                questions.append({"cle": cle, "question": question})
        guide = clarification.questions_pour([fiche], self.guide, deja_posees=deja)
        questions.extend(self._question_guide(q, etat.get("demande")) for q in guide)
        etat.update(etape="clarification", fiches=[choix], questions=questions,
                    guide_posees=[q["cle"] for q in guide], reponses={}, tour=1,
                    aiguillage_choisi=choix)
        self._ecrire_etat(dossier_id, etat)
        return self._vue_clarification(dossier_id, etat, [fiche], questions)

    def _conclure_prudemment(self, dossier_id, etat, message):
        reponse = {"statut_reponse": "CONCLUSION_IMPOSSIBLE",
                   "message": message,
                   "avertissement": AVERTISSEMENT}
        etat.update(etape="repondu", reponse=reponse)
        self._ecrire_etat(dossier_id, etat)
        return {"etape": "reponse", "dossier_id": dossier_id, "reponse": reponse}

    def _construire_analyse(self, dossier_id, fiches, fait_ids):
        analyse = A.nouvelle_analyse(dossier_id, sorted({f["domaine"] for f in fiches}))
        for fiche in fiches:
            A.ajouter_regle(analyse, fiche["ref_id"], fiche["citation"],
                            articles="Article %s" % fiche["article"],
                            citation="« %s »" % fiche["citation"])
        A.ajouter_application(
            analyse,
            "Ces articles s'appliquent à la situation décrite par l'utilisateur, "
            "sous réserve des faits non établis.",
            ref_ids=[f["ref_id"] for f in fiches], faits_ids=fait_ids)
        for fiche in fiches:
            if fiche["etat_verification"] != "VERIFIE" or (
                    fiche.get("origine_texte") == "OCR_AUTO" and not fiche.get("recoupe")):
                A.declarer_incertitude(
                    analyse, fiche["ref_id"],
                    "Texte %s%s : le contenu exact peut différer de l'exemplaire officiel."
                    % (fiche["etat_verification"],
                       ", lu par OCR non recoupé" if fiche.get("origine_texte") == "OCR_AUTO"
                       else ""))
        return analyse

    # -- restitution -----------------------------------------------------
    def _sources(self, fiches):
        sources = []
        for fiche in fiches:
            sources.append({
                "reference": fiche.get("titre_texte"),
                "numero_texte": fiche.get("numero_texte"),
                "article": fiche["article"],
                "citation": fiche["citation"],
                "url_source": fiche.get("url_source"),
                "sha256_article": fiche.get("sha256_article"),
                "etat_verification": fiche["etat_verification"],
                "origine_texte": fiche.get("origine_texte"),
                "recoupe": bool(fiche.get("recoupe")),
                "confiance_ocr": fiche.get("confiance_ocr"),
                "limites_texte": fiche.get("limites_texte"),
                "note_lecture": fiche.get("note_lecture"),
            })
        return sources

    def _restituer(self, cloture, fiches, etat):
        statut = cloture.get("statut_reponse")
        controles = cloture.get("controles_qualite") or {}
        plan = cloture.get("plan") or {}
        sections = {
            "1_faits": {
                "demande": etat.get("demande"),
                "note": ("Les faits ci-dessous sont DÉCLARÉS par vous. Aucun n'est "
                         "prouvé par une pièce dans ce dossier."),
                "declares": [f for f in (cloture.get("analyse") or {}).get("applications", [])],
            },
            "2_droit": [
                {"titre": f["titre"], "article": f["article"],
                 "numero_texte": f.get("numero_texte"),
                 "citation": f["citation"], "lecture": f.get("lecture"),
                 "note_lecture": f.get("note_lecture")} for f in fiches],
            "3_application": ("Ces textes s'appliquent SI les faits déclarés sont exacts. "
                              "Je ne peux pas vérifier les faits."),
            "4_demarches": ([e.get("objectif") for e in plan.get("etapes", [])]
                            + [f.get("etape_plan") for f in fiches if f.get("etape_plan")]),
            "5_a_verifier": ([v.get("libelle") for v in controles.get("violations", [])]
                             + list(cloture.get("champs_non_renseignes") or [])),
            "6_sources": self._sources(fiches),
        }
        guide = self._questions_guide(etat)
        reponses = etat.get("reponses") or {}
        lignes, manquantes = clarification.application(guide, reponses, self.catalogue)
        restantes = clarification.contradictions(guide, reponses, etat.get("demande"))
        sections["3_application_aux_faits"] = {
            "statut": self.guide.get("statut_validation"),
            "note": ("Lectures des articles au vu de VOS réponses. Ce ne sont pas des "
                     "citations : elles n'ont pas encore été relues par un juriste."),
            "lignes": lignes,
        }
        sections["5_informations_manquantes"] = manquantes
        sections["5_contradictions"] = [
            dict(c, message=c["message"] + " — réponse confirmée : c'est elle qui est retenue, "
                 "mais le récit et la réponse divergent : faites vérifier ce point.")
            for c in restantes]
        sections["5_a_verifier"] = (
            sections["5_a_verifier"]
            + ["Information manquante — %s (%s)" % (m["question"], m["pourquoi"])
               for m in manquantes]
            + [c["message"] for c in sections["5_contradictions"]])
        brouillon = self._brouillon(cloture, fiches, etat)
        return {
            "statut_reponse": statut,
            "sections": sections,
            "verrous_humains": controles.get("raisons_verrous_ouverts") or [],
            "actions_externes_autorisees": controles.get("actions_externes_autorisees"),
            "traceabilite": cloture.get("traceabilite"),
            "brouillon": brouillon,
            "avertissement": (cloture.get("avertissement") or AVERTISSEMENT),
        }

    def _brouillon(self, cloture, fiches, etat=None):
        """Prépare un brouillon si le module de documents le permet. Jamais envoyé."""
        fabricant = getattr(mod_documents, "generer_brouillon", None)
        if fabricant is None:
            return {"disponible": False,
                    "raison": "aucune fonction de génération de brouillon dans core.documents"}
        dossier_id = cloture.get("dossier_id")
        en_cours = self.agent.lire_en_cours(dossier_id) or {}
        faits = mod_faits.Faits.depuis_dict(en_cours.get("faits") or {})
        courrier = en_cours.get("courrier") or {}
        champs, fondement = self._champs_brouillon(fiches, (etat or {}).get("demande"),
                                                   faits, courrier)
        try:
            genere = fabricant(dossier_id, "reclamation", champs)
            texte = None
            chemin_txt = genere.get("fichier_txt") if isinstance(genere, dict) else None
            if chemin_txt and os.path.isfile(chemin_txt):
                with open(chemin_txt, encoding="utf-8") as flux:
                    texte = flux.read()
            return {"disponible": True,
                    "note": "BROUILLON — NON ENVOYÉ. À relire et compléter avant tout usage.",
                    "fondement": fondement,
                    "champs_a_completer": mod_documents.champs_manquants(champs),
                    "texte": texte,
                    "genere": genere}
        except Exception as erreur:  # noqa: BLE001 — on déclare l'échec, on ne le masque pas
            return {"disponible": False, "raison": "génération impossible : %s" % (erreur,)}

    @staticmethod
    def _champs_brouillon(fiches, demande, faits, courrier):
        """Champs du courrier, et fondement SI — et seulement si — il est vérifié.

        Fonction partagée par la première génération (fin de conversation) et
        par la régénération (`rediger_courrier`) : sans elle, les deux chemins
        divergeraient et l'un finirait par citer un texte non vérifié.
        """
        verifiees = [f for f in fiches if f.get("etat_verification") == "VERIFIE"]
        fondement = None
        if verifiees:
            premiere = verifiees[0]
            fondement = ("article %s de la loi n° %s"
                         % (premiere["article"], premiere.get("numero_texte") or "")).strip()
        champs = {
            "objet": (fiches[0]["titre"] if fiches else "Demande"),
            "demande": demande or "",
            "faits": [f.get("libelle") for f in faits.tous() if f.get("libelle")],
            "references": ["Article %s (%s)" % (f["article"], f.get("numero_texte") or "")
                           for f in fiches],
            # On n'invente ni l'identité ni l'adresse : tant qu'elles manquent,
            # le trou reste visible et la question est posée (`champs_a_completer`).
            "adresse_retour": courrier.get("expediteur")
                              or "[À COMPLÉTER : vos nom, prénom et adresse]",
            "destinataire": courrier.get("destinataire") or "",
            "pieces": courrier.get("pieces")
                      or "[À COMPLÉTER : liste des documents joints, par exemple le contrat et les reçus]",
            "fondement": fondement,
        }
        return champs, fondement

    def rediger_courrier(self, dossier_id, informations=None):
        """Regénère le courrier d'un dossier AVEC les informations fournies.

        Ne rouvre pas la conversation, ne modifie aucun fait, ne change aucun
        statut. Un dossier sans analyse aboutie est refusé : un courrier ne se
        rédige pas avant que le droit applicable ait été identifié.
        """
        en_cours = self.agent.lire_en_cours(dossier_id)
        etat = self._lire_etat(dossier_id)
        if not en_cours or not etat:
            raise ValueError("aucun dossier ouvert pour %r" % (dossier_id,))
        if etat.get("etape") != "repondu" or not etat.get("reponse"):
            raise ValueError("analyse non terminée : répondez d'abord aux questions "
                             "posées avant de rédiger un courrier")
        identifiants = etat.get("fiches") or []
        fiches = [self.catalogue[i] for i in identifiants if i in self.catalogue]
        if not fiches:
            raise ValueError("aucune fiche identifiée : le courrier ne peut pas être rédigé "
                             "avant l'analyse")
        courrier = self.agent.enregistrer_courrier(dossier_id, informations or {})
        faits = mod_faits.Faits.depuis_dict(en_cours.get("faits") or {})
        champs, fondement = self._champs_brouillon(fiches, en_cours.get("demande"), faits,
                                                   courrier)
        genere = mod_documents.generer_brouillon(dossier_id, "reclamation", champs)
        texte = None
        if genere.get("fichier_txt") and os.path.isfile(genere["fichier_txt"]):
            with open(genere["fichier_txt"], encoding="utf-8") as flux:
                texte = flux.read()
        return {"dossier_id": dossier_id, "type_document": "reclamation",
                "fondement": fondement,
                "champs_a_completer": mod_documents.champs_manquants(champs),
                "texte": texte, "genere": genere,
                "note": "BROUILLON — NON ENVOYÉ. À relire et compléter avant tout usage."}

    def _restituer_refus(self, dossier):
        return {"statut_reponse": "REFUS",
                "raison": dossier.get("refus"),
                "sections": {"1_faits": {"demande": dossier.get("demande")}},
                "avertissement": AVERTISSEMENT}

    def _restituer_sans_fiche(self, demande, domaines, du_domaine):
        """Le corpus couvre parfois le domaine sans qu'aucune fiche n'existe."""
        couverture = {}
        for ligne in corpus.articles_par_origine():
            pass
        par_domaine = {}
        for domaine in domaines:
            articles = corpus.chercher_articles(demande, domaine=domaine, limite=5)
            par_domaine[domaine] = [{"article": a["numero"], "numero_texte": a["numero_texte"],
                                     "etat_verification": a["etat_verification"]}
                                    for a in articles]
        try:
            vision = domaines_vision.reconnaitre(demande)
        except (OSError, ValueError, domaines_vision.RegistreInvalide):
            vision = []
        return {
            "statut_reponse": "CONCLUSION_IMPOSSIBLE",
            "message": ("Je ne trouve pas de fiche de réponse correspondant à votre "
                        "question. Je préfère vous le dire plutôt que de citer un article "
                        "au hasard."),
            # Domaine probable parmi les 24 de la vision, avec le nombre de fiches
            # réellement disponibles : 0 = domaine non couvert, dit comme tel.
            "domaines_vision": [{"code": v["code"], "libelle": v["libelle"],
                                 "fiches_disponibles": v["fiches_disponibles"]} for v in vision],
            "domaines_identifies": domaines,
            "articles_du_domaine_sans_fiche": par_domaine,
            "pistes_sans_fiche": [f["titre"] for f in du_domaine],
            "couverture_du_catalogue": catalogue.couverture(fiches=self.fiches),
            "avertissement": AVERTISSEMENT,
        }
