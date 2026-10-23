# -*- coding: utf-8 -*-
"""Interface fournisseur de langage — PRÉPARÉE, NON OPÉRATIONNELLE.

Objectif : pouvoir remplacer un jour la couche déterministe par un modèle de
langage, **sans jamais lui donner la main sur le droit**.

Principe non négociable : un fournisseur ne PRODUIT QUE DES PROPOSITIONS.
Chaque proposition est repassée par les contrôles du moteur :

    citation présente dans l'article indexé   (corpus.verifier_citation_article)
    énoncé non dépassant l'article            (corpus.verifier_enonce_contre_article)

Ce qui ne passe pas est **rejeté**, et le rejet est conservé. Un article inventé
par un modèle ne peut donc pas entrer dans une réponse.

ARCHITECTURE — LE RÉSEAU RESTE HORS DU CŒUR
-------------------------------------------
Ce module **n'importe aucun client réseau** : le garde-fou du projet veut que
`core/sources.py` soit le seul module du cœur à atteindre le réseau, et il est
maintenu. Le transport HTTP vit dans `bin/fournisseur_http.py`, chargé
paresseusement et **injecté** ici. Le cœur ne connaît donc que le contrat.

ÉTAT RÉEL : aucun fournisseur n'est configuré, aucune clé n'est présente dans le
code, aucun appel réseau n'a été effectué. `statut()["operationnel"]` vaut donc
`False`, et le restera tant qu'un appel réel n'aura pas été exécuté ET testé.

Aucune clé API dans le code : la clé est lue dans `MONRECOURS_LLM_API_KEY`.
"""

import importlib.util
import fcntl
import os
import threading

from core import corpus

NOM_VARIABLE_CLE = "MONRECOURS_LLM_API_KEY"
NOM_VARIABLE_URL = "MONRECOURS_LLM_URL"
NOM_VARIABLE_FOURNISSEUR = "MONRECOURS_LLM_FOURNISSEUR"
DELAI_PAR_DEFAUT = 8.0
RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHEMIN_ADAPTATEUR = os.path.join(RACINE, "bin", "fournisseur_http.py")


class ErreurFournisseur(Exception):
    """Erreur de transport ou de format. Ne contient jamais la clé."""


class FournisseurIndisponible(ErreurFournisseur):
    """Aucun fournisseur configuré : c'est le cas NORMAL aujourd'hui."""


class DelaiDepasse(ErreurFournisseur):
    """Le fournisseur n'a pas répondu dans le délai imparti."""


class Fournisseur(object):
    """Contrat minimal : un nom, une disponibilité, une proposition."""

    nom = "abstrait"

    def disponible(self):
        return False

    def proposer(self, demande, contexte=None, delai=DELAI_PAR_DEFAUT):
        raise FournisseurIndisponible("fournisseur abstrait : aucune implémentation")

    def statut(self):
        return {"fournisseur": self.nom, "disponible": self.disponible(),
                "operationnel": False,
                "raison": "aucune proposition réelle n'a été exécutée et testée"}


class FournisseurDesactive(Fournisseur):
    """Fournisseur par défaut : personne ne l'a configuré, et c'est voulu."""

    nom = "desactive"

    def proposer(self, demande, contexte=None, delai=DELAI_PAR_DEFAUT):
        raise FournisseurIndisponible(
            "aucun fournisseur de langage n'est configuré ; le moteur déterministe "
            "reste seul en service")


class FournisseurFactice(Fournisseur):
    """Fournisseur de TEST : répond ce qu'on lui donne, en local, sans réseau.

    Sert à prouver que les contrôles rejettent une proposition inventée. Il n'est
    jamais sélectionné par `obtenir_fournisseur()`.
    """

    nom = "factice"

    def __init__(self, reponse=None, delai_avant=0.0, erreur=None):
        self.reponse = reponse if reponse is not None else {"propositions": []}
        self.delai_avant = delai_avant
        self.erreur = erreur

    def disponible(self):
        return True

    def proposer(self, demande, contexte=None, delai=DELAI_PAR_DEFAUT):
        if self.erreur is not None:
            raise self.erreur
        if self.delai_avant > delai:
            raise DelaiDepasse("délai dépassé (factice)")
        return self.reponse


_CONSIGNE = (
    "Propose UNIQUEMENT des articles présents dans le contexte fourni, avec leur "
    "citation exacte. N'invente aucun article, aucun numéro, aucun délai. "
    "Réponds en JSON : {\"propositions\":[{\"ref_id\":..., \"article\":..., "
    "\"citation\":...}]}"
)


