# -*- coding: utf-8 -*-
"""Génère l'inventaire de couverture juridique et le rapport de mission.

    python3 bin/rapport_couverture.py

Écrit :
    KNOWLEDGE/INVENTAIRE_COUVERTURE.json   (machine)
    KNOWLEDGE/INVENTAIRE_COUVERTURE.md     (fiches par domaine)
    RAPPORT_FINAL_MISSION.json             (rapport de mission)

Tous les chiffres viennent de la base et du dossier de tests : rien n'est saisi
à la main ni estimé. Si une mesure n'est pas disponible, elle est marquée
`INDISPONIBLE` plutôt que remplie avec une valeur plausible.
"""

import datetime
import json
import os
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from config import COUVERTURE_DOMAINES, DOMAINES_JURIDIQUES, STATUTS_DOMAINE  # noqa: E402
from core import corpus, couverture  # noqa: E402

KNOWLEDGE = os.path.join(RACINE, "KNOWLEDGE")


def executer_tests():
    """Lance la suite et lit son verdict réel. Ne devine jamais le résultat."""
    try:
        resultat = subprocess.run([sys.executable, "tests/run_all.py"], cwd=RACINE,
                                  capture_output=True, text=True, timeout=900)
    except Exception as erreur:  # noqa: BLE001
        return {"disponible": False, "raison": str(erreur)}
    lignes = {}
    for ligne in (resultat.stdout or "").splitlines():
        if "=" in ligne and ligne.split("=")[0] in ("TESTS", "VERDICT"):
            cle, _, valeur = ligne.partition("=")
            lignes[cle.strip()] = valeur.strip()
    return {"disponible": True, "exit_code": resultat.returncode,
            "resume": lignes.get("TESTS"), "verdict": lignes.get("VERDICT")}


def inventaire_markdown(inventaire_courant):
    lignes = ["# Inventaire de couverture juridique — Mon Recours CI", "",
              "Généré le %s par `bin/rapport_couverture.py`."
              % inventaire_courant["horodatage"], "",
              "**La réussite des tests ne vaut pas validation juridique par un "
              "professionnel.** Un domaine `TERMINE_TECHNIQUEMENT` reste "
              "`INCOMPLET` au plan juridique : les deux colonnes sont séparées "
              "exprès.", "",
              "| Code | Domaine | Statut technique | Complétude juridique | Documents | "
              "Réf. vérifiées | Articles |", "|---|---|---|---|---|---|---|"]
    for entree in inventaire_courant["domaines"]:
        m = entree["mesures"]
        lignes.append("| %s | %s | `%s` | %s | %s | %s | %s |"
                      % (m["code"], entree["libelle"], entree["statut"],
                         entree["completude_juridique"], m["documents"],
                         m["references_verifiees"], m["articles"]))
    lignes += ["", "**Total** : %d documents, %d articles. Provenance : %s"
               % (inventaire_courant["total_documents"], inventaire_courant["total_articles"],
                  ", ".join("%s = %s" % (o, n)
                            for o, n in sorted(inventaire_courant["articles_par_origine"].items()))),
               "", "## Méthode de comptage", "",
               "> %s" % inventaire_courant["methode_de_comptage"], "",
               "## Ce que le corpus permet, et ce qu'il ne permet pas", "",
               inventaire_courant["avertissement"], ""]
    for entree in inventaire_courant["domaines"]:
        m = entree["mesures"]
        lignes += ["---", "", "## %s — %s (`%s`)" % (m["code"], entree["libelle"],
                                                     entree["domaine"]), "",
                   "* **Statut technique** : `%s` — %s" % (entree["statut"], entree["motif"]),
                   "* **Validation juridique** : `%s` · complétude : `%s`"
                   % (entree["validation_juridique"], entree["completude_juridique"]),
                   "* **Risque** : %s" % (entree["risque"] or "non évalué"),
                   "* **Intervention humaine** : %s"
                   % (entree["validation_humaine_obligatoire"] and "OBLIGATOIRE"
                      or "recommandée selon les faits"), ""]
        if entree["perimetre"]:
            lignes += ["**Périmètre visé**", ""]
            lignes += ["- %s" % sujet for sujet in entree["perimetre"]]
            lignes += [""]
        if entree["sources_tentees"]:
            lignes += ["**Sources interrogées pendant la mission**", "",
                       "| Source | Résultat mesuré | Usage |", "|---|---|---|"]
            for source in entree["sources_tentees"]:
                lignes.append("| %s | %s | %s |" % (source.get("source", ""),
                                                    source.get("resultat", ""),
                                                    source.get("usage", "")))
            lignes += [""]
        if entree["lacunes"]:
            lignes += ["**Lacunes identifiées**", ""]
            lignes += ["- %s" % lacune for lacune in entree["lacunes"]]
            lignes += [""]
        if m["documents"]:
            lignes += ["**Documents indexés**", "",
                       "| Document | Référence | Lecture | Articles |", "|---|---|---|---|"]
            for document in corpus.lister_documents(domaine=entree["domaine"]):
                lignes.append("| `%s` | %s | `%s` | %s |"
                              % (document["doc_id"], document["numero_texte"] or "—",
                                 document["methode_extraction"],
                                 len(corpus.articles_dun_document(document["doc_id"]))))
            lignes += [""]
    return "\n".join(lignes) + "\n"


