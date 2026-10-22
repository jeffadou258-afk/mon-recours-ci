# -*- coding: utf-8 -*-
"""Garde-fou de consommation du fournisseur de langage.

Rôle : empêcher un modèle de coûter plus que prévu et de bloquer le service
quand il tombe. Deux mécanismes, tous deux DÉTERMINISTES :

  * un plafond journalier de jetons (`MONRECOURS_LLM_BUDGET_JETONS`) ;
  * un disjoncteur : au-delà de cinq échecs consécutifs, le service repasse en
    déterministe pendant dix minutes, sans rappeler le fournisseur.

Le registre ne contient QUE des compteurs : date, jetons, nombre d'échecs.
Jamais un récit, jamais une réponse, jamais une clé.

Aucune de ces fonctions ne lève : un garde-fou qui casse le service serait pire
que le risque qu'il couvre.
"""
import datetime
import json
import os
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "RUNTIME")

NOM_VARIABLE_PLAFOND = "MONRECOURS_LLM_BUDGET_JETONS"
NOM_VARIABLE_REGISTRE = "MONRECOURS_LLM_REGISTRE"

PLAFOND_DEFAUT = 2000000      # 2 M de jetons/jour : large, borné, explicite
ECHECS_AVANT_PANNE = 5
DUREE_PANNE = 600             # secondes


def _chemin():
    """Registre surchargeable (les tests écrivent dans un fichier jetable)."""
    return os.environ.get(NOM_VARIABLE_REGISTRE) or os.path.join(DOSSIER, "llm_consommation.json")


def _jour():
    return datetime.date.today().isoformat()


def _lire():
    try:
        with open(_chemin(), encoding="utf-8") as flux:
            donnees = json.load(flux)
        return donnees if isinstance(donnees, dict) else {}
    except (OSError, ValueError):
        return {}


def _ecrire(donnees):
    chemin = _chemin()
    dossier = os.path.dirname(chemin)
    try:
        os.makedirs(dossier, mode=0o700, exist_ok=True)
        descripteur, temporaire = tempfile.mkstemp(dir=dossier, prefix=".llm-", suffix=".tmp")
        with os.fdopen(descripteur, "w", encoding="utf-8") as flux:
            json.dump(donnees, flux, ensure_ascii=False)
        os.chmod(temporaire, 0o600)
        os.replace(temporaire, chemin)
    except OSError:
        # Un registre illisible ne doit pas bloquer le service : on préfère
        # perdre le comptage que refuser une réponse.
        pass


def plafond():
    try:
        valeur = int(os.environ.get(NOM_VARIABLE_PLAFOND) or PLAFOND_DEFAUT)
    except (TypeError, ValueError):
        return PLAFOND_DEFAUT
    return valeur if valeur > 0 else PLAFOND_DEFAUT


def etat():
    donnees = _lire()
    jour = _jour()
    if donnees.get("jour") != jour:
        return {"jour": jour, "jetons": 0, "plafond": plafond(), "echecs": 0, "en_panne": False}
    return {
        "jour": jour,
        "jetons": int(donnees.get("jetons") or 0),
        "plafond": plafond(),
        "echecs": int(donnees.get("echecs") or 0),
        "en_panne": _panne_active(donnees),
    }


def _panne_active(donnees):
    if int(donnees.get("echecs") or 0) < ECHECS_AVANT_PANNE:
        return False
    dernier = donnees.get("dernier_echec") or ""
    try:
        quand = datetime.datetime.fromisoformat(dernier)
    except (TypeError, ValueError):
        return False
    ecoule = (datetime.datetime.now(quand.tzinfo) - quand).total_seconds()
    return ecoule < DUREE_PANNE


def peut_appeler(jetons_estimes=2000):
    """Le service a-t-il le droit d'appeler le fournisseur maintenant ?"""
    courant = etat()
    if courant["en_panne"]:
        return False
    return courant["jetons"] + max(0, int(jetons_estimes)) <= courant["plafond"]


def enregistrer(entree=0, sortie=0):
    """Ajoute la consommation réelle. Ne lève jamais."""
    donnees = _lire()
    jour = _jour()
    if donnees.get("jour") != jour:
        donnees = {"jour": jour, "jetons": 0, "echecs": 0}
    donnees["jetons"] = int(donnees.get("jetons") or 0) + max(0, int(entree)) + max(0, int(sortie))
    _ecrire(donnees)


def signaler_succes():
    donnees = _lire()
    jour = _jour()
    if donnees.get("jour") != jour:
        donnees = {"jour": jour, "jetons": 0}
    donnees["echecs"] = 0
    donnees.pop("dernier_echec", None)
    _ecrire(donnees)


def signaler_echec():
    donnees = _lire()
    jour = _jour()
    if donnees.get("jour") != jour:
        donnees = {"jour": jour, "jetons": 0, "echecs": 0}
    donnees["echecs"] = int(donnees.get("echecs") or 0) + 1
    donnees["dernier_echec"] = datetime.datetime.now().isoformat()
    _ecrire(donnees)