def charger_adaptateur_http(chemin=None):
    """Charge `bin/fournisseur_http.py` à la demande. Aucun import réseau dans le cœur.

    Retourne None si l'adaptateur est absent : le mode déterministe s'applique.
    """
    chemin = chemin or CHEMIN_ADAPTATEUR
    if not os.path.isfile(chemin):
        return None
    specification = importlib.util.spec_from_file_location("fournisseur_http", chemin)
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def obtenir_fournisseur(nom=None):
    """Sélection par variable d'environnement, avec repli déterministe."""
    nom = (nom or os.environ.get(NOM_VARIABLE_FOURNISSEUR) or "desactive").lower()
    if nom == "http":
        adaptateur = charger_adaptateur_http()
        if adaptateur is None:
            return FournisseurDesactive()
        return adaptateur.FournisseurHTTP()
    return FournisseurDesactive()


def valider_propositions(propositions, chemin_db=None):
    """Filtre les propositions par les contrôles du moteur. Rien ne passe en force.

    Renvoie (acceptees, rejets). `acceptees` contient exactement ce que le moteur
    sait vérifier : une citation réellement présente dans l'article cité.
    """
    acceptees, rejets = [], []
    for proposition in propositions or []:
        if not isinstance(proposition, dict):
            rejets.append({"proposition": proposition, "raison": "format non conforme"})
            continue
        ref_id = proposition.get("ref_id")
        article = proposition.get("article")
        citation = proposition.get("citation") or ""
        if not ref_id or article is None or not citation:
            rejets.append({"proposition": proposition,
                           "raison": "champs ref_id / article / citation incomplets"})
            continue
        texte_article = corpus.obtenir_article_par_reference(ref_id, article, chemin=chemin_db)
        if texte_article is None:
            rejets.append({"proposition": proposition,
                           "raison": "ARTICLE_INCONNU ou non citable"})
            continue
        ok, details = corpus.verifier_citation_article(ref_id, article, citation,
                                                       chemin=chemin_db)
        if not ok:
            rejets.append({"proposition": proposition,
                           "raison": "CITATION_ABSENTE : %s" % details.get("raison")})
            continue
        controle = corpus.verifier_enonce_contre_article(ref_id, article, citation,
                                                         chemin=chemin_db)
        if not controle["ok"]:
            rejets.append({"proposition": proposition,
                           "raison": "ENONCE_HORS_ARTICLE : %s" % controle["mots_absents"]})
            continue
        acceptees.append({"ref_id": ref_id, "article": str(article), "citation": citation,
                          "origine_texte": texte_article.get("origine_texte"),
                          "recoupe": bool(texte_article.get("recoupe")),
                          "sha256_article": texte_article.get("sha256_article")})
    return acceptees, rejets


def proposer_avec_repli(demande, contextes, fournisseur=None, delai=DELAI_PAR_DEFAUT,
                        chemin_db=None):
    """Tente un fournisseur, revient au déterministe en cas d'échec. Jamais bloquant.

    `contextes` : fiches du catalogue (source de vérité). Le repli consiste à les
    utiliser telles quelles — le service reste donc identique à aujourd'hui.
    """
    fournisseur = fournisseur or obtenir_fournisseur()
    rapport = {"fournisseur": fournisseur.nom, "mode": "deterministe",
               "acceptees": [], "rejets": [], "erreur": None}
    try:
        reponse = fournisseur.proposer(demande, contexte={"fiches": contextes}, delai=delai)
        propositions = (reponse or {}).get("propositions") or []
        acceptees, rejets = valider_propositions(propositions, chemin_db=chemin_db)
        rapport.update(mode="llm", acceptees=acceptees, rejets=rejets)
        if not acceptees:
            rapport["erreur"] = "aucune proposition acceptée : repli déterministe"
            rapport["mode"] = "deterministe"
    except ErreurFournisseur as erreur:
        rapport["erreur"] = str(erreur)
    except Exception as erreur:  # noqa: BLE001 — un fournisseur ne doit jamais casser le service
        rapport["erreur"] = "erreur inattendue : %s" % (erreur,)
    if rapport["mode"] == "deterministe":
        rapport["acceptees"] = [{"ref_id": f["ref_id"], "article": f["article"],
                                 "citation": f["citation"]} for f in contextes or []]
    return rapport