def main():
    inventaire_courant = couverture.inventaire()
    tests = executer_tests()
    integrite = corpus.verifier_integrite()

    with open(os.path.join(KNOWLEDGE, "INVENTAIRE_COUVERTURE.json"), "w",
              encoding="utf-8") as flux:
        json.dump(inventaire_courant, flux, ensure_ascii=False, indent=1)
    with open(os.path.join(KNOWLEDGE, "INVENTAIRE_COUVERTURE.md"), "w",
              encoding="utf-8") as flux:
        flux.write(inventaire_markdown(inventaire_courant))

    rapport = {
        "genere_le": inventaire_courant["horodatage"],
        "tests": tests,
        "integrite_corpus": {"verdict": integrite["verdict"],
                             "documents": integrite["nb_documents"],
                             "absents": len(integrite["absents"]),
                             "alteres": len(integrite["alteres"])},
        "couverture": inventaire_courant,
        "statuts_disponibles": list(STATUTS_DOMAINE),
        "taxonomie": [dict(e) for e in COUVERTURE_DOMAINES],
        "methodologie": inventaire_courant["methode_de_comptage"],
        "reserves": [
            "Un domaine TERMINE_TECHNIQUEMENT n'est pas juridiquement complet.",
            "Aucun article du corpus n'a été relu par un humain "
            "(VERIFIE_MANUELLEMENT = 0).",
            "TERMINE_ET_VERIFIE est inatteignable tant qu'une relecture humaine "
            "n'est pas tracée.",
            "Les sources secondaires (Laws.Africa, dépôts internationaux) ne sont "
            "jamais promues VERIFIE.",
        ],
    }
    with open(os.path.join(RACINE, "RAPPORT_FINAL_MISSION.json"), "w",
              encoding="utf-8") as flux:
        json.dump(rapport, flux, ensure_ascii=False, indent=1)

    print("Tests            : %s" % (tests.get("resume") or "INDISPONIBLE"))
    print("Verdict          : %s" % (tests.get("verdict") or "INDISPONIBLE"))
    print("Intégrité        : %s (%d documents)" % (integrite["verdict"], integrite["nb_documents"]))
    print("Documents        : %d" % inventaire_courant["total_documents"])
    print("Articles         : %d" % inventaire_courant["total_articles"])
    print("Domaines         : %d" % len(inventaire_courant["domaines"]))
    print("  TERMINE_TECHNIQUEMENT  : %d" % sum(1 for l in inventaire_courant["domaines"]
                                               if l["statut"] == "TERMINE_TECHNIQUEMENT"))
    print("  CORPUS_PARTIEL         : %d" % sum(1 for l in inventaire_courant["domaines"]
                                               if l["statut"] == "CORPUS_PARTIEL"))
    print("  BLOQUE_SOURCE          : %d" % sum(1 for l in inventaire_courant["domaines"]
                                               if l["statut"] == "BLOQUE_SOURCE"))
    print("  NON_DEMARRE            : %d" % sum(1 for l in inventaire_courant["domaines"]
                                               if l["statut"] == "NON_DEMARRE"))
    print("\nÉcrit : KNOWLEDGE/INVENTAIRE_COUVERTURE.{json,md}, RAPPORT_FINAL_MISSION.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
