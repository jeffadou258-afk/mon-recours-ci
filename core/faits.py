# -*- coding: utf-8 -*-
"""Faits d'un dossier — statuts, pièces, informations manquantes.

Invariant central (spec §6, §10.7, §16) : un fait DÉCLARÉ par l'utilisateur
n'est JAMAIS promu en fait DOCUMENTÉ. Seule une pièce réellement fournie
(nom de fichier + empreinte SHA-256 calculée sur le fichier) le permet.

Les informations absentes sont NOMMÉES (`MANQUANT`) et listées ; elles ne sont
jamais complétées par une supposition.

Un fait porte aussi `ecarte` : une déclaration peut être retirée sans être
effacée, pour que le dossier reste fidèle à ce qui a été dit.
"""

import datetime
import hashlib
import os

from config import ETATS_FAIT


def horodatage():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def empreinte_fichier(chemin):
    """SHA-256 d'un fichier réel. Lève si le fichier n'existe pas."""
    if not os.path.isfile(chemin):
        raise FileNotFoundError("pièce introuvable : %s" % chemin)
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(65536), b""):
            h.update(bloc)
    return "sha256:" + h.hexdigest()


class Faits(object):
    """Collecte des faits d'un dossier, avec statuts préservés."""

    def __init__(self, dossier_id):
        self.dossier_id = dossier_id
        self._faits = []

    # -- écriture ---------------------------------------------------------
    def declarer(self, libelle, date_fait=None, precision=None):
        """Enregistre une déclaration de l'utilisateur (statut DECLARE)."""
        if not libelle or not str(libelle).strip():
            raise ValueError("un fait déclaré ne peut pas être vide")
        fait = {
            "fait_id": "F%02d" % (len(self._faits) + 1),
            "libelle": str(libelle).strip(),
            "date_fait": date_fait,
            "precision": precision,
            "etat": "DECLARE_PAR_L_UTILISATEUR",
            "piece": None,
            "empreinte_piece": None,
            "date_ajout": horodatage(),
            "ecarte": False,
        }
        self._faits.append(fait)
        return fait

    def documenter(self, fait_id, chemin_piece, precision=None):
        """Promeut une déclaration en fait DOCUMENTÉ — pièce obligatoire.

        La pièce doit exister : son empreinte est calculée, pas déclarée.
        """
        fait = self._trouver(fait_id)
        if fait["etat"] == "MANQUANT":
            raise ValueError("%s est une information manquante : rien à documenter" % fait_id)
        if not chemin_piece:
            raise ValueError("documenter %s exige le chemin d'une pièce" % fait_id)
        fait["empreinte_piece"] = empreinte_fichier(chemin_piece)
        fait["piece"] = os.path.abspath(chemin_piece)
        fait["etat"] = "DOCUMENTE"
        if precision:
            fait["precision"] = precision
        return fait

    def marquer_a_confirmer(self, fait_id, raison):
        fait = self._trouver(fait_id)
        fait["etat"] = "A_CONFIRMER"
        fait["precision"] = raison
        return fait

    def ecarter(self, fait_id, raison):
        fait = self._trouver(fait_id)
        fait["ecarte"] = True
        fait["precision"] = raison
        return fait

    def nommer_manquant(self, libelle, pourquoi=None):
        """Déclare une information MANQUANTE. Ne crée aucune valeur par défaut."""
        fait = {
            "fait_id": "M%02d" % (sum(1 for f in self._faits if f["etat"] == "MANQUANT") + 1),
            "libelle": str(libelle).strip(),
            "date_fait": None,
            "precision": pourquoi,
            "etat": "MANQUANT",
            "piece": None,
            "empreinte_piece": None,
            "date_ajout": horodatage(),
            "ecarte": False,
        }
        self._faits.append(fait)
        return fait

    # -- lecture ----------------------------------------------------------
    def _trouver(self, fait_id):
        for fait in self._faits:
            if fait["fait_id"] == fait_id:
                return fait
        raise KeyError("fait inconnu : %r" % (fait_id,))

    def tous(self, inclure_ecartes=False):
        if inclure_ecartes:
            return [dict(f) for f in self._faits]
        return [dict(f) for f in self._faits if not f["ecarte"]]

    def par_etat(self, etat):
        if etat not in ETATS_FAIT:
            raise ValueError("état de fait inconnu : %r" % (etat,))
        return [f for f in self.tous() if f["etat"] == etat]

    @property
    def manquants(self):
        return self.par_etat("MANQUANT")

    @property
    def declares(self):
        return self.par_etat("DECLARE_PAR_L_UTILISATEUR")

    @property
    def documentes(self):
        return self.par_etat("DOCUMENTE")

    def resume(self):
        """Résumé neutre : compte par état, en NOMMANT les manquants.

        Aucun état n'est omis : un compte à zéro est affiché comme zéro.
        """
        compte = {etat: len(self.par_etat(etat)) for etat in ETATS_FAIT}
        return {
            "dossier_id": self.dossier_id,
            "nb_faits": len(self.tous()),
            "compte_par_etat": compte,
            "tous_les_etats_nommes": compte,
            "informations_manquantes": [
                {"libelle": f["libelle"], "pourquoi": f["precision"]} for f in self.manquants
            ],
            "avertissement": (
                "Les faits DECLARE_PAR_L_UTILISATEUR ne sont pas établis : ils "
                "représentent le récit reçu, pas une preuve."
            ),
        }

    def to_dict(self):
        return {
            "dossier_id": self.dossier_id,
            "faits": self.tous(inclure_ecartes=True),
            "resume": self.resume(),
        }

    @classmethod
    def depuis_dict(cls, data):
        """Reconstruit une collecte à partir d'une sérialisation.

        Permet de rouvrir un dossier sans repasser par la saisie : les statuts
        (DECLARE / DOCUMENTE / MANQUANT) sont restaurés tels quels, jamais déduits.
        """
        objet = cls(data.get("dossier_id"))
        objet._faits = [dict(f) for f in (data or {}).get("faits", [])]
        return objet
