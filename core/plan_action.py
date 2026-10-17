# -*- coding: utf-8 -*-
"""Étape 5 — Plan d'action, orientations et VERROUS HUMAINS.

Deux principes :

1. **Un verrou ne se ferme jamais tout seul.** `HumanGate.statut` vaut `OUVERT`
   à la création. Seule une décision humaine explicite le ferme, et cette
   décision doit porter un marqueur humain (nom/auteur) + un motif. Sans ces
   deux éléments, la fermeture est refusée par exception.

2. **Une étape sans automate est déclarée `manuel`.** Elle n'est jamais
   présentée comme automatisable, et une étape d'orientation vers un humain est
   `orientation_humaine`.

Ce module n'énonce aucun délai, aucune sanction et aucune procédure : il
organise des actions administratives neutres (rassembler, demander, conserver,
consulter).
"""

import datetime
import re

from config import NATURES_ETAPE

MOTIFS_VERROU = {
    "URGENCE_CRITIQUE": "Danger immédiat : la sécurité prime sur l'analyse.",
    "RISQUE_PERTE_DE_DROITS": "Risque d'expulsion, de perte importante de droits ou échéance critique.",
    "PROCEDURE_JUDICIAIRE": "Procédure judiciaire, détention, accusation pénale ou décision exécutoire.",
    "VIOLENCE_OU_MENACE": "Situation de violence, de menace ou de danger immédiat.",
    "PERSONNE_VULNERABLE": "Dossier concernant un enfant ou une personne vulnérable.",
    "SOURCES_CONTRADICTOIRES": "Sources contradictoires ou insuffisantes pour conclure.",
    "EXPERTISE_NECESSAIRE": "Une expertise, une représentation ou une consultation professionnelle est nécessaire.",
    "ACTION_ENGAGEANTE": "L'utilisateur veut envoyer un courrier officiel ou engager une procédure.",
    "RISQUE_ERREUR_SERIEUX": "Risque sérieux d'erreur ou de conséquences importantes détecté.",
    "PERMISSION_MANQUANTE": "Une autorisation nécessaire n'a pas été donnée.",
}

_DOMAINE_VERS_VERROU = {
    "penal_procedure_penale": "PROCEDURE_JUDICIAIRE",
    # `famille_mariage_filiation` n'est PLUS mappé automatiquement : un divorce entre
    # adultes ou une succession ne concernent pas forcément une personne vulnérable.
    # Le verrou suit désormais les MOTIFS réels (enfant, mineur, handicap…), pas
    # l'étiquette du domaine. Défaut constaté : « mon bailleur garde ma caution »
    # déclenchait « personne vulnérable » parce que le domaine famille était reconnu
    # (mot-clé « garde ») ; la protection devenait du bruit, donc elle cessait d'alerter.
}

_MOTIFS_VULNERABILITE = (
    r"\b(enfant|mineur|bebe|nouveau-?ne)\b",
    r"\b(vieill|handicap|malade|vulnerab|grossesse|enceinte)\w*",
)

_MOTIFS_JUDICIAIRE = (
    r"\b(tribunal|procureur|juge|audience|assignation|jugement|detention|garde a vue|ecroue)\w*",
)


def horodatage():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


