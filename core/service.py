# -*- coding: utf-8 -*-
"""API de service de Mon Recours CI — façade stable pour une application.

Cette couche N'AJOUTE AUCUNE LOGIQUE JURIDIQUE : elle valide les entrées, appelle
`core.conversation` et renvoie un résultat typé. C'est le point d'entrée à
brancher sur une application web, un bot ou un CLI.

    from core import service
    service.ouvrir("DOSSIER_1", "Mon bailleur garde ma caution.")
    service.repondre("DOSSIER_1", {"logement": "oui"})

Forme de retour, TOUJOURS la même :

    {"ok": True,  "data": {...}}
    {"ok": False, "erreur": {"code": "ENTREE_INVALIDE", "message": "...", "detail": ...}}

Aucune exception ne sort de ce module : une application hôte ne doit pas planter
parce qu'un dossier est inconnu.

CONFIDENTIALITÉ
---------------
* `dossier_id` est validé par `config.dossier_utilisateur` : toute traversée
  (`../`, `/`, octet nul) est refusée avant toute lecture ;
* aucun identifiant d'un dossier n'est renvoyé avec les données d'un autre ;
* les réponses ne contiennent pas de données personnelles ajoutées par le
  service : uniquement ce que l'utilisateur a écrit et ce que le corpus contient.

CE QUI N'EST PAS FAIT ICI
-------------------------
Aucun serveur HTTP. Le contrat est défini et testé ; l'exposition réseau reste à
faire, et doit alors ajouter authentification, limitation de débit et journalisation.
"""

import os
import shutil
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import config  # noqa: E402
from core import catalogue, corpus, couverture, llm  # noqa: E402
from core.conversation import Conversation  # noqa: E402

LONGUEUR_MAX_DEMANDE = 4000
LONGUEUR_MAX_REPONSE = 1000

CODES_ERREUR = {
    "ENTREE_INVALIDE": "La demande ou les réponses ne respectent pas le contrat.",
    "DOSSIER_INVALIDE": "L'identifiant de dossier est refusé (traversée de chemin).",
    "DOSSIER_INCONNU": "Aucune conversation n'est ouverte pour ce dossier.",
    "CATALOGUE_INVALIDE": "Le catalogue de fiches ne correspond plus au corpus.",
    "INTERNE": "Erreur interne : l'incident est déclaré, pas masqué.",
}

# Contrat d'entrée/sortie, publié tel quel pour l'intégration.
SCHEMAS = {
    "ouvrir": {
        "entree": {"dossier_id": "str (identifiant simple, sans séparateur de chemin)",
                   "demande": "str, 1..%d caractères" % LONGUEUR_MAX_DEMANDE},
        "sortie": {"etape": "refus | clarification | hors_catalogue",
                   "dossier_id": "str",
                   "fiches_identifiees": "[{titre, article, numero_texte, etat_verification}]",
                   "questions": "[{cle, question}]",
                   "urgence": "{niveau, declencheurs}",
                   "verrous_humains": "[str]"},
    },
    "repondre": {
        "entree": {"dossier_id": "str", "reponses": "dict[cle] -> str (1..%d car.)"
                   % LONGUEUR_MAX_REPONSE},
        "sortie": {"statut_reponse": "ANALYSE_CONFORME | CONCLUSION_IMPOSSIBLE | "
                                     "ANALYSE_REFUSEE | REFUS",
                   "sections": {"1_faits": "object", "2_droit": "list",
                                "3_application": "str", "4_demarches": "list",
                                "5_a_verifier": "list", "6_sources": "list"},
                   "verrous_humains": "list", "traceabilite": "chemin du dossier JSON",
                   "brouillon": "{disponible, note, genere | raison}"},
    },
    "supprimer": {
        "entree": {"dossier_id": "str"},
        "sortie": {"supprime": "bool", "deja_absent": "bool"},
    },
    "sante": {
        "sortie": {"catalogue": "fiches par domaine", "corpus": "documents, articles, "
                   "provenance", "domaines": "statut par domaine"},
    },
}


class _ErreurService(Exception):
    def __init__(self, code, message, detail=None):
        super(_ErreurService, self).__init__(message)
        self.code = code
        self.message = message
        self.detail = detail


def _valider_dossier(dossier_id):
    if not isinstance(dossier_id, str) or not dossier_id.strip():
        raise _ErreurService("ENTREE_INVALIDE", "dossier_id doit être une chaîne non vide")
    try:
        config.dossier_utilisateur(dossier_id)
    except ValueError as erreur:
        raise _ErreurService("DOSSIER_INVALIDE", str(erreur), detail=dossier_id)
    return dossier_id


def _valider_texte(valeur, nom, maximum):
    if not isinstance(valeur, str) or not valeur.strip():
        raise _ErreurService("ENTREE_INVALIDE", "%s doit être une chaîne non vide" % nom)
    if len(valeur) > maximum:
        raise _ErreurService("ENTREE_INVALIDE",
                             "%s dépasse %d caractères" % (nom, maximum),
                             detail=len(valeur))
    return valeur


