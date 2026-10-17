# -*- coding: utf-8 -*-
"""Dossier de traçabilité (spec §16) — la preuve de ce qui a été fait et de ce qui manque.

Un dossier de traçabilité qui ne nomme pas ses zones aveugles se lit comme
exhaustif. Ce module impose donc que les informations non renseignées soient
**listées par leur nom** (`champs_non_renseignes`), et non omises.

Le module n'enregistre jamais de contenu de pièce sensible : il enregistre
l'empreinte, le nom du fichier et sa date — pas le texte du document fourni.
"""

import datetime
import json
import os
import tempfile

from config import DOSSIERS_DIR, VERSION, dossier_utilisateur

CHAMPS_ATTENDUS = (
    "demande_et_resume_neutre",
    "questions_posees_et_informations_manquantes",
    "textes_consultes_et_references",
    "articles_effectivement_verifies",
    "dates_consultation_et_etat_verification",
    "distinction_faits_regles_analyse",
    "incertitudes_exceptions_limites",
    "plan_action_et_raison",
    "recommandations_orientation_humaine",
    "resultats_controles_qualite",
    "validations_humaines",
)


def horodatage():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def construire(
    dossier_id,
    demande=None,
    resume_neutre=None,
    faits=None,
    questions=None,
    references_consultees=None,
    articles_verifies=None,
    analyse=None,
    plan=None,
    verrous=None,
    orientations=None,
    controles_qualite=None,
    validations_humaines=None,
    verrous_humains=None,
    refus=None,
    urgence=None,
    qualification=None,
    sources_testees=None,
):
    """Assemble le dossier de traçabilité. Les champs absents sont NOMMÉS."""
    faits_resume = faits.resume() if hasattr(faits, "resume") else (faits or {})
    # Les faits eux-mêmes, pas seulement leur comptage : sans cela la section
    # « distinction » du dossier de traçabilité serait vide alors que des faits
    # déclarés existent — un dossier qui perd ses faits se lit comme un dossier
    # sans faits.
    liste_faits = (faits.tous() if hasattr(faits, "tous")
                   else (faits_resume.get("faits") or []))

    dossier = {
        "dossier_id": dossier_id,
        "agent": {"nom": "Mon Recours CI", "version": VERSION, "pays": "Côte d'Ivoire"},
        "horodatage": horodatage(),
        "demande_et_resume_neutre": {
            "demande": demande,
            "resume_neutre": resume_neutre,
            "avertissement": (
                "Résumé produit à partir du récit de l'utilisateur. Les faits "
                "déclarés ne sont pas établis."
            ),
        },
        "faits": faits_resume,
        "questions_posees_et_informations_manquantes": {
            "questions_posees": questions or [],
            "informations_manquantes": (faits_resume or {}).get("informations_manquantes", []),
        },
        "textes_consultes_et_references": references_consultees or [],
        "articles_effectivement_verifies": articles_verifies or [],
        "dates_consultation_et_etat_verification": _dates_et_etats(references_consultees),
        "distinction_faits_regles_analyse": {
            "faits": liste_faits,
            "faits_declares_non_etablis": [
                f for f in liste_faits if f.get("etat") == "DECLARE_PAR_L_UTILISATEUR"
            ],
            "regles": (analyse or {}).get("regles", []),
            "analysee_appliquee": (analyse or {}).get("applications", []),
            "hypotheses_non_verifiees": (analyse or {}).get("hypotheses", []),
        },
        "incertitudes_exceptions_limites": {
            "incertitudes": (analyse or {}).get("incertitudes", []),
            "limites": (analyse or {}).get("limites", []),
            "avertissements": [
                "Le système ne dit pas qu'un texte est en vigueur sans vérification.",
                "Les domaines qualifiés sont des pistes de routage, pas une qualification juridique.",
            ],
        },
        "plan_action_et_raison": {
            "plan": plan,
            "raison": "Plan proportionné : démarches administratives neutres, aucune action externe automatique.",
        },
        "recommandations_orientation_humaine": orientations or
            [v.get("motif") for v in (verrous or [])],
        "resultats_controles_qualite": controles_qualite or {},
        "validations_humaines": validations_humaines or [],
        "verrous_humains": verrous or verrous_humains or [],
        "urgence": urgence,
        "qualification": qualification,
        "sources_testees": sources_testees or [],
        "refus_opposes": refus or [],
        "conservation": {
            "politique": (
                "Conservation proportionnée : le dossier contient des empreintes et des "
                "références, pas le texte des pièces sensibles fournies."
            ),
            "revision_recommandee": "Supprimer ou archiver le dossier lorsqu'il n'est plus utile.",
        },
    }

    dossier["champs_non_renseignes"] = champs_non_renseignes(dossier)
    return dossier


def _dates_et_etats(references):
    return [
        {
            "ref_id": r.get("ref_id"),
            "date_consultation": r.get("date_consultation"),
            "etat_verification": r.get("etat_verification"),
            "source_url": r.get("source_url"),
        }
        for r in (references or [])
    ]


def champs_non_renseignes(dossier):
    """Liste NOMMÉE de ce qui manque. C'est ce qui rend le dossier honnête."""
    manquants = []
    for champ in CHAMPS_ATTENDUS:
        valeur = dossier.get(champ)
        if valeur is None or valeur == [] or valeur == {} or (
            isinstance(valeur, dict) and not any(
                v for v in valeur.values() if v not in (None, [], {}, "")
            )
        ):
            manquants.append(champ)

    if not (dossier.get("textes_consultes_et_references") or []):
        manquants.append("aucune_reference_juridique_consultee")
    if not (dossier.get("articles_effectivement_verifies") or []):
        manquants.append("aucun_article_verifie")
    if not (dossier.get("validations_humaines") or []):
        manquants.append("aucune_validation_humaine")
    return manquants


def ecrire(dossier, chemin=None):
    """Écrit le dossier en JSON, écriture atomique, confinée au dossier utilisateur."""
    dossier_id = dossier["dossier_id"]
    if chemin is None:
        destination = dossier_utilisateur(dossier_id) / "DOSSIER_TRACABILITE.json"
    else:
        destination = chemin
        racine = os.path.abspath(str(DOSSIERS_DIR))
        if not os.path.abspath(str(destination)).startswith(racine):
            raise ValueError("écriture refusée hors de DOSSIERS/ : %s" % destination)

    os.makedirs(os.path.dirname(str(destination)), exist_ok=True)
    fd, temporaire = tempfile.mkstemp(dir=os.path.dirname(str(destination)), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(dossier, f, ensure_ascii=False, indent=2)
        os.replace(temporaire, str(destination))
    except Exception:
        if os.path.exists(temporaire):
            os.unlink(temporaire)
        raise
    return str(destination)


def lire(dossier_id, chemin=None):
    """Relit le dossier de traçabilité d'un utilisateur donné. Jamais celui d'un autre."""
    if chemin is None:
        chemin = dossier_utilisateur(dossier_id) / "DOSSIER_TRACABILITE.json"
    with open(str(chemin), "r", encoding="utf-8") as f:
        return json.load(f)


def lister_dossiers():
    if not os.path.isdir(str(DOSSIERS_DIR)):
        return []
    resultats = []
    for nom in sorted(os.listdir(str(DOSSIERS_DIR))):
        chemin = DOSSIERS_DIR / nom
        if chemin.is_dir():
            trace = chemin / "DOSSIER_TRACABILITE.json"
            resultats.append({
                "dossier_id": nom,
                "tracabilite_presente": os.path.isfile(str(trace)),
                "octets": os.path.getsize(str(trace)) if os.path.isfile(str(trace)) else 0,
            })
    return resultats