class HumanGate(object):
    """Verrou humain. OUVERT par défaut, fermable uniquement par une décision humaine."""

    def __init__(self, motif_code, precision=None, dossier_id=None):
        if motif_code not in MOTIFS_VERROU:
            raise ValueError("motif de verrou inconnu : %r" % (motif_code,))
        self.dossier_id = dossier_id
        self.motif_code = motif_code
        self.motif = MOTIFS_VERROU[motif_code]
        self.precision = precision
        self.statut = "OUVERT"
        self.date_ouverture = horodatage()
        self.decision = None

    @property
    def ouvert(self):
        return self.statut == "OUVERT"

    def fermer_par_decision_humaine(self, decision, marqueur_humain, commentaire=""):
        """Ferme le verrou. Exige une décision ET un marqueur humain explicite.

        `decision` : "autorise" | "refuse" | "revision_demandee"
        `marqueur_humain` : nom, identifiant ou canal d'où vient la décision.
        """
        if decision not in ("autorise", "refuse", "revision_demandee"):
            raise ValueError("décision inconnue : %r" % (decision,))
        if not (marqueur_humain and str(marqueur_humain).strip()):
            raise ValueError(
                "fermeture refusée : aucune source humaine identifiée. Un verrou ne se "
                "ferme pas automatiquement."
            )
        self.statut = {"autorise": "AUTORISE", "refuse": "REFUSE",
                       "revision_demandee": "REVISION_DEMANDEE"}[decision]
        self.decision = {
            "decision": decision,
            "marqueur_humain": str(marqueur_humain).strip(),
            "commentaire": commentaire,
            "date_decision": horodatage(),
        }
        return self.decision

    def to_dict(self):
        return {
            "dossier_id": self.dossier_id,
            "motif_code": self.motif_code,
            "motif": self.motif,
            "precision": self.precision,
            "statut": self.statut,
            "ouvert": self.ouvert,
            "date_ouverture": self.date_ouverture,
            "decision": self.decision,
            "rappel": "Un verrou ouvert bloque toute action externe jusqu'à décision humaine.",
        }


def _texte_faits(faits):
    if hasattr(faits, "tous"):
        return " ".join(f["libelle"] for f in faits.tous())
    return " ".join(str(f) for f in (faits or []))


def evaluer_verrous(urgence, domaines, texte=""):
    """Détermine les verrous humains requis. Motifs cités, jamais résumés en « risque »."""
    from core.garde_fous import normaliser

    norm = normaliser(texte)
    codes = []
    precisions = {}

    if urgence.get("niveau") == "CRITIQUE":
        codes.append("URGENCE_CRITIQUE")
        precisions["URGENCE_CRITIQUE"] = "déclencheurs : " + ", ".join(
            d["libelle"] for d in urgence.get("declencheurs", [])
        )
        codes.append("VIOLENCE_OU_MENACE")

    if urgence.get("niveau") == "ELEVEE":
        codes.append("RISQUE_PERTE_DE_DROITS")

    for domaine in domaines or []:
        code = _DOMAINE_VERS_VERROU.get(domaine)
        if code and code not in codes:
            codes.append(code)

    if any(re.search(motif, norm) for motif in _MOTIFS_VULNERABILITE):
        if "PERSONNE_VULNERABLE" not in codes:
            codes.append("PERSONNE_VULNERABLE")
        precisions["PERSONNE_VULNERABLE"] = "motif détecté dans le récit"
    if any(re.search(motif, norm) for motif in _MOTIFS_JUDICIAIRE) and "PROCEDURE_JUDICIAIRE" not in codes:
        codes.append("PROCEDURE_JUDICIAIRE")
        precisions["PROCEDURE_JUDICIAIRE"] = "procédure en cours détectée dans le récit"

    return [HumanGate(code, precisions.get(code)).to_dict() for code in codes]


def _etape(numero, objectif, nature, detail, interlocuteur=None, automatise=False):
    if nature not in NATURES_ETAPE:
        raise ValueError("nature d'étape inconnue : %r" % (nature,))
    return {
        "numero": numero,
        "objectif": objectif,
        "nature": nature,
        "detail": detail,
        "interlocuteur": interlocuteur,
        "automatise_par_l_agent": bool(automatise and nature == "automatisable"),
    }


