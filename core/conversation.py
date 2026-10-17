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
from core import base, catalogue, corpus, documents as mod_documents
from core import faits as mod_faits

FICHIER_ETAT = "CONVERSATION.json"

# Ce que la couche ne sait pas faire, dit à l'utilisateur avant toute réponse.
AVERTISSEMENT = (
    "Je suis un service d'information juridique, pas un avocat. Je ne réponds que "
    "sur les textes enregistrés dans mon corpus, et je dis quand je ne peux pas."
)


class Conversation(object):
    """Une conversation = un dossier. L'état est écrit sur disque, jamais en mémoire."""

    def __init__(self, chemin_db=None, chemin_sources=None, fiches=None):
        self.agent = MonRecoursCI(chemin_db=chemin_db, chemin_sources=chemin_sources)
        self.chemin_db = path = (chemin_db or str(config.CHEMIN_DB))
        self.fiches = fiches if fiches is not None else catalogue.charger(chemin_db=path)
        self.catalogue = {f["id"]: f for f in self.fiches}

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
        os.makedirs(os.path.dirname(chemin), exist_ok=True)
        with open(chemin, "w", encoding="utf-8") as flux:
            json.dump(etat, flux, ensure_ascii=False, indent=1)
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
            demande, domaines, fiches=self.fiches, chemin_db=self.chemin_db)

        if not retenues:
            # Aucun déclencheur ne tombe : on ne sert PAS d'articles au hasard.
            etat = {"dossier_id": dossier_id, "demande": demande, "tour": 1,
                    "fiches": [], "questions": [], "etape": "hors_catalogue",
                    "domaines": domaines}
            self._ecrire_etat(dossier_id, etat)
            return {"etape": "hors_catalogue", "dossier_id": dossier_id,
                    "reponse": self._restituer_sans_fiche(demande, domaines, du_domaine),
                    "domaines": domaines}

        questions, deja = [], set()
        for fiche in retenues:
            for cle, question in fiche.get("faits_requis", []):
                if cle not in deja:
                    deja.add(cle)
                    questions.append({"cle": cle, "question": question})
        etat = {"dossier_id": dossier_id, "demande": demande, "tour": 1,
                "fiches": [f["id"] for f in retenues], "questions": questions,
                "etape": "clarification", "domaines": domaines}
        self._ecrire_etat(dossier_id, etat)
        return {"etape": "clarification", "dossier_id": dossier_id,
                "avertissement": AVERTISSEMENT,
                "urgence": dossier.get("urgence"),
                "verrous_humains": dossier.get("verrous_humains"),
                "fiches_identifiees": [
                    {"titre": f["titre"], "article": f["article"],
                     "numero_texte": f.get("numero_texte"),
                     "etat_verification": f["etat_verification"]} for f in retenues],
                "questions": questions,
                "note_corpus": dossier.get("note_corpus")}

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

        fiches = [self.catalogue[i] for i in etat["fiches"] if i in self.catalogue]
        if not fiches:
            return {"etape": "erreur", "erreur": "AUCUNE_FICHE",
                    "message": "Aucune fiche n'est associée à ce dossier."}

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
        champs = {
            "objet": (fiches[0]["titre"] if fiches else "Demande"),
            "demande": (etat or {}).get("demande") or "",
            "faits": [f.get("libelle") for f in faits.tous() if f.get("libelle")],
            "references": ["Article %s (%s)" % (f["article"], f.get("numero_texte") or "")
                           for f in fiches],
            # Champ laissé explicitement à compléter : on n'invente pas l'identité
            # ni l'adresse de l'utilisateur.
            "adresse_retour": "[À COMPLÉTER : vos nom, prénom et adresse]",
            "pieces": "[À COMPLÉTER : liste des documents joints, par exemple le contrat et les reçus]",
        }
        try:
            genere = fabricant(dossier_id, "reclamation", champs)
            texte = None
            chemin_txt = genere.get("fichier_txt") if isinstance(genere, dict) else None
            if chemin_txt and os.path.isfile(chemin_txt):
                with open(chemin_txt, encoding="utf-8") as flux:
                    texte = flux.read()
            # `texte` : le contenu du brouillon, pour l'afficher à l'utilisateur
            # (les chemins de fichiers restent dans `genere`, côté serveur).
            return {"disponible": True,
                    "note": "BROUILLON — NON ENVOYÉ. À relire et compléter avant tout usage.",
                    "texte": texte,
                    "genere": genere}
        except Exception as erreur:  # noqa: BLE001 — on déclare l'échec, on ne le masque pas
            return {"disponible": False, "raison": "génération impossible : %s" % (erreur,)}

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
        return {
            "statut_reponse": "CONCLUSION_IMPOSSIBLE",
            "message": ("Je ne trouve pas de fiche de réponse correspondant à votre "
                        "question. Je préfère vous le dire plutôt que de citer un article "
                        "au hasard."),
            "domaines_identifies": domaines,
            "articles_du_domaine_sans_fiche": par_domaine,
            "pistes_sans_fiche": [f["titre"] for f in du_domaine],
            "couverture_du_catalogue": catalogue.couverture(fiches=self.fiches),
            "avertissement": AVERTISSEMENT,
        }
