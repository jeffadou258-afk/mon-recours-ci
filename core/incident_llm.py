# -*- coding: utf-8 -*-
"""Incident « crédits du fournisseur épuisés » — état persistant et alerte unique.

Principe : un incident n'est pas une erreur. Une erreur se produit à chaque
appel ; un incident a une date de début, une date de fin, et ne s'annonce
qu'UNE fois. Sans cela, un solde vide produirait une alerte par consultation et
l'alerte deviendrait du bruit qu'on apprend à ignorer.

Le fichier ne contient que des métadonnées d'incident : statut, dates,
fournisseur, message public du fournisseur (tronqué). Jamais de clé, jamais de
récit, jamais de donnée personnelle.
"""
import datetime
import json
import os
import sys
import tempfile
import threading

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "RUNTIME")

NOM_VARIABLE_FICHIER = "MONRECOURS_INCIDENT_FICHIER"

OUVERT = "CREDITS_EPUISES"
RESOLU = "RESOLU"

# Marqueurs d'un épuisement de crédits dans la réponse du fournisseur. Volontairement
# stricts : un 402 ou un 429 SANS ces mots n'est PAS un épuisement de crédits.
MARQUEURS_CREDITS = (
    "insufficient balance",
    "insufficient_quota",
    "insufficient_quota_exceeded",
    "exceeded your current quota",
    "credit balance is too low",
    "no credit",
    "solde insuffisant",
    "crédits épuisés",
    "credits exhausted",
)


def _chemin():
    return os.environ.get(NOM_VARIABLE_FICHIER) or os.path.join(DOSSIER, "incident_llm.json")


def _maintenant():
    return datetime.datetime.now().isoformat(timespec="seconds")


# Copie en mémoire du dernier état connu. Elle ne sert QUE si le fichier ne
# peut pas être écrit (dossier RUNTIME absent ou en lecture seule, par exemple
# sous systemd `ProtectSystem=strict`) : sans elle, chaque consultation
# re-déclarerait l'incident (une alerte par consultation) et rappellerait le
# fournisseur malgré un solde épuisé. Le moteur tourne dans UN processus : cette
# copie est donc bien l'état qu'il utilise. Elle ne survit pas à un redémarrage,
# et `etat()["persistant"]` le dit.
_MEMOIRE = {}            # chemin -> dernier état écrit (ou tenté)
_NON_PERSISTANT = set()  # chemins dont la dernière écriture a échoué
# Le serveur du moteur est multi-fil : sans verrou, deux consultations
# simultanées pourraient toutes deux « ouvrir » l'incident (deux alertes).
_VERROU = threading.Lock()


def _persistant():
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
    """Écrit l'état ; renvoie True seulement s'il est réellement sur disque."""
    chemin = _chemin()
    dossier = os.path.dirname(chemin)
    _MEMOIRE[chemin] = dict(donnees)
    try:
        os.makedirs(dossier, mode=0o700, exist_ok=True)
        descripteur, temporaire = tempfile.mkstemp(dir=dossier, prefix=".incident-", suffix=".tmp")
        with os.fdopen(descripteur, "w", encoding="utf-8") as flux:
            json.dump(donnees, flux, ensure_ascii=False)
        os.chmod(temporaire, 0o600)
        os.replace(temporaire, chemin)
    except OSError:
        _NON_PERSISTANT.add(chemin)
        sys.stderr.write("incident_llm : etat NON enregistre sur disque (dossier %s "
                         "non inscriptible) ; conserve en memoire jusqu'au redemarrage\n"
                         % dossier)
        return False
    _NON_PERSISTANT.discard(chemin)
    return True


def etat():
    """État courant de l'incident (vide si aucun)."""
    donnees = _lire()
    if not donnees.get("statut"):
        return {"statut": None, "ouvert": False, "persistant": _persistant()}
    donnees["ouvert"] = donnees.get("statut") == OUVERT
    donnees["persistant"] = _persistant()
    return donnees


def ouvert():
    return etat().get("ouvert", False)


def declarer(fournisseur, message="", statut_http=None):
    """Ouvre l'incident s'il ne l'est pas déjà. Renvoie True si c'est NOUVEAU.

    L'appelant s'en sert pour n'alerter qu'une fois : plusieurs consultations
    pendant la panne ne produisent aucune nouvelle alerte.
    """
    with _VERROU:
        return _declarer(fournisseur, statut_http)


def _declarer(fournisseur, statut_http):
    courant = _lire()
    if courant.get("statut") == OUVERT:
        return False
    _ecrire({
        "statut": OUVERT,
        "fournisseur": fournisseur or "inconnu",
        "detecte_le": _maintenant(),
        "resolu_le": None,
        "statut_http": statut_http,
        # Le message du fournisseur n'est PAS conservé : il peut contenir un
        # extrait de requête, une adresse ou un identifiant. On garde le fait.
        "message": "Le fournisseur a signalé un solde insuffisant.",
        "objet": "Crédits %s épuisés — Mon Recours CI" % (fournisseur or "du fournisseur"),
        "consequence": ("Le moteur déterministe fonctionne en secours : les consultations "
                        "restent traitées, sans compréhension assistée."),
        "action_attendue": ("Vérifier le solde du fournisseur et rétablir le service : après "
                            "rechargement du compte, utiliser « Vérifier le solde et réactiver "
                            "DeepSeek ». Le service ne se rétablit que sur preuve d'un solde positif."),
    })
    return True


def resoudre(motif=""):
    """Clôt l'incident. Renvoie True si un incident était ouvert.

    La clôture vaut pour le processus du moteur même si le disque refuse
    l'écriture ; `etat()["persistant"]` indique alors qu'elle ne survivra pas à
    un redémarrage.
    """
    with _VERROU:
        courant = _lire()
        if courant.get("statut") != OUVERT:
            return False
        courant["statut"] = RESOLU
        courant["resolu_le"] = _maintenant()
        courant["resolution"] = (motif or "")[:200]
        _ecrire(courant)
        return True


def message_credits(texte):
    """Le message du fournisseur dit-il explicitement un épuisement de crédits ?

    Un 402 sans ces mots (paiement requis pour une autre raison) et un 429
    (débit dépassé) ne sont PAS des épuisements de crédits. On ne déclenche donc
    jamais l'alerte sur un code seul.
    """
    if not texte:
        return False
    bas = str(texte).lower()
    return any(marqueur in bas for marqueur in MARQUEURS_CREDITS)