def statut():
    fournisseur = obtenir_fournisseur()
    etat = fournisseur.statut()
    etat["configuration"] = {"variable_cle": NOM_VARIABLE_CLE,
                             "variable_url": NOM_VARIABLE_URL,
                             "variable_fournisseur": NOM_VARIABLE_FOURNISSEUR,
                             "cle_presente": bool(os.environ.get(NOM_VARIABLE_CLE)),
                             "adaptateur_http_present": os.path.isfile(CHEMIN_ADAPTATEUR)}
    etat["budget"] = llm_budget.etat()
    etat["avertissement"] = (
        "Le mode LLM n'est PAS opérationnel : aucun appel réel n'a été validé. "
        "Le moteur déterministe reste la seule source de vérité.")
    return etat


# ===========================================================================
# COMPRÉHENSION DU RÉCIT — le modèle propose, le moteur dispose
# ===========================================================================
#
# Rôle confié au modèle (et à lui seul) : lire le récit, choisir parmi les
# fiches EXISTANTES celles qui le concernent, repérer dans le récit ce qui
# répond déjà aux questions du guide, et résumer la situation.
#
# Ce qu'il ne fait jamais : citer un article, créer une fiche, répondre à la
# place de la personne. Tout ce qu'il renvoie est contrôlé :
#   * fiches       -> identifiants présents dans le catalogue, sinon rejet ;
#   * suggestions  -> clés du guide des fiches retenues, valeur oui/non, et un
#                     EXTRAIT recopié du récit (vérifié littéralement) ;
#                     ce ne sont que des pré-remplissages que la personne confirme ;
#   * résumé       -> borné, et aucun nombre absent du récit.
# Activation : fournisseur choisi + clé + accord explicite sur l'envoi des
# données (MONRECOURS_LLM_ACCORD_DONNEES=oui). Sans les trois : déterministe.

import json as _json
import re as _re

from core import incident_llm, llm_budget, pseudonymisation
from core.base import normaliser as _normaliser

NOM_VARIABLE_ACCORD = "MONRECOURS_LLM_ACCORD_DONNEES"
FOURNISSEURS_COMPREHENSION = ("anthropic", "compatible_openai", "deepseek")
LONGUEUR_MAX_RESUME = 600
# Estimation HAUTE d'un appel : consigne + récit + 92 fiches + guide.
# Sert au plafond AVANT l'appel, jamais à la facturation (le fournisseur
# renvoie ses vrais compteurs).
JETONS_ESTIMES_PAR_APPEL = 6000

_SYSTEME_COMPREHENSION = (
    "Tu aides un service d'information juridique ivoirien. Tu ne donnes AUCUN avis "
    "juridique et tu ne cites AUCUN texte de loi. Tu lis le récit d'une personne et tu "
    "réponds UNIQUEMENT par un objet JSON, sans texte autour, de la forme : "
    "{\"fiches\": [identifiants pris dans la liste fournie, au plus 4, les plus "
    "pertinents ; liste vide si aucun ne convient], \"suggestions\": [{\"cle\": clé "
    "d'une question fournie, \"valeur\": \"oui\" ou \"non\", \"extrait\": passage "
    "RECOPIÉ MOT POUR MOT du récit qui justifie la valeur}], \"resume\": deux phrases "
    "neutres qui reformulent la situation sans rien ajouter, sans aucun nombre absent "
    "du récit}. Ne propose une suggestion que si le récit le dit clairement. "
    "N'invente ni fiche, ni clé, ni fait."
)


def comprehension_active():
    """Les trois conditions d'activation sont-elles réunies ?"""
    nom = (os.environ.get(NOM_VARIABLE_FOURNISSEUR) or "").lower()
    return (nom in FOURNISSEURS_COMPREHENSION
            and bool(os.environ.get(NOM_VARIABLE_CLE))
            and (os.environ.get(NOM_VARIABLE_ACCORD) or "").lower() == "oui")


def fournisseur_comprehension():
    """Fournisseur configuré, ou None (mode déterministe)."""
    if not comprehension_active():
        return None
    adaptateur = charger_adaptateur_http()
    if adaptateur is None:
        return None
    nom = os.environ.get(NOM_VARIABLE_FOURNISSEUR).lower()
    classes = {
        "anthropic": getattr(adaptateur, "FournisseurAnthropic", None),
        "deepseek": getattr(adaptateur, "FournisseurDeepSeek", None),
        "compatible_openai": getattr(adaptateur, "FournisseurCompatibleOpenAI", None),
    }
    classe = classes.get(nom)
    if classe is None:
        return None
    fournisseur = classe()
    return fournisseur if fournisseur.disponible() else None


