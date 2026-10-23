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

import decimal
import json
import os
import socket
import urllib.error
import urllib.parse
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
    """Erreur de transport, SANS détail sensible.

    `statut_http` et `message_fournisseur` sont renseignés quand le fournisseur a
    répondu : le cœur s'en sert pour distinguer un épuisement de crédits d'une
    simple panne. Le corps brut n'est jamais conservé au-delà de 400 caractères et
    ne contient pas la clé.
    """

    statut_http = None
    message_fournisseur = ""
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


def _poster_api(url, entetes, corps, delai, libelles=None):
    """POST JSON avec des messages d'erreur LISIBLES et sans fuite.

    Le corps d'erreur du fournisseur n'est jamais recopié : il peut contenir
    l'extrait de requête, donc du texte citoyen. On ne rapporte que le statut,
    traduit en clair. Aucun en-tête d'authentification n'entre dans le message.
    """
    requete = urllib.request.Request(
        url, data=json.dumps(corps).encode("utf-8"), method="POST",
        headers=dict({"Content-Type": "application/json"}, **entetes))
    try:
        with urllib.request.urlopen(requete, timeout=delai) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except urllib.error.HTTPError as erreur:
        libelle = (libelles or {}).get(erreur.code, "HTTP %s" % erreur.code)
        detail = ""
        try:
            detail = erreur.read(400).decode("utf-8", "replace")
        except Exception:  # noqa: BLE001 — le détail est un bonus, jamais bloquant
            detail = ""
        levee = ErreurTransport("fournisseur : %s" % libelle)
        levee.statut_http = erreur.code
        levee.message_fournisseur = detail
        raise levee from erreur
    except (socket.timeout, TimeoutError) as erreur:
        raise ErreurTransport("délai dépassé") from erreur
    except urllib.error.URLError as erreur:
        raise ErreurTransport("transport : %s" % (erreur.reason,)) from erreur
    except ValueError as erreur:
        raise ErreurTransport("réponse non JSON") from erreur


NOM_VARIABLE_URL_SOLDE = "MONRECOURS_LLM_URL_SOLDE"


def url_solde_autorisee():
    """Adresse de l'API de solde DeepSeek.

    Par défaut l'adresse officielle. `MONRECOURS_LLM_URL_SOLDE` ne sert qu'aux
    tests (faux fournisseur local) : elle n'est acceptée que vers l'hôte
    officiel en HTTPS ou vers la boucle locale. Toute autre valeur est refusée,
    pour qu'une variable mal renseignée ne puisse pas envoyer la clé ailleurs.
    """
    valeur = os.environ.get(NOM_VARIABLE_URL_SOLDE)
    if not valeur:
        return FournisseurDeepSeek.URL_SOLDE
    try:
        morceaux = urllib.parse.urlsplit(valeur)
    except ValueError:
        return None
    if morceaux.scheme == "https" and morceaux.hostname == "api.deepseek.com":
        return valeur
    if morceaux.scheme == "http" and morceaux.hostname in ("127.0.0.1", "localhost", "::1"):
        return valeur
    return None