_ORIENTATIONS = {
    "logement_baux_foncier": "Un professionnel du droit ou le service compétent en matière de logement.",
    "travail": "L'inspection du travail compétente, ou un professionnel du droit du travail.",
    "famille_mariage_filiation": "Un professionnel du droit de la famille ; les services sociaux si un enfant est concerné.",
    "contrats_dettes_commerce": "Un professionnel du droit des affaires ou un commissaire de justice.",
    "penal_procedure_penale": "Le parquet compétent, un commissariat ou la gendarmerie, et un avocat.",
    "consommation": "Le service de contrôle compétent, ou une association de consommateurs.",
    "associations_organisations_religieuses": "Le service administratif compétent pour les associations.",
    "donnees_personnelles_numerique": "L'autorité de protection des données compétente, et la plateforme concernée.",
    "administratif_voies_de_recours": "L'administration qui a pris la décision, puis l'autorité de recours compétente.",
    "indetermine": "Un professionnel du droit, après qualification du domaine.",
}


def construire_plan(dossier_id, domaines, urgence, faits=None, references=None, documents_prepares=None):
    """Construit le plan d'action. Chaque étape porte sa nature et son interlocuteur."""
    etapes = []
    n = 1

    etapes.append(_etape(
        n, "Mettre les pièces en sécurité", "automatisable",
        "Classer et copier les documents disponibles (écrits, reçus, messages). "
        "Aucune pièce n'est modifiée ni supprimée.", automatise=True))
    n += 1

    if urgence.get("niveau") == "CRITIQUE":
        etapes.append(_etape(
            n, "Assurer la sécurité avant toute démarche", "orientation_humaine",
            urgence.get("consigne", "Orientation humaine immédiate."),
            interlocuteur="Services d'urgence et un interlocuteur humain habilité"))
        n += 1

    if faits is not None:
        manquants = faits.manquants if hasattr(faits, "manquants") else []
        etapes.append(_etape(
            n, "Réunir les informations manquantes", "manuel",
            "Éléments à réunir : " + ("; ".join(f["libelle"] for f in manquants)
                                      if manquants else "aucun élément manquant déclaré"),
            automatise=False))
        n += 1

    etapes.append(_etape(
        n, "Vérifier chaque référence juridique utilisée", "automatisable",
        "Contrôler l'accessibilité de la source et l'état de vérification de chaque "
        "référence citée. Une référence non vérifiée est signalée comme telle.",
        automatise=True))
    n += 1

    if documents_prepares:
        etapes.append(_etape(
            n, "Valider les brouillons avant tout envoi", "orientation_humaine",
            "Brouillons préparés : " + ", ".join(documents_prepares) +
            ". Aucun envoi n'est effectué par l'agent.",
            interlocuteur="L'utilisateur (ou un professionnel habilité)"))
        n += 1

    etapes.append(_etape(
        n, "Saisir l'interlocuteur compétent", "manuel",
        "Adresser la demande à l'interlocuteur identifié et conserver la preuve de "
        "dépôt (récépissé, accusé, capture horodatée).",
        interlocuteur="; ".join(_ORIENTATIONS.get(d, _ORIENTATIONS["indetermine"])
                                for d in (domaines or ["indetermine"]))))
    n += 1

    etapes.append(_etape(
        n, "Conserver une trace de chaque échange", "manuel",
        "Archiver les réponses reçues et les dates de chaque échange pour le suivi.",
        automatise=False))

    return {
        "dossier_id": dossier_id,
        "etapes": etapes,
        "nb_etapes": len(etapes),
        "verrous": evaluer_verrous(urgence, domaines, _texte_faits(faits)),
        "orientations": sorted({_ORIENTATIONS.get(d, _ORIENTATIONS["indetermine"])
                                for d in (domaines or ["indetermine"])}),
        "avertissement": (
            "Ce plan organise des démarches. Il ne constitue pas une consultation "
            "juridique et ne garantit aucun résultat."
        ),
    }


def actions_externes_autorisees(plan):
    """Retourne (autorise: bool, raisons: list).

    Tant qu'un verrou est ouvert, aucune action externe n'est autorisée : envoyer
    un courrier, engager une procédure ou déposer un document.
    """
    ouverts = [v for v in plan.get("verrous", []) if v.get("ouvert")]
    if ouverts:
        return False, [
            "%s — %s" % (v["motif_code"], v["motif"]) for v in ouverts
        ]
    return True, []