def _message(recit, fiches, guide):
    lignes = ["RÉCIT :", recit, "", "FICHES DISPONIBLES (identifiant — sujet) :"]
    lignes += ["%s — %s" % (f["id"], f["titre"]) for f in fiches]
    lignes += ["", "QUESTIONS (clé — question — fiches concernées) :"]
    lignes += ["%s — %s — %s" % (q["cle"], q["question"], ", ".join(q["fiches"]))
               for q in guide.get("questions", [])]
    return "\n".join(lignes)


def _extraire_json(texte):
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut < 0 or fin <= debut:
        raise ValueError("aucun objet JSON dans la réponse")
    return _json.loads(texte[debut:fin + 1])


_NOMBRE = _re.compile(r"\b\d+\b")
_MOTS_NOMBRES = ("deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
                 "onze", "douze", "quinze", "vingt", "trente", "cent", "mille")


def _nombres(texte):
    t = _normaliser(texte)
    trouves = set(_NOMBRE.findall(t))
    mots = set(_re.findall(r"[a-z]+", t))
    return trouves | {m for m in _MOTS_NOMBRES if m in mots}


def valider_comprehension(brut, recit, fiches, guide):
    """Ne garde que ce que le moteur peut vérifier. Renvoie (retenu, rejets)."""
    index = {f["id"]: f for f in fiches}
    rejets = []
    retenues = []
    for fid in (brut.get("fiches") or [])[:4]:
        if isinstance(fid, str) and fid in index:
            if fid not in retenues:
                retenues.append(fid)
        else:
            rejets.append({"element": "fiche", "valeur": fid, "raison": "absente du catalogue"})
    cles_permises = {q["cle"] for q in guide.get("questions", [])
                     if set(q["fiches"]) & set(retenues)}
    recit_norm = _normaliser(recit)
    suggestions = {}
    for s in brut.get("suggestions") or []:
        if not isinstance(s, dict):
            rejets.append({"element": "suggestion", "valeur": s, "raison": "format"})
            continue
        cle, valeur, extrait = s.get("cle"), s.get("valeur"), s.get("extrait") or ""
        if cle not in cles_permises:
            rejets.append({"element": "suggestion", "valeur": cle,
                           "raison": "clé hors des questions des fiches retenues"})
        elif valeur not in ("oui", "non"):
            rejets.append({"element": "suggestion", "valeur": cle, "raison": "valeur"})
        elif len(_normaliser(extrait)) < 4 or _normaliser(extrait) not in recit_norm:
            rejets.append({"element": "suggestion", "valeur": cle,
                           "raison": "extrait absent du récit (non recopié)"})
        else:
            suggestions[cle] = {"valeur": valeur, "indice": extrait.strip()}
    resume = brut.get("resume")
    if not isinstance(resume, str) or not resume.strip():
        resume = None
    elif len(resume) > LONGUEUR_MAX_RESUME:
        rejets.append({"element": "resume", "raison": "trop long"})
        resume = None
    elif _nombres(resume) - _nombres(recit):
        rejets.append({"element": "resume",
                       "raison": "nombre absent du récit : %s"
                                 % ", ".join(sorted(_nombres(resume) - _nombres(recit)))})
        resume = None
    return {"fiches": retenues, "suggestions": suggestions, "resume": resume}, rejets


