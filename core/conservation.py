# -*- coding: utf-8 -*-
"""Conservation temporaire des consultations : expiration = création + N heures.

Décision produit du 22/10/2026 : une consultation est conservée **24 heures au
plus** après sa création, puis supprimée par une purge côté serveur.

Ce module ne supprime RIEN. Il fournit :

* `marquer(chemin)` — écrit, à la création du dossier et une seule fois,
  `CONSERVATION.json` : `{version, cree_le, expire_le, duree_heures}`. Ce fichier
  ne contient aucune donnée personnelle ; la purge et les contrôles de lecture
  s'y fient sans ouvrir le récit.
* `expiration(chemin)` — l'instant d'expiration et la façon dont il a été établi :
  `conservation` (le fichier ci-dessus), `ouvert_le` (dossiers créés avant ce
  module : date d'ouverture inscrite par le moteur dans `DOSSIER_EN_COURS.json`),
  `mtime` (dernier recours : date de modification du répertoire). Chaque repli
  ne peut que retarder l'échéance, jamais l'avancer.
* `est_expire(chemin)` — vrai si l'échéance est passée. Le moteur et l'interface
  refusent de servir un dossier expiré, même si la purge n'est pas encore passée.

La durée vient de `MONRECOURS_CONSERVATION_HEURES` (entier >= 1), 24 par défaut.
Une valeur invalide est refusée : la durée ne se devine pas.
"""

import datetime
import json
import os

import config

FICHIER = "CONSERVATION.json"
VERSION = 1
DUREE_HEURES_DEFAUT = 24
VARIABLE_DUREE = "MONRECOURS_CONSERVATION_HEURES"


class DureeInvalide(ValueError):
    pass


def duree_heures(env=None):
    brut = (env if env is not None else os.environ).get(VARIABLE_DUREE, "")
    if brut == "":
        return DUREE_HEURES_DEFAUT
    try:
        valeur = int(brut)
    except ValueError:
        raise DureeInvalide("%s doit être un entier (heures) : %r" % (VARIABLE_DUREE, brut))
    if valeur < 1:
        raise DureeInvalide("%s doit valoir au moins 1 : %r" % (VARIABLE_DUREE, brut))
    return valeur


def maintenant():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0)


def _iso(instant):
    return instant.astimezone(datetime.timezone.utc).replace(microsecond=0).isoformat()


def _lire_instant(texte):
    instant = datetime.datetime.fromisoformat(str(texte))
    if instant.tzinfo is None:  # les horodatages du moteur sont en UTC
        instant = instant.replace(tzinfo=datetime.timezone.utc)
    return instant


def marquer(chemin_dossier, instant=None, heures=None):
    """Écrit CONSERVATION.json s'il n'existe pas ; ne le réécrit jamais.

    Création exclusive (`O_EXCL`) : deux ouvertures concurrentes ne peuvent pas
    repousser l'échéance. Retourne le contenu en vigueur.
    """
    chemin = os.path.join(str(chemin_dossier), FICHIER)
    if os.path.exists(chemin):
        return lire(chemin_dossier)
    instant = instant or maintenant()
    heures = heures if heures is not None else duree_heures()
    contenu = {
        "version": VERSION,
        "cree_le": _iso(instant),
        "expire_le": _iso(instant + datetime.timedelta(hours=heures)),
        "duree_heures": heures,
    }
    config.creer_dossier_prive(str(chemin_dossier))
    try:
        descripteur = os.open(chemin, os.O_WRONLY | os.O_CREAT | os.O_EXCL, config.PERMISSIONS_FICHIER)
    except FileExistsError:
        return lire(chemin_dossier)
    with os.fdopen(descripteur, "w", encoding="utf-8") as flux:
        json.dump(contenu, flux, ensure_ascii=False)
    return contenu


def lire(chemin_dossier):
    chemin = os.path.join(str(chemin_dossier), FICHIER)
    with open(chemin, encoding="utf-8") as flux:
        return json.load(flux)


def expiration(chemin_dossier, heures=None):
    """(instant d'expiration, source) — ou (None, None) si le répertoire n'existe pas."""
    chemin_dossier = str(chemin_dossier)
    if not os.path.isdir(chemin_dossier):
        return None, None
    try:
        return _lire_instant(lire(chemin_dossier)["expire_le"]), "conservation"
    except (OSError, ValueError, KeyError, TypeError):
        pass
    heures = heures if heures is not None else duree_heures()
    try:
        with open(os.path.join(chemin_dossier, "DOSSIER_EN_COURS.json"), encoding="utf-8") as flux:
            ouvert = _lire_instant(json.load(flux)["ouvert_le"])
        return ouvert + datetime.timedelta(hours=heures), "ouvert_le"
    except (OSError, ValueError, KeyError, TypeError):
        pass
    mtime = datetime.datetime.fromtimestamp(os.stat(chemin_dossier).st_mtime, datetime.timezone.utc)
    return mtime + datetime.timedelta(hours=heures), "mtime"


def est_expire(chemin_dossier, instant=None, heures=None):
    """Vrai si l'échéance est passée (à la seconde près, échéance comprise)."""
    echeance, _ = expiration(chemin_dossier, heures=heures)
    if echeance is None:
        return False
    return (instant or maintenant()) >= echeance
