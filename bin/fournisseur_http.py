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
