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
import sys
import tempfile
import threading

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


# Repli mémoire, comme pour l'incident : si RUNTIME n'est pas inscriptible
# (systemd `ProtectSystem=strict` sans `ReadWritePaths`), le plafond journalier
# et le disjoncteur restent appliqués dans le processus du moteur au lieu de
# disparaître en silence — un plafond qui ne compte rien n'est pas un plafond.
_MEMOIRE = {}
_NON_PERSISTANT = set()
_VERROU = threading.RLock()


def persistant():
    return _chemin() not in _NON_PERSISTANT


def _lire():
    chemin = _chemin()
    if chemin in _NON_PERSISTANT and chemin in _MEMOIRE:
        return dict(_MEMOIRE[chemin])
    try:
        with open(chemin, encoding="utf-8") as flux:
            donnees = json.load(flux)
        return donnees if isinstance(donnees, dict) else {}
    except (OSError, ValueError):
        return {}


def _ecrire(donnees):
    chemin = _chemin()
    dossier = os.path.dirname(chemin)
    _MEMOIRE[chemin] = dict(donnees)
    try:
        os.makedirs(dossier, mode=0o700, exist_ok=True)
        descripteur, temporaire = tempfile.mkstemp(dir=dossier, prefix=".llm-", suffix=".tmp")
        with os.fdopen(descripteur, "w", encoding="utf-8") as flux:
            json.dump(donnees, flux, ensure_ascii=False)
        os.chmod(temporaire, 0o600)
        os.replace(temporaire, chemin)
    except OSError:
        # Un registre non inscriptible ne bloque pas le service, mais le
        # comptage continue en mémoire et l'anomalie est signalée.
        if chemin not in _NON_PERSISTANT:
            sys.stderr.write("llm_budget : registre NON enregistre sur disque (dossier %s "
                             "non inscriptible) ; comptage en memoire\n" % dossier)
        _NON_PERSISTANT.add(chemin)
        return False
    _NON_PERSISTANT.discard(chemin)
    return True


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
        return {"jour": jour, "jetons": 0, "plafond": plafond(), "echecs": 0, "en_panne": False,
                "persistant": persistant()}
    return {
        "jour": jour,
        "jetons": int(donnees.get("jetons") or 0),
        "plafond": plafond(),
        "echecs": int(donnees.get("echecs") or 0),
        "en_panne": _panne_active(donnees),
        "persistant": persistant(),
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
    with _VERROU:
        donnees = _lire()
        jour = _jour()
        if donnees.get("jour") != jour:
            donnees = {"jour": jour, "jetons": 0, "echecs": 0}
        donnees["jetons"] = int(donnees.get("jetons") or 0) + max(0, int(entree)) + max(0, int(sortie))
        _ecrire(donnees)


def signaler_succes():
    with _VERROU:
        donnees = _lire()
        jour = _jour()
        if donnees.get("jour") != jour:
            donnees = {"jour": jour, "jetons": 0}
        donnees["echecs"] = 0
        donnees.pop("dernier_echec", None)
        _ecrire(donnees)


def signaler_echec():
    with _VERROU:
        donnees = _lire()
        jour = _jour()
        if donnees.get("jour") != jour:
            donnees = {"jour": jour, "jetons": 0, "echecs": 0}
        donnees["echecs"] = int(donnees.get("echecs") or 0) + 1
        donnees["dernier_echec"] = datetime.datetime.now().isoformat()
        _ecrire(donnees)
