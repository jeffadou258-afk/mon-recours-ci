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
import tempfile

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
        descripteur, temporaire = tempfile.mkstemp(dir=dossier, prefix=".incident-", suffix=".tmp")
        with os.fdopen(descripteur, "w", encoding="utf-8") as flux:
            json.dump(donnees, flux, ensure_ascii=False)
        os.chmod(temporaire, 0o600)
        os.replace(temporaire, chemin)
    except OSError:
        pass


def etat():
    """État courant de l'incident (vide si aucun)."""
    donnees = _lire()
    if not donnees.get("statut"):
        return {"statut": None, "ouvert": False}
    donnees["ouvert"] = donnees.get("statut") == OUVERT
    return donnees


def ouvert():
    return etat().get("ouvert", False)


def declarer(fournisseur, message="", statut_http=None):
    """Ouvre l'incident s'il ne l'est pas déjà. Renvoie True si c'est NOUVEAU.

    L'appelant s'en sert pour n'alerter qu'une fois : plusieurs consultations
    pendant la panne ne produisent aucune nouvelle alerte.
    """
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
        "action_attendue": ("Vérifier le solde du fournisseur et rétablir le service. "
                            "La réactivation se fait par la vérification du solde, pas par un bouton."),
    })
    return True


def resoudre(motif=""):
    """Clôt l'incident. Renvoie True si un incident était ouvert."""
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
