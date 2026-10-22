#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Mesure RÉELLE du fournisseur DeepSeek sur les questions de Mon Recours CI.

Ce que ce script produit, et rien d'autre :
  * jetons d'entrée/sortie réellement facturés, latence, validité du JSON ;
  * combien de fiches le modèle propose, combien survivent à chaque contrôle ;
  * le coût constaté, aux tarifs publiés.

Ce qu'il ne fait JAMAIS :
  * afficher la clé (lue dans l'environnement ou ~/.monrecours/deepseek.key) ;
  * écrire le récit d'une personne ni la réponse brute du modèle ;
  * toucher au registre de production (il écrit dans un registre de mesure).

Usage : MONRECOURS_LLM_API_KEY=... python bin/mesurer_deepseek.py
        (ou laisser le script lire ~/.monrecours/deepseek.key, en 600)
"""
import json
import os
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

# Le registre de mesure est isolé : la mesure ne doit pas consommer le plafond
# du service.
os.environ.setdefault("MONRECOURS_LLM_REGISTRE",
                      os.path.join(RACINE, "RUNTIME", "mesure_deepseek.json"))

from core import catalogue, clarification, llm  # noqa: E402

# Tarifs publiés (api-docs.deepseek.com), en dollars par million de jetons.
TARIF_ENTREE_HORS_POINTE = 0.15
TARIF_SORTIE_HORS_POINTE = 0.60

QUESTIONS = [
    ("caution (fiche attendue)", "Mon bailleur refuse de me rendre la caution de deux mois."),
    ("naissance (aucune fiche)", "Je veux déclarer la naissance de mon enfant à l'état civil."),
    ("salaire saisi (piège)", "On a saisi mon salaire ce mois-ci."),
    ("compte saisi (piège)", "Ils ont saisi mon compte bancaire."),
    ("appartement à récupérer", "Mon propriétaire veut récupérer son appartement pour y habiter."),
    ("consommation (aucune fiche)", "Le magasin refuse de me rembourser un produit défectueux."),
    ("association (aucune fiche)", "Je veux créer une association dans mon village."),
]


def cle():
    valeur = os.environ.get("MONRECOURS_LLM_API_KEY")
    if valeur:
        return valeur.strip()
    chemin = os.path.expanduser("~/.monrecours/deepseek.key")
    try:
        with open(chemin, encoding="utf-8") as flux:
            return flux.read().strip()
    except OSError:
        raise SystemExit("clé absente : ni MONRECOURS_LLM_API_KEY ni %s" % chemin)


def main():
    adaptateur = llm.charger_adaptateur_http()
    if adaptateur is None or not hasattr(adaptateur, "FournisseurDeepSeek"):
        raise SystemExit("adaptateur DeepSeek introuvable")
    fournisseur = adaptateur.FournisseurDeepSeek(cle=cle())
    if not fournisseur.disponible():
        raise SystemExit("fournisseur indisponible : clé vide")

    fiches = catalogue.charger()
    guide = clarification.charger(fiches)
    lignes, jetons_entree, jetons_sortie = [], 0, 0

    for etiquette, question in QUESTIONS:
        debut = time.time()
        rapport = llm.comprendre(question, fiches, guide, fournisseur=fournisseur)
        latence = time.time() - debut
        consommation = getattr(fournisseur, "derniere_consommation", None) or {}
        entree = int(consommation.get("entree") or 0)
        sortie = int(consommation.get("sortie") or 0)
        jetons_entree += entree
        jetons_sortie += sortie

        proposees = rapport.get("fiches") or []
        validees = []
        if proposees:
            candidates = [f for f in fiches if f["id"] in proposees]
            validees, rejets = catalogue.valider_fiches_proposees(
                candidates, question, fiches=fiches,
                domaines=[f["domaine"] for f in candidates])
            for rejet in rejets:
                rapport.setdefault("rejets", []).append(rejet)
        lignes.append({
            "etiquette": etiquette,
            "mode": rapport.get("mode"),
            "json_valide": rapport.get("mode") == "llm",
            "proposees": len(proposees),
            "ids_proposes": list(proposees),
            "ids_retenus": [f["id"] for f in validees],
            "retenues_apres_comprehension": len(proposees),
            "retenues_apres_pertinence": len(validees),
            "rejets": len(rapport.get("rejets") or []),
            "erreur": (rapport.get("erreur") or "")[:80] or None,
            "jetons_entree": entree,
            "jetons_sortie": sortie,
            "latence_s": round(latence, 2),
        })

    cout = (jetons_entree / 1e6) * TARIF_ENTREE_HORS_POINTE + \
           (jetons_sortie / 1e6) * TARIF_SORTIE_HORS_POINTE
    total_proposees = sum(l["proposees"] for l in lignes)
    total_retenues = sum(l["retenues_apres_pertinence"] for l in lignes)
    json_ok = sum(1 for l in lignes if l["json_valide"])

    print("  %-28s %-6s %-5s %-9s %-10s %-6s %s"
          % ("question", "mode", "prop.", "pertinent.", "rejets", "lat.", "jetons"))
    for ligne in lignes:
        print("  %-28s %-6s %-5d %-9d %-10d %-6.1fs %d/%d"
              % (ligne["etiquette"], ligne["mode"], ligne["proposees"],
                 ligne["retenues_apres_pertinence"], ligne["rejets"],
                 ligne["latence_s"], ligne["jetons_entree"], ligne["jetons_sortie"]))
    print()
    print("  JSON exploitable ....... %d/%d" % (json_ok, len(lignes)))
    print("  fiches proposées ....... %d" % total_proposees)
    print("  fiches retenues ........ %d (%.0f %% de rejet par les contrôles)"
          % (total_retenues,
             100.0 * (total_proposees - total_retenues) / total_proposees if total_proposees else 0))
    print("  jetons ................. %d entrée / %d sortie" % (jetons_entree, jetons_sortie))
    print("  coût réel (hors pointe)  %.4f $  (~%.1f FCFA)"
          % (cout, cout * 655))
    print("  coût projeté 1 000 consult. %.2f $" % (cout / len(lignes) * 1000))

    rapport_final = {
        "fournisseur": "deepseek",
        "modele": fournisseur.modele,
        "questions": len(lignes),
        "json_exploitable": "%d/%d" % (json_ok, len(lignes)),
        "fiches_proposees": total_proposees,
        "fiches_retenues": total_retenues,
        "jetons": {"entree": jetons_entree, "sortie": jetons_sortie},
        "cout_usd": round(cout, 5),
        "detail": lignes,
    }
    chemin = os.path.join(RACINE, "RUNTIME", "mesure_deepseek.json")
    os.makedirs(os.path.dirname(chemin), mode=0o700, exist_ok=True)
    with open(chemin, "w", encoding="utf-8") as flux:
        json.dump(rapport_final, flux, ensure_ascii=False, indent=2)
    os.chmod(chemin, 0o600)
    print("  rapport : %s" % chemin)


if __name__ == "__main__":
    main()
