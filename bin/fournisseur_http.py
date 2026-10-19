# -*- coding: utf-8 -*-
"""Adaptateur HTTP du fournisseur de langage — HORS DU CŒUR, NON ÉPROUVÉ EN RÉEL.

Pourquoi ici et pas dans `core/` : le garde-fou du projet impose que
`core/sources.py` soit le seul module du cœur à atteindre le réseau. Cet
adaptateur est donc un module de bordure, chargé paresseusement par
`core.llm.obtenir_fournisseur()` et injecté — jamais importé par le cœur.

Ce qui est testé : le transport (délai, erreurs, JSON invalide, absence de clé).
Ce qui n'est PAS testé : un vrai service. Aucun fournisseur payant n'a été
activé, aucune dépense engagée, aucun appel réel effectué.

Aucune clé dans ce fichier : elle vient de `MONRECOURS_LLM_API_KEY`.
"""

import json
import os
import socket
import urllib.error
import urllib.request

NOM_VARIABLE_CLE = "MONRECOURS_LLM_API_KEY"
NOM_VARIABLE_URL = "MONRECOURS_LLM_URL"
DELAI_PAR_DEFAUT = 8.0

CONSIGNE = (
    "Propose UNIQUEMENT des articles présents dans le contexte fourni, avec leur "
    "citation exacte. N'invente aucun article, aucun numéro, aucun délai. "
    "Réponds en JSON : {\"propositions\":[{\"ref_id\":..., \"article\":..., "
    "\"citation\":...}]}"
)


class ErreurTransport(Exception):
    pass


class FournisseurHTTP(object):
    nom = "http"

    def __init__(self, url=None, cle=None, delai=DELAI_PAR_DEFAUT):
        self.url = url if url is not None else os.environ.get(NOM_VARIABLE_URL, "")
        self._cle = cle if cle is not None else os.environ.get(NOM_VARIABLE_CLE, "")
        self.delai = delai

    def disponible(self):
        return bool(self.url and self._cle)

    def statut(self):
        return {"fournisseur": self.nom, "disponible": self.disponible(),
                "operationnel": False,
                "raison": "transport écrit mais aucun appel réel exécuté et testé"}

    def proposer(self, demande, contexte=None, delai=None):
        if not self.disponible():
            raise ErreurTransport("URL ou clé absente de l'environnement")
        charge = json.dumps({"demande": demande, "contexte": contexte or {},
                             "consigne": CONSIGNE}).encode("utf-8")
        requete = urllib.request.Request(
            self.url, data=charge, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer %s" % self._cle})
        try:
            with urllib.request.urlopen(requete, timeout=delai or self.delai) as reponse:
                return json.loads(reponse.read().decode("utf-8"))
        except (socket.timeout, TimeoutError) as erreur:
            raise ErreurTransport("délai dépassé") from erreur
        except urllib.error.URLError as erreur:
            # `erreur.reason` peut contenir l'URL, jamais la clé d'authentification.
            raise ErreurTransport("transport : %s" % (erreur.reason,)) from erreur
        except ValueError as erreur:
            raise ErreurTransport("réponse non JSON") from erreur


# ---------------------------------------------------------------------------
# Fournisseurs de « complétion » utilisés par `core.llm.comprendre`.
#
# Même règles : aucune clé dans le code (variable d'environnement), délai borné,
# erreurs traduites en `ErreurTransport` sans jamais recopier la clé.
# L'URL de base est surchargeable (`MONRECOURS_LLM_URL`) : les tests pointent
# vers un faux serveur local ; en production, l'URL officielle du fournisseur.
# ---------------------------------------------------------------------------

NOM_VARIABLE_MODELE = "MONRECOURS_LLM_MODELE"


def _poster(url, entetes, corps, delai):
    requete = urllib.request.Request(
        url, data=json.dumps(corps).encode("utf-8"), method="POST",
        headers=dict({"Content-Type": "application/json"}, **entetes))
    try:
        with urllib.request.urlopen(requete, timeout=delai) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except urllib.error.HTTPError as erreur:
        # Le corps d'erreur du fournisseur n'est pas recopié (il peut être long) :
        # seul le statut HTTP est rapporté.
        raise ErreurTransport("le fournisseur a répondu HTTP %s" % erreur.code) from erreur
    except (socket.timeout, TimeoutError) as erreur:
        raise ErreurTransport("délai dépassé") from erreur
    except urllib.error.URLError as erreur:
        raise ErreurTransport("transport : %s" % (erreur.reason,)) from erreur
    except ValueError as erreur:
        raise ErreurTransport("réponse non JSON") from erreur


class FournisseurAnthropic(object):
    """API Messages d'Anthropic (Claude). Modèle par défaut : le moins coûteux."""

    nom = "anthropic"
    URL_DEFAUT = "https://api.anthropic.com/v1/messages"
    MODELE_DEFAUT = "claude-haiku-5-5"

    def __init__(self, url=None, cle=None, modele=None, delai=DELAI_PAR_DEFAUT):
        self.url = url or os.environ.get(NOM_VARIABLE_URL) or self.URL_DEFAUT
        self._cle = cle if cle is not None else os.environ.get(NOM_VARIABLE_CLE, "")
        self.modele = modele or os.environ.get(NOM_VARIABLE_MODELE) or self.MODELE_DEFAUT
        self.delai = delai

    def disponible(self):
        return bool(self._cle)

    def completer(self, systeme, message, delai=None, max_tokens=1200):
        if not self.disponible():
            raise ErreurTransport("clé absente de l'environnement")
        donnees = _poster(
            self.url,
            {"x-api-key": self._cle, "anthropic-version": "2023-06-01"},
            {"model": self.modele, "max_tokens": max_tokens, "temperature": 0,
             "system": systeme, "messages": [{"role": "user", "content": message}]},
            delai or self.delai)
        try:
            return "".join(b.get("text", "") for b in donnees["content"] if b.get("type") == "text")
        except (KeyError, TypeError, AttributeError) as erreur:
            raise ErreurTransport("réponse du fournisseur au format inattendu") from erreur


class FournisseurCompatibleOpenAI(object):
    """Toute API « chat/completions » compatible (OpenAI, Mistral, serveur local…)."""

    nom = "compatible_openai"

    def __init__(self, url=None, cle=None, modele=None, delai=DELAI_PAR_DEFAUT):
        self.url = url or os.environ.get(NOM_VARIABLE_URL, "")
        self._cle = cle if cle is not None else os.environ.get(NOM_VARIABLE_CLE, "")
        self.modele = modele or os.environ.get(NOM_VARIABLE_MODELE, "")
        self.delai = delai

    def disponible(self):
        return bool(self.url and self._cle and self.modele)

    def completer(self, systeme, message, delai=None, max_tokens=1200):
        if not self.disponible():
            raise ErreurTransport("URL, clé ou modèle absent de l'environnement")
        donnees = _poster(
            self.url, {"Authorization": "Bearer %s" % self._cle},
            {"model": self.modele, "max_tokens": max_tokens, "temperature": 0,
             "messages": [{"role": "system", "content": systeme},
                          {"role": "user", "content": message}]},
            delai or self.delai)
        try:
            return donnees["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as erreur:
            raise ErreurTransport("réponse du fournisseur au format inattendu") from erreur
