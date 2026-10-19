# -*- coding: utf-8 -*-
"""Évaluation d'un scénario d'audit contre le VRAI moteur (service.ouvrir / repondre).

Utilisé par `tests/test_audit_24_domaines.py` et par `bin/audit_domaines.py` :
les deux lisent exactement les mêmes résultats, ce qui rend le rapport traçable.
"""

import os
import shutil
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import config  # noqa: E402
from core import catalogue, clarification, corpus, service  # noqa: E402
from core.base import normaliser  # noqa: E402

NIVEAUX = {"NORMALE": 0, "ELEVEE": 1, "CRITIQUE": 2}
_INDEX = None


def _index():
    global _INDEX
    if _INDEX is None:
        fiches = catalogue.charger()
        _INDEX = {"par_titre": {(f["titre"], str(f["article"])): f for f in fiches},
                  "par_id": {f["id"]: f for f in fiches}}
    return _INDEX


def _id(vue_fiche):
    f = _index()["par_titre"].get((vue_fiche.get("titre"), str(vue_fiche.get("article"))))
    return f["id"] if f else None


def _textes_produits(reponse):
    """Ce que le service a RÉDIGÉ (hors citations mot pour mot) : lectures, démarches, points."""
    sections = reponse.get("sections") or {}
    textes = [r.get("lecture") or "" for r in sections.get("2_droit") or []]
    textes += [l.get("lecture") or "" for l in (sections.get("3_application_aux_faits") or {}).get("lignes", [])]
    textes += list(sections.get("4_demarches") or [])
    textes += list(sections.get("5_a_verifier") or [])
    textes += [reponse.get("message") or ""]
    return [t for t in textes if t]


def _nombres_autorises(fiches, recit):
    autorises = set(clarification._nombres(normaliser(recit)))
    for f in fiches:
        article = corpus.obtenir_article_par_reference(f["ref_id"], f["article"]) or {}
        autorises |= clarification._nombres(normaliser(article.get("texte") or f["citation"]))
        autorises |= set((f.get("numero_texte") or "").replace("-", " ").split())
    return autorises


def evaluer(code, type_cas, scenario, prefixe="AUDIT24"):
    """Exécute un scénario. Renvoie {observe, ecarts, ok}. Aucun effet durable (dossier supprimé)."""
    attendu = scenario["attendu"]
    recit = scenario["recit"]
    identifiant = "%s_%02d_%s" % (prefixe, code, type_cas)
    observe, ecarts = {}, []
    try:
        resultat = service.ouvrir(identifiant, recit)
        if not resultat["ok"]:
            return {"observe": {"erreur": resultat["erreur"]}, "ecarts": ["service en erreur"], "ok": False}
        data = resultat["data"]
        reponse_ouverture = data.get("reponse") or {}
        fiches_vues = [_id(f) for f in data.get("fiches_identifiees") or []]
        observe = {
            "etape": data.get("etape"),
            "fiches": fiches_vues,
            "questions": len(data.get("questions") or []),
            "urgence": (data.get("urgence") or {}).get("niveau", "NORMALE"),
            "verrous": len(data.get("verrous_humains") or []),
            "vision": [v["code"] for v in reponse_ouverture.get("domaines_vision") or []],
        }
        if "etape" in attendu and observe["etape"] != attendu["etape"]:
            ecarts.append("étape %s au lieu de %s" % (observe["etape"], attendu["etape"]))
        manquantes = set(attendu.get("fiches") or ()) - set(fiches_vues)
        if manquantes:
            ecarts.append("fiches attendues absentes : %s" % sorted(manquantes))
        servies_a_tort = set(attendu.get("interdites") or ()) & set(fiches_vues)
        if servies_a_tort:
            ecarts.append("fiches servies à tort : %s" % sorted(servies_a_tort))
        if observe["questions"] < attendu.get("questions_min", 0):
            ecarts.append("%d question(s), %d attendue(s) au moins"
                          % (observe["questions"], attendu["questions_min"]))
        if attendu.get("urgence_min") and \
                NIVEAUX[observe["urgence"]] < NIVEAUX[attendu["urgence_min"]]:
            ecarts.append("urgence %s, au moins %s attendue" % (observe["urgence"], attendu["urgence_min"]))
        if attendu.get("vision") and observe["etape"] == "hors_catalogue" \
                and attendu["vision"] not in observe["vision"]:
            ecarts.append("domaine %d non reconnu (reconnus : %s)" % (attendu["vision"], observe["vision"]))
        if observe["etape"] == "hors_catalogue" and \
                (reponse_ouverture.get("sections") or {}).get("6_sources"):
            ecarts.append("hors catalogue mais des sources sont servies")

        if attendu.get("abstention"):
            ecarts += _controle_abstention(identifiant, data, recit, observe)
    finally:
        shutil.rmtree(str(config.dossier_utilisateur(identifiant)), ignore_errors=True)
    return {"observe": observe, "ecarts": ecarts, "ok": not ecarts}


def _controle_abstention(identifiant, data, recit, observe):
    """Parcours complet en répondant « je ne sais pas », puis aucun nombre non sourcé."""
    ecarts = []
    reponse = data.get("reponse") or {}
    fiches = [_index()["par_id"][i] for i in observe["fiches"] if i in _index()["par_id"]]
    if data.get("etape") == "clarification":
        suite = data
        for _ in range(clarification.TOURS_MAX + 1):
            resultat = service.repondre(identifiant, {})
            if not resultat["ok"]:
                observe["fin"] = resultat["erreur"]["code"]
                return ecarts  # analyse refusée : aucune affirmation servie
            suite = resultat["data"]
            if suite["etape"] != "clarification":
                break
        reponse = suite.get("reponse") or {}
        observe["fin"] = reponse.get("statut_reponse")
        cites = {(s.get("numero_texte"), str(s.get("article"))) for s in
                 (reponse.get("sections") or {}).get("6_sources") or []}
        permis = {(f.get("numero_texte"), str(f["article"])) for f in fiches}
        if cites - permis:
            ecarts.append("articles cités hors des fiches servies : %s" % sorted(cites - permis))
    autorises = _nombres_autorises(fiches, recit)
    for texte in _textes_produits(reponse):
        ajoutes = clarification._nombres(normaliser(texte)) - autorises
        if ajoutes:
            ecarts.append("nombre non sourcé %s dans : %s" % (sorted(ajoutes), texte[:90]))
    return ecarts
