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
import os

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

from core import pseudonymisation
from core.base import normaliser as _normaliser

NOM_VARIABLE_ACCORD = "MONRECOURS_LLM_ACCORD_DONNEES"
FOURNISSEURS_COMPREHENSION = ("anthropic", "compatible_openai")
LONGUEUR_MAX_RESUME = 600

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
    classe = (adaptateur.FournisseurAnthropic if nom == "anthropic"
              else adaptateur.FournisseurCompatibleOpenAI)
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
    recit_masque, rapport["masquages"] = pseudonymisation.masquer(recit)
    try:
        texte = fournisseur.completer(_SYSTEME_COMPREHENSION,
                                      _message(recit_masque, fiches, guide), delai=delai)
        brut = _extraire_json(texte or "")
        retenu, rejets = valider_comprehension(brut, recit_masque, fiches, guide)
    except Exception as erreur:  # noqa: BLE001 — repli déterministe, jamais de panne
        rapport["erreur"] = "%s : %s" % (type(erreur).__name__, erreur)
        return rapport
    rapport.update(retenu)
    rapport["rejets"] = rejets
    if retenu["fiches"] or retenu["resume"]:
        rapport["mode"] = "llm"
    return rapport