def comprendre(recit, fiches, guide, fournisseur=None, delai=DELAI_PAR_DEFAUT):
    """Compréhension assistée, avec repli. Ne lève jamais.

    Renvoie un rapport : `mode` (« llm » ou « deterministe »), `fiches`,
    `suggestions`, `resume`, `rejets`, `erreur`, `masquages`.
    """
    rapport = {"mode": "deterministe", "fournisseur": None, "fiches": [],
               "suggestions": {}, "resume": None, "rejets": [], "erreur": None,
               "masquages": 0}
    fournisseur = fournisseur if fournisseur is not None else fournisseur_comprehension()
    if fournisseur is None:
        rapport["erreur"] = "aucun fournisseur actif"
        return rapport
    rapport["fournisseur"] = getattr(fournisseur, "nom", "inconnu")
    # Garde-fou AVANT l'appel : plafond journalier et disjoncteur. Rien n'est
    # envoyé, le service continue en déterministe, le citoyen reçoit sa réponse.
    if not llm_budget.peut_appeler(JETONS_ESTIMES_PAR_APPEL):
        rapport["erreur"] = "garde-fou : plafond journalier atteint ou fournisseur en panne"
        return rapport
    # Incident ouvert (crédits épuisés) : plus aucun appel inutile tant que le
    # solde n'a pas été vérifié. Le service continue en déterministe.
    if incident_llm.ouvert():
        rapport["erreur"] = "incident ouvert : crédits du fournisseur épuisés"
        return rapport
    recit_masque, rapport["masquages"] = pseudonymisation.masquer(recit)
    try:
        texte = fournisseur.completer(_SYSTEME_COMPREHENSION,
                                      _message(recit_masque, fiches, guide), delai=delai)
        consommation = getattr(fournisseur, "derniere_consommation", None) or {}
        llm_budget.enregistrer(consommation.get("entree", 0), consommation.get("sortie", 0))
        llm_budget.signaler_succes()
        brut = _extraire_json(texte or "")
        retenu, rejets = valider_comprehension(brut, recit_masque, fiches, guide)
    except Exception as erreur:  # noqa: BLE001 — repli déterministe, jamais de panne
        llm_budget.signaler_echec()
        # Épuisement de crédits : ce n'est PAS une panne réseau. On l'identifie sur
        # le STATUT ET LE MESSAGE du fournisseur — jamais sur un code seul. Un 402
        # sans mention de solde, ou un 429 (débit dépassé), restent des erreurs.
        statut = getattr(erreur, "statut_http", None)
        detail = getattr(erreur, "message_fournisseur", "") or ""
        if statut == 402 and incident_llm.message_credits(detail):
            nouveau = incident_llm.declarer(getattr(fournisseur, "nom", "deepseek"), detail, statut)
            rapport["erreur"] = "crédits du fournisseur épuisés"
            rapport["incident_nouveau"] = nouveau
            return rapport
        rapport["erreur"] = "%s : %s" % (type(erreur).__name__, erreur)
        return rapport
    rapport.update(retenu)
    rapport["rejets"] = rejets
    if retenu["fiches"] or retenu["resume"]:
        rapport["mode"] = "llm"
    return rapport


# ---------------------------------------------------------------------------
# Réactivation après épuisement des crédits
# ---------------------------------------------------------------------------

NOM_VARIABLE_VERROU = "MONRECOURS_VERROU_SOLDE"
DUREE_VERROU = 30.0


_VERROU_PROCESSUS = threading.Lock()