def _executer(fonction):
    try:
        return {"ok": True, "data": fonction()}
    except _ErreurService as erreur:
        return {"ok": False, "erreur": {"code": erreur.code, "message": erreur.message,
                                        "libelle": CODES_ERREUR.get(erreur.code),
                                        "detail": erreur.detail}}
    except catalogue.CatalogueInvalide as erreur:
        return {"ok": False, "erreur": {"code": "CATALOGUE_INVALIDE",
                                        "message": str(erreur),
                                        "libelle": CODES_ERREUR["CATALOGUE_INVALIDE"]}}
    except Exception as erreur:  # noqa: BLE001 — aucune exception ne sort du service
        return {"ok": False, "erreur": {"code": "INTERNE", "message": str(erreur),
                                        "libelle": CODES_ERREUR["INTERNE"]}}


def _conversation():
    return Conversation()


def ouvrir(dossier_id, demande):
    def corps():
        _valider_dossier(dossier_id)
        _valider_texte(demande, "demande", LONGUEUR_MAX_DEMANDE)
        if os.path.exists(str(config.dossier_utilisateur(dossier_id) / "CONVERSATION.json")):
            raise _ErreurService(
                "ENTREE_INVALIDE",
                "une conversation est déjà ouverte pour ce dossier ; utilisez `repondre` "
                "ou un nouvel identifiant")
        return _conversation().demarrer(dossier_id, demande)
    return _executer(corps)


def repondre(dossier_id, reponses):
    def corps():
        _valider_dossier(dossier_id)
        if not isinstance(reponses, dict):
            raise _ErreurService("ENTREE_INVALIDE", "reponses doit être un dictionnaire")
        propre = {}
        for cle, valeur in reponses.items():
            if not isinstance(cle, str):
                raise _ErreurService("ENTREE_INVALIDE", "les clés de réponses doivent être "
                                                       "des chaînes")
            if valeur is None:
                continue
            if not isinstance(valeur, str):
                raise _ErreurService("ENTREE_INVALIDE",
                                     "la réponse %r doit être une chaîne" % cle)
            propre[cle] = _valider_texte(valeur, "réponse %r" % cle, LONGUEUR_MAX_REPONSE)
        resultat = _conversation().repondre(dossier_id, propre)
        if resultat.get("etape") == "erreur":
            raise _ErreurService(resultat.get("erreur") or "INTERNE",
                                 resultat.get("message") or "erreur inconnue")
        return resultat
    return _executer(corps)


def supprimer(dossier_id):
    """Supprime le dossier d'une consultation, à la demande de la personne.

    Ne touche QUE le dossier désigné, après la même validation que les autres
    opérations (aucune traversée de chemin possible). Idempotent : un dossier
    déjà absent est signalé comme tel, sans erreur.
    """
    def corps():
        _valider_dossier(dossier_id)
        chemin = config.dossier_utilisateur(dossier_id)
        if not chemin.exists():
            return {"supprime": False, "deja_absent": True}
        racine = os.path.realpath(str(config.DOSSIERS_DIR))
        cible = os.path.realpath(str(chemin))
        if os.path.dirname(cible) != racine:
            raise _ErreurService("DOSSIER_INVALIDE", "dossier hors de la racine des dossiers")
        shutil.rmtree(cible)
        return {"supprime": True, "deja_absent": False}
    return _executer(corps)


def sante(chemin_db=None):
    """État exploitable par une supervision : catalogue, corpus, domaines."""
    def corps():
        fiches = catalogue.charger(chemin_db=chemin_db)
        integrite = corpus.verifier_integrite(chemin=chemin_db)
        origine = corpus.articles_par_origine(chemin=chemin_db)
        inventaire = couverture.inventaire(chemin=chemin_db)
        return {
            "catalogue": {"fiches": len(fiches),
                          "domaines": sorted({f["domaine"] for f in fiches}),
                          "par_domaine": catalogue.couverture(fiches=fiches)},
            "corpus": {"verdict_integrite": integrite["verdict"],
                       "documents": integrite["nb_documents"],
                       "articles": sum(v["articles"] for v in origine.values()),
                       "articles_par_origine": {k: v["articles"] for k, v in origine.items()}},
            "domaines": [{"domaine": l["domaine"], "statut": l["statut"],
                          "completude": l["completude_juridique"]}
                         for l in inventaire["domaines"]],
            "langage": {"actif": llm.comprehension_active(),
                        "fournisseur": (os.environ.get(llm.NOM_VARIABLE_FOURNISSEUR) or None)
                        if llm.comprehension_active() else None},
            "avertissement": ("Aucune validation juridique humaine n'a été effectuée. "
                              "Un statut technique n'est pas une garantie de justesse."),
        }
    return _executer(corps)