class FournisseurDeepSeek(object):
    """API DeepSeek (compatible OpenAI) — modèle par défaut : deepseek-flash.

    Trois différences avec le générique `compatible_openai`, et trois seulement :
      * URL et modèle par défaut, pour que la configuration tienne en une ligne ;
      * `response_format: json_object` : la sortie est un OBJET, pas du texte à
        découper — le service refuse déjà tout ce qui n'est pas un JSON strict ;
      * `usage` capturé : les jetons consommés alimentent le plafond journalier.

    Ce fournisseur ne décide de rien : il propose des identifiants de fiches et
    des reformulations, que `core.llm.valider_comprehension` puis
    `core.catalogue.valider_fiches_proposees` rejettent s'ils ne tiennent pas.
    Il ne cite jamais d'article et n'écrit jamais de démarche.
    """

    nom = "deepseek"
    URL_DEFAUT = "https://api.deepseek.com/chat/completions"
    MODELE_DEFAUT = "deepseek-flash"
    URL_SOLDE = "https://api.deepseek.com/user/balance"

    LIBELLES_ERREUR = {
        400: "requête refusée",
        401: "clé refusée",
        402: "solde du compte épuisé",
        422: "requête invalide",
        429: "débit dépassé chez le fournisseur",
        500: "erreur interne du fournisseur",
        502: "passerelle du fournisseur en erreur",
        503: "fournisseur indisponible",
    }

    def __init__(self, url=None, cle=None, modele=None, delai=DELAI_PAR_DEFAUT):
        self.url = url or os.environ.get(NOM_VARIABLE_URL) or self.URL_DEFAUT
        self._cle = cle if cle is not None else os.environ.get(NOM_VARIABLE_CLE, "")
        self.modele = modele or os.environ.get(NOM_VARIABLE_MODELE) or self.MODELE_DEFAUT
        self.delai = delai
        self.derniere_consommation = None

    def disponible(self):
        return bool(self.url and self._cle and self.modele)

    def completer(self, systeme, message, delai=None, max_tokens=800):
        if not self.disponible():
            raise ErreurTransport("clé, URL ou modèle absent de l'environnement")
        donnees = _poster_api(
            self.url,
            {"Authorization": "Bearer %s" % self._cle},
            {"model": self.modele,
             "max_tokens": max_tokens,
             "temperature": 0,
             "stream": False,
             # MESURÉ le 22/10/2026 sur l'API réelle : le mode réflexion est
             # ACTIF PAR DÉFAUT sur deepseek-flash. Avec 300 jetons de plafond,
             # il consommait tout le budget en raisonnement et la réponse
             # arrivait tronquée : 2 appels sur 7 rendaient un JSON invalide.
             # On le désactive — cette tâche est de l'extraction, pas du
             # raisonnement — et on laisse 800 jetons à la sortie.
             "thinking": {"type": "disabled"},
             "response_format": {"type": "json_object"},
             "messages": [{"role": "system", "content": systeme},
                          {"role": "user", "content": message}]},
            delai or self.delai,
            self.LIBELLES_ERREUR)
        usage = donnees.get("usage") if isinstance(donnees, dict) else None
        usage = usage if isinstance(usage, dict) else {}
        try:
            self.derniere_consommation = {
                "entree": int(usage.get("prompt_tokens") or 0),
                "sortie": int(usage.get("completion_tokens") or 0),
            }
        except (TypeError, ValueError):
            self.derniere_consommation = None
        try:
            contenu = donnees["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as erreur:
            raise ErreurTransport("réponse du fournisseur au format inattendu") from erreur
        if not isinstance(contenu, str) or not contenu.strip():
            raise ErreurTransport("réponse vide du fournisseur")
        return contenu

    def verifier_solde(self, delai=10.0):
        """Interroge GET /user/balance (documentation officielle DeepSeek).

        Lecture seule : aucun jeton consommé, aucune donnée de citoyen envoyée.
        Renvoie un état qualifié — jamais une interprétation optimiste :
          POSITIF  : is_available vrai ET solde total > 0
          EPUISE   : is_available faux, ou solde total <= 0
          AMBIGU   : réponse 200 mais illisible (ni solde ni indicateur)
          ERREUR   : statut non 200, réseau, délai
        """
        cle = os.environ.get("MONRECOURS_LLM_API_KEY")
        if not cle:
            return {"etat": "ERREUR", "detail": "clé absente"}
        url_solde = url_solde_autorisee()
        if url_solde is None:
            return {"etat": "ERREUR", "detail": "adresse de solde refusée"}
        requete = urllib.request.Request(url_solde, method="GET", headers={
            "Authorization": "Bearer %s" % cle,
            "Accept": "application/json",
        })
        try:
            with urllib.request.urlopen(requete, timeout=delai) as reponse:
                if reponse.status != 200:
                    return {"etat": "ERREUR", "detail": "HTTP %s" % reponse.status}
                corps = reponse.read(20000).decode("utf-8", "replace")
        except urllib.error.HTTPError as erreur:
            return {"etat": "ERREUR", "detail": "HTTP %s" % erreur.code,
                    "statut_http": erreur.code}
        except Exception as erreur:  # noqa: BLE001 — réseau, délai, DNS
            return {"etat": "ERREUR", "detail": type(erreur).__name__}
        try:
            donnees = json.loads(corps)
        except ValueError:
            return {"etat": "AMBIGU", "detail": "réponse non JSON"}
        if not isinstance(donnees, dict):
            return {"etat": "AMBIGU", "detail": "réponse inattendue"}
        disponible = donnees.get("is_available")
        infos = donnees.get("balance_infos")
        if not isinstance(infos, list) or not infos:
            return {"etat": "AMBIGU", "detail": "aucun solde dans la réponse"}
        devise = None
        total = None
        for info in infos:
            if not isinstance(info, dict):
                continue
            try:
                montant = decimal.Decimal(str(info.get("total_balance")))
            except (decimal.InvalidOperation, TypeError, ValueError):
                continue
            if total is None or montant > total:
                total = montant
                devise = info.get("currency")
        if total is None:
            return {"etat": "AMBIGU", "detail": "solde non numérique"}
        if disponible is False or total <= 0:
            return {"etat": "EPUISE", "devise": devise, "total": str(total)}
        if disponible is not True:
            # Contrat documenté : POSITIF exige is_available VRAI. Un indicateur
            # absent ou d'un autre type n'est pas une preuve : réponse ambiguë.
            return {"etat": "AMBIGU", "detail": "indicateur de disponibilité absent"}
        return {"etat": "POSITIF", "devise": devise, "total": str(total)}