def _verrouiller():
    """Verrou exclusif : deux clics simultanés ne produisent qu'une vérification.

    Renvoie un jeton opaque, ou None si une vérification est déjà en cours.

    Le verrou de fichier protège contre plusieurs processus. S'il ne peut pas
    être créé (RUNTIME absent ou en lecture seule), on ne répond PAS « déjà en
    cours » pour toujours — c'était le comportement précédent, qui rendait la
    réactivation impossible en production : on se replie sur un verrou du
    processus, suffisant puisque le moteur tourne dans un seul processus.
    """
    if not _VERROU_PROCESSUS.acquire(blocking=False):
        return None
    chemin = os.environ.get(NOM_VARIABLE_VERROU) or os.path.join(RACINE, "RUNTIME", "verification_solde.lock")
    try:
        os.makedirs(os.path.dirname(chemin), mode=0o700, exist_ok=True)
        descripteur = os.open(chemin, os.O_CREAT | os.O_RDWR, 0o600)
    except OSError:
        return {"fichier": None}
    try:
        fcntl.flock(descripteur, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        os.close(descripteur)
        _VERROU_PROCESSUS.release()
        return None
    return {"fichier": descripteur}


def _deverrouiller(jeton):
    try:
        descripteur = jeton.get("fichier") if isinstance(jeton, dict) else None
        if descripteur is not None:
            try:
                fcntl.flock(descripteur, fcntl.LOCK_UN)
            finally:
                os.close(descripteur)
    finally:
        _VERROU_PROCESSUS.release()


def configuration_manquante():
    """Ce qui empêche une activation — jamais une clé, seulement des noms."""
    manques = []
    nom = (os.environ.get(NOM_VARIABLE_FOURNISSEUR) or "").lower()
    if nom not in FOURNISSEURS_COMPREHENSION:
        manques.append("fournisseur non configuré")
    if not os.environ.get(NOM_VARIABLE_CLE):
        manques.append("clé absente")
    if (os.environ.get(NOM_VARIABLE_ACCORD) or "").lower() != "oui":
        manques.append("accord de traitement des données non donné")
    return manques


def verifier_solde_et_reactiver(delai=10.0, verificateur=None):
    """Interroge le solde officiel et ne rétablit QUE sur preuve.

    Rien n'est supposé : si la réponse est ambiguë, si le réseau échoue ou si la
    configuration est incomplète, l'incident reste ouvert et le moteur
    déterministe continue. Aucun succès fictif n'est jamais renvoyé.
    """
    resultat = {"reactive": False, "mode": "deterministe", "etat": None,
                "manques": configuration_manquante(),
                "methode": "GET https://api.deepseek.com/user/balance"}

    if (os.environ.get(NOM_VARIABLE_FOURNISSEUR) or "").lower() != "deepseek":
        # La vérification interroge l'API de solde de DeepSeek avec la clé
        # configurée : si le fournisseur configuré est un autre, cette clé n'est
        # pas une clé DeepSeek et ne doit JAMAIS être envoyée à DeepSeek.
        resultat["etat"] = "NON_APPLICABLE"
        resultat["message"] = ("Le fournisseur configuré n'est pas DeepSeek : aucune "
                               "vérification de solde n'est faite, l'incident reste en l'état.")
        resultat["incident"] = incident_llm.etat()
        return resultat

    if "clé absente" in resultat["manques"]:
        resultat["etat"] = "SANS_CLE"
        resultat["message"] = "Aucune clé configurée : le solde ne peut pas être vérifié."
        resultat["incident"] = incident_llm.etat()
        return resultat

    verrou = _verrouiller()
    if verrou is None:
        resultat["etat"] = "EN_COURS"
        resultat["message"] = "Une vérification est déjà en cours."
        resultat["incident"] = incident_llm.etat()
        return resultat
    try:
        if verificateur is None:
            adaptateur = charger_adaptateur_http()
            classe = getattr(adaptateur, "FournisseurDeepSeek", None) if adaptateur else None
            if classe is None:
                resultat["etat"] = "ERREUR"
                resultat["message"] = "Adaptateur indisponible."
                resultat["incident"] = incident_llm.etat()
                return resultat
            verificateur = classe().verifier_solde
        try:
            solde = verificateur(delai=delai)
        except Exception as erreur:  # noqa: BLE001 — une panne ne ferme jamais l'incident
            resultat["etat"] = "ERREUR"
            resultat["message"] = ("Vérification impossible : l'incident reste ouvert, "
                                   "le secours déterministe continue.")
            resultat["incident"] = incident_llm.etat()
            return resultat
        resultat["etat"] = solde.get("etat")
        resultat["devise"] = solde.get("devise")
        resultat["solde"] = solde.get("total")

        if solde.get("etat") == "POSITIF" and not resultat["manques"]:
            incident_llm.resoudre("solde vérifié : %s %s" % (solde.get("total"), solde.get("devise") or ""))
            resultat["reactive"] = not incident_llm.ouvert()
            resultat["mode"] = "llm" if resultat["reactive"] else "deterministe"
            if not resultat["reactive"]:
                resultat["message"] = "La clôture de l'incident a échoué : le secours déterministe continue."
            elif not incident_llm.etat().get("persistant", True):
                resultat["message"] = ("Solde confirmé : compréhension assistée réactivée pour ce "
                                       "processus, mais l'état n'a pas pu être enregistré sur disque "
                                       "(droits du dossier RUNTIME à corriger).")
            else:
                resultat["message"] = "Solde confirmé : compréhension assistée réactivée."
        elif solde.get("etat") == "POSITIF":
            resultat["message"] = ("Solde confirmé, mais la configuration est incomplète : "
                                   "DeepSeek reste désactivé.")
        elif solde.get("etat") == "EPUISE":
            resultat["message"] = "Solde épuisé : l'incident reste ouvert, le secours déterministe continue."
        elif solde.get("etat") == "AMBIGU":
            resultat["message"] = ("Réponse du fournisseur inexploitable : l'incident reste ouvert.")
        else:
            resultat["message"] = ("Vérification impossible : l'incident reste ouvert, "
                                   "le secours déterministe continue.")
        resultat["incident"] = incident_llm.etat()
        return resultat
    finally:
        _deverrouiller(verrou)


# ---------------------------------------------------------------------------
# Explication en langage simple (après la citation des textes)
# ---------------------------------------------------------------------------
#
# Le moteur CITE les articles mot pour mot ; beaucoup de citoyens ne les
# comprennent pas. Le modèle les EXPLIQUE ensuite, en français simple, sans
# rien ajouter au droit. Ce qu'il propose est contrôlé comme le reste :
#   * il n'explique que les articles RETENUS par le moteur (aucun autre) ;
#   * aucun nombre (délai, montant, numéro d'article ou de loi) qui ne figure
#     pas dans les citations, les titres, le récit, les réponses ou les
#     démarches fournies ;
#   * aucune mention d'un article autre que ceux retenus ;
#   * aucune promesse de résultat ;
#   * les étapes ne sont que des reformulations des démarches déjà produites
#     par le moteur (référencées par leur numéro) ;
#   * longueurs bornées.
# Tout élément qui échoue est écarté (et consigné) ; si rien ne tient, la page
# garde la citation et la lecture déterministe de la fiche. Ne lève jamais.

LONGUEUR_MAX_EXPLICATION = 700
LONGUEUR_MAX_POUR_VOUS = 900
LONGUEUR_MAX_ETAPE = 260
JETONS_ESTIMES_EXPLICATION = 3000

_SYSTEME_EXPLICATION = (
    "Tu aides un service d'information juridique ivoirien à EXPLIQUER, en français très "
    "simple (phrases courtes, mots de tous les jours, pas de jargon), des articles de loi "
    "DÉJÀ cités à une personne qui n'est pas juriste. Tu n'utilises QUE les textes fournis. "
    "Tu n'ajoutes AUCUN article, AUCUNE loi, AUCUN délai, AUCUN montant, AUCUN nombre qui "
    "n'apparaît pas dans les textes, le récit, les réponses ou les démarches fournies. Tu "
    "parles au conditionnel pour la situation de la personne (« si ce que vous décrivez est "
    "exact… »). Tu ne promets jamais de résultat. Réponds UNIQUEMENT par un objet JSON, sans "
    "texte autour, de la forme : {\"explications\": [{\"article\": numéro d'article fourni, "
    "\"en_clair\": deux à quatre phrases qui disent ce que l'article signifie concrètement}], "
    "\"pour_vous\": trois à cinq phrases qui relient ces articles à la situation décrite, au "
    "conditionnel, en disant aussi ce qui reste incertain, \"etapes\": [{\"numero\": numéro "
    "d'une démarche fournie, \"en_clair\": la même démarche reformulée simplement}]}."
)

_PROMESSES = ("vous allez gagner", "vous gagnerez", "c'est garanti", "est garanti", "garantie de",
              "sans aucun doute", "a coup sur", "à coup sûr", "100 %", "100%", "certainement gain")
_ARTICLE_CITE = _re.compile(r"\barticles?\s+(?:n[°o]\s*)?(\d+)", _re.IGNORECASE)


def _message_explication(recit, lignes_reponses, fiches, demarches):
    lignes = ["RÉCIT DE LA PERSONNE :", recit or "(non fourni)", "", "SES RÉPONSES :"]
    lignes += ["- %s %s" % (q, r) for q, r in lignes_reponses] or ["(aucune)"]
    lignes += ["", "ARTICLES CITÉS (à expliquer) :"]
    for f in fiches:
        lignes.append("Article %s (texte n° %s) — %s :\n« %s »"
                      % (f.get("article"), f.get("numero_texte") or "?", f.get("titre"), f.get("citation")))
    lignes += ["", "DÉMARCHES PROPOSÉES PAR LE SERVICE (numéro — démarche) :"]
    lignes += ["%d — %s" % (i + 1, d) for i, d in enumerate(demarches)] or ["(aucune)"]
    return "\n".join(lignes)


def _texte_autorise(texte, nombres_permis, articles_permis, maximum):
    """Renvoie la raison du refus, ou None si le texte est acceptable."""
    if not isinstance(texte, str) or not texte.strip():
        return "vide"
    if len(texte) > maximum:
        return "trop long"
    inconnus = _nombres(texte) - nombres_permis
    if inconnus:
        return "nombre absent des sources : %s" % ", ".join(sorted(inconnus))
    autres = {n for n in _ARTICLE_CITE.findall(texte)} - articles_permis
    if autres:
        return "article non retenu : %s" % ", ".join(sorted(autres))
    bas = _normaliser(texte)
    if any(_normaliser(p) in bas for p in _PROMESSES):
        return "promesse de résultat"
    return None


def valider_explication(brut, recit, lignes_reponses, fiches, demarches):
    """Ne garde que ce qui reste fidèle aux sources. Renvoie (retenu, rejets)."""
    sources = " ".join([recit or ""]
                       + ["%s %s" % (q, r) for q, r in lignes_reponses]
                       + ["%s %s %s %s" % (f.get("titre"), f.get("article"), f.get("numero_texte") or "",
                                           f.get("citation")) for f in fiches]
                       + list(demarches))
    nombres_permis = _nombres(sources)
    articles_permis = {str(f.get("article")) for f in fiches}
    rejets = []
    explications = []
    for e in (brut.get("explications") or [])[:len(fiches)]:
        if not isinstance(e, dict):
            rejets.append({"element": "explication", "raison": "format"})
            continue
        article = str(e.get("article") or "").strip()
        fiche = next((f for f in fiches if str(f.get("article")) == article), None)
        if fiche is None:
            rejets.append({"element": "explication", "valeur": article, "raison": "article non retenu"})
            continue
        raison = _texte_autorise(e.get("en_clair"), nombres_permis, articles_permis, LONGUEUR_MAX_EXPLICATION)
        if raison:
            rejets.append({"element": "explication", "valeur": article, "raison": raison})
            continue
        if any(x["article"] == article for x in explications):
            continue
        explications.append({"article": article, "numero_texte": fiche.get("numero_texte"),
                             "titre": fiche.get("titre"), "en_clair": e["en_clair"].strip()})
    pour_vous = brut.get("pour_vous")
    raison = _texte_autorise(pour_vous, nombres_permis, articles_permis, LONGUEUR_MAX_POUR_VOUS)
    if raison:
        if pour_vous:
            rejets.append({"element": "pour_vous", "raison": raison})
        pour_vous = None
    else:
        pour_vous = pour_vous.strip()
    etapes = []
    for e in (brut.get("etapes") or [])[:len(demarches)]:
        try:
            numero = int(e.get("numero")) if isinstance(e, dict) else 0
        except (TypeError, ValueError):
            numero = 0
        if not 1 <= numero <= len(demarches):
            rejets.append({"element": "etape", "valeur": numero, "raison": "démarche inconnue"})
            continue
        raison = _texte_autorise(e.get("en_clair"), nombres_permis, articles_permis, LONGUEUR_MAX_ETAPE)
        if raison:
            rejets.append({"element": "etape", "valeur": numero, "raison": raison})
            continue
        if numero not in {x["numero"] for x in etapes}:
            etapes.append({"numero": numero, "en_clair": e["en_clair"].strip()})
    etapes.sort(key=lambda x: x["numero"])
    return {"explications": explications, "pour_vous": pour_vous, "etapes": etapes}, rejets


def expliquer(recit, lignes_reponses, fiches, demarches, fournisseur=None, delai=DELAI_PAR_DEFAUT):
    """Explication simple des articles cités, avec repli. Ne lève jamais.

    Renvoie {"mode": "llm"|"deterministe", "explications", "pour_vous", "etapes",
    "rejets", "erreur"}. En mode déterministe, rien n'est inventé : la page garde
    les citations et les lectures des fiches.
    """
    rapport = {"mode": "deterministe", "explications": [], "pour_vous": None, "etapes": [],
               "rejets": [], "erreur": None}
    if not fiches:
        rapport["erreur"] = "aucun article à expliquer"
        return rapport
    fournisseur = fournisseur if fournisseur is not None else fournisseur_comprehension()
    if fournisseur is None:
        rapport["erreur"] = "aucun fournisseur actif"
        return rapport
    if not llm_budget.peut_appeler(JETONS_ESTIMES_EXPLICATION):
        rapport["erreur"] = "garde-fou : plafond journalier atteint ou fournisseur en panne"
        return rapport
    if incident_llm.ouvert():
        rapport["erreur"] = "incident ouvert : crédits du fournisseur épuisés"
        return rapport
    recit_masque, _ = pseudonymisation.masquer(recit or "")
    reponses_masquees = [(q, pseudonymisation.masquer(str(r))[0]) for q, r in lignes_reponses]
    try:
        texte = fournisseur.completer(
            _SYSTEME_EXPLICATION,
            _message_explication(recit_masque, reponses_masquees, fiches, demarches),
            delai=delai, max_tokens=1100)
        consommation = getattr(fournisseur, "derniere_consommation", None) or {}
        llm_budget.enregistrer(consommation.get("entree", 0), consommation.get("sortie", 0))
        llm_budget.signaler_succes()
        retenu, rejets = valider_explication(_extraire_json(texte or ""), recit_masque,
                                             reponses_masquees, fiches, demarches)
    except Exception as erreur:  # noqa: BLE001 — repli : la citation reste, rien n'est inventé
        llm_budget.signaler_echec()
        statut = getattr(erreur, "statut_http", None)
        detail = getattr(erreur, "message_fournisseur", "") or ""
        if statut == 402 and incident_llm.message_credits(detail):
            incident_llm.declarer(getattr(fournisseur, "nom", "deepseek"), detail, statut)
            rapport["erreur"] = "crédits du fournisseur épuisés"
            return rapport
        rapport["erreur"] = "%s : %s" % (type(erreur).__name__, str(erreur)[:200])
        return rapport
    rapport.update(retenu)
    rapport["rejets"] = rejets
    if retenu["explications"] or retenu["pour_vous"]:
        rapport["mode"] = "llm"
    return rapport
