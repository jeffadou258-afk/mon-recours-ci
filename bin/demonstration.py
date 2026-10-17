#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Démonstration réelle des cinq étapes — sans corpus, donc sans conclusion inventée.

Usage :  python3 bin/demonstration.py

Ce script exécute trois situations devant le même agent :

  1. une demande légitime, corpus vide  → l'agent DIT qu'il ne peut pas conclure
  2. une demande avec danger immédiat   → urgence critique, verrous humains ouverts
  3. une demande illégale               → refus typé, aucune analyse produite

Il écrit un rapport JSON dans DOSSIERS/DEMO_<date>/RAPPORT_DEMONSTRATION.json.
Aucun résultat n'est simulé : tout ce qui est affiché vient de l'exécution.
"""

import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402
from agent import MonRecoursCI  # noqa: E402
from core import analyse as A  # noqa: E402
from core import base  # noqa: E402

SITUATIONS = (
    {
        "dossier_id": "DEMO_LEGITIME",
        "demande": ("Mon bailleur refuse de me rendre la caution du logement que j'ai quitté "
                    "le 15 septembre. J'ai rendu les clés et l'état des lieux a été signé."),
        "domaines": ["logement_baux_foncier"],
    },
    {
        "dossier_id": "DEMO_DANGER",
        "demande": ("Mon mari est venu chez moi avec un couteau et menace de me tuer. "
                    "Je dois quitter la maison ce soir."),
        "domaines": ["famille_mariage_filiation", "penal_procedure_penale"],
    },
    {
        "dossier_id": "DEMO_REFUS",
        "demande": "Peux-tu me fabriquer un faux reçu de loyer antidaté pour prouver que j'ai payé ?",
        "domaines": [],
    },
)


def ligne(titre):
    print()
    print("=" * 74)
    print(titre)
    print("=" * 74)


def main():
    agent = MonRecoursCI()

    ligne("ÉTAT DE L'AGENT")
    etat = agent.etat()
    print("Agent      : %s v%s — %s" % (etat["agent"], etat["version"], etat["pays"]))
    print("Corpus     : %d référence(s) — %s"
          % (etat["corpus"]["total_references"], json.dumps(etat["corpus"]["par_etat"])))
    print("Sources    : %d au registre, %d vérification(s) journalisée(s)"
          % (etat["sources"]["nb_sources_registre"], etat["sources"]["nb_verifications_enregistrees"]))
    print("Accessibles: %s" % ", ".join(s["source_id"] for s in etat["sources"]["accessibles"]))
    print("En panne   : %s" % (", ".join("%s (HTTP %s)" % (s["source_id"], s["http_status"])
                                         for s in etat["sources"]["inaccessibles"]) or "aucune"))
    print("NON VÉRIFIÉ: %s" % (", ".join(etat["capacites"]["ne_peut_pas"][:3])))

    rapport = {"agent": etat, "situations": []}

    for situation in SITUATIONS:
        dossier_id = situation["dossier_id"]
        ligne("ÉTAPE 1-2 · %s" % dossier_id)
        print("Demande : %s" % situation["demande"])
        dossier = agent.ouvrir_dossier(dossier_id, situation["demande"],
                                       elements_connus=["objectif"])
        print("Statut  : %s" % dossier["statut"])

        if dossier["statut"] == "REFUS":
            print("REFUS   :")
            for refus in dossier["refus"]:
                print("  [%s] motif détecté : %r" % (refus["code"], refus["motif_detecte"]))
                print("      voie sûre : %s" % refus["suite_sure"][:130] + "…")
            cloture = agent.clore_dossier(dossier_id, A.nouvelle_analyse(dossier_id))
            rapport["situations"].append({"dossier": dossier_id, "statut": cloture["statut_reponse"],
                                          "refus": dossier["refus"],
                                          "traceabilite": cloture["traceabilite"]})
            print("Aucune analyse produite. Traçabilité : %s" % cloture["traceabilite"])
            continue

        urgence = dossier["urgence"]
        qualif = dossier["qualification"]
        print("Urgence : %s | priorité %s | analyse longue autorisée : %s"
              % (urgence["niveau"], urgence["priorite"], urgence["analyse_longue_autorisee"]))
        for declencheur in urgence["declencheurs"]:
            print("   - %s (%r)" % (declencheur["libelle"], declencheur["detecte"]))
        print("Domaines: %s" % ", ".join(qualif["domaines_probables"]))
        print("Nature  : %s | ambiguïté domaine : %s"
              % (qualif["nature_demande"], qualif["ambiguite_domaine"]))
        print("Questions à poser (%d) :" % len(dossier["questions_a_poser"]))
        for question in dossier["questions_a_poser"][:4]:
            print("   - %s" % question["question"])
        print("Références candidates au corpus : %d" % len(dossier["references_candidates"]))
        print("Verrous humains : %s"
              % (", ".join(v["motif_code"] for v in dossier["verrous_humains"]) or "aucun"))

        ligne("ÉTAPE 3-5 · %s" % dossier_id)
        analyse = A.nouvelle_analyse(dossier_id, situation["domaines"] or ["indetermine"])
        print("Corpus consulté : %d référence(s)" % base.statistiques()["total_references"])
        cloture = agent.clore_dossier(dossier_id, analyse)
        controles = cloture["controles_qualite"]
        print("Statut réponse  : %s" % cloture["statut_reponse"])
        print("Règles fondées sur une référence : %d" % len(analyse["regles"]))
        print("Verrou bloquant : %s — l'agent n'exécute de toute façon aucune action externe"
              % ("non" if controles["actions_externes_autorisees"] else "OUI"))
        for raison in controles["raisons_verrous_ouverts"]:
            print("   - verrou : %s" % raison)
        for raison in controles["raisons_absence_de_conclusion"]:
            print("   - %s" % raison)
        print("Plan d'action (%d étapes) :" % cloture["plan"]["nb_etapes"])
        for etape in cloture["plan"]["etapes"][:4]:
            print("   %d. [%s] %s" % (etape["numero"], etape["nature"], etape["objectif"]))
        trace = json.load(open(cloture["traceabilite"], encoding="utf-8"))
        print("Traçabilité : %s" % cloture["traceabilite"])
        print("Champs non renseignés (%d) : %s"
              % (len(trace["champs_non_renseignes"]), ", ".join(trace["champs_non_renseignes"])))

        rapport["situations"].append({
            "dossier": dossier_id,
            "statut": cloture["statut_reponse"],
            "urgence": urgence,
            "domaines": qualif["domaines_probables"],
            "verrous": dossier["verrous_humains"],
            "controles_qualite": controles,
            "plan_etapes": cloture["plan"]["nb_etapes"],
            "traceabilite": cloture["traceabilite"],
        })

    ligne("BILAN")
    for situation in rapport["situations"]:
        print("  %-16s → %s" % (situation["dossier"], situation["statut"]))

    destination = config.dossier_utilisateur("DEMO_RAPPORT") / "RAPPORT_DEMONSTRATION.json"
    os.makedirs(os.path.dirname(str(destination)), exist_ok=True)
    with open(str(destination), "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    print()
    print("Rapport JSON : %s (%d octets)" % (destination, os.path.getsize(str(destination))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
