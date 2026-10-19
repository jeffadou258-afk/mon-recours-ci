# -*- coding: utf-8 -*-
"""Audit reproductible des 24 domaines : inventaire + scénarios exécutés + statut mesuré.

    python3 bin/audit_domaines.py            # écrit reports/inventaire_24_domaines.json
                                             # et affiche la matrice

Tout chiffre du rapport vient de ce fichier JSON, produit en interrogeant le
corpus, le catalogue, le guide de questions et le VRAI service (scénarios de
tests/scenarios_24_domaines.py). Rien n'est déclaré à la main, sauf les
« lacunes » du registre KNOWLEDGE/domaines_24.json, qui sont des constats.

Règle de statut (technique — jamais une validation juridique) :
  NON COUVERT            aucune fiche atteignable dans le domaine ;
  BLOQUÉ POUR VALIDATION des fiches existent mais aucune n'est citable telle quelle
                         (référence non vérifiée ou texte neutralisé) ;
  FONCTIONNEL            fiches atteignables, les 7 types de cas exécutés et réussis,
                         aucune lacune recensée ;
  PARTIEL                sinon (fiches et scénarios réussis, mais couverture limitée).
"""

import datetime
import json
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for chemin in (RACINE, os.path.join(RACINE, "tests")):
    if chemin not in sys.path:
        sys.path.insert(0, chemin)

import config  # noqa: E402
from core import catalogue, clarification, domaines_vision  # noqa: E402
from evaluation_24_domaines import evaluer  # noqa: E402
from scenarios_24_domaines import SCENARIOS, TYPES  # noqa: E402

SORTIE = os.path.join(RACINE, "reports", "inventaire_24_domaines.json")


def _documents():
    conn = sqlite3.connect("file:%s?mode=ro" % config.CHEMIN_DB, uri=True)
    conn.row_factory = sqlite3.Row
    lignes = conn.execute("""
        SELECT d.doc_id, d.type_texte, d.numero_texte, d.date_texte, d.titre, d.methode_extraction,
               d.articles_fiables, d.hote_officiel, d.url_source,
               (SELECT COUNT(*) FROM articles_corpus a WHERE a.doc_id = d.doc_id) AS articles,
               r.etat_verification
        FROM documents d LEFT JOIN references_juridiques r ON r.ref_id = d.ref_id""").fetchall()
    conn.close()
    return [dict(l) for l in lignes]


def _textes_du_domaine(registre_textes, documents):
    trouves = []
    for cle in registre_textes:
        for doc in documents:
            if (cle == "AU-SURETES" and doc["type_texte"] == "acte_uniforme") or doc["numero_texte"] == cle:
                trouves.append({
                    "numero": doc["numero_texte"] or "Acte uniforme OHADA (sûretés)",
                    "titre": doc["titre"], "date": doc["date_texte"], "type": doc["type_texte"],
                    "articles_indexes": doc["articles"], "articles_citables": doc["articles"] if doc["articles_fiables"] else 0,
                    "lecture": doc["methode_extraction"], "reference": doc["etat_verification"],
                    "source": doc["url_source"], "domaine_officiel": bool(doc["hote_officiel"]),
                })
    return trouves


def auditer():
    fiches = catalogue.charger()
    index = {f["id"]: f for f in fiches}
    guide = clarification.charger(fiches)
    registre = domaines_vision.charger(fiches)
    documents = _documents()
    domaines = []
    for d in registre:
        code = d["code"]
        fiches_dom = [index[i] for i in d["fiches"]]
        questions = [q for q in guide["questions"] if set(q["fiches"]) & set(d["fiches"])]
        scenarios = []
        for type_cas in TYPES:
            sc = SCENARIOS[code][type_cas]
            if "sans_objet" in sc:
                scenarios.append({"type": type_cas, "resultat": "SANS_OBJET", "raison": sc["sans_objet"]})
                continue
            r = evaluer(code, type_cas, sc, prefixe="AUDITOUTIL")
            scenarios.append({"type": type_cas, "recit": sc["recit"],
                              "resultat": "REUSSI" if r["ok"] else "ECHOUE",
                              "ecarts": r["ecarts"], "observe": r["observe"]})
        executes = [s for s in scenarios if s["resultat"] != "SANS_OBJET"]
        reussis = [s for s in executes if s["resultat"] == "REUSSI"]
        citables = [f for f in fiches_dom if f["etat_verification"] in ("VERIFIE", "PARTIELLEMENT_VERIFIE")]
        if not fiches_dom:
            statut = "NON COUVERT"
        elif not citables:
            statut = "BLOQUÉ POUR VALIDATION"
        elif len(executes) == len(TYPES) and len(reussis) == len(executes) and not d["lacunes"]:
            statut = "FONCTIONNEL"
        else:
            statut = "PARTIEL"
        domaines.append({
            "code": code, "libelle": d["libelle"], "cles_moteur": d["cles_moteur"],
            "textes": _textes_du_domaine(d["textes"], documents),
            "fiches": [{"id": f["id"], "titre": f["titre"], "article": f["article"],
                        "texte": f.get("numero_texte") or "Acte uniforme OHADA",
                        "reference": f["etat_verification"], "lecture_texte": f.get("origine_texte"),
                        "questions": [q["cle"] for q in questions if f["id"] in q["fiches"]]}
                       for f in fiches_dom],
            "questions": [{"cle": q["cle"], "question": q["question"]} for q in questions],
            "scenarios": scenarios,
            "scenarios_executes": len(executes), "scenarios_reussis": len(reussis),
            "scenarios_echoues": len(executes) - len(reussis),
            "scenarios_sans_objet": len(scenarios) - len(executes),
            "lacunes": d["lacunes"], "statut_technique": statut,
            "validation_juridique": "AUCUNE relecture humaine tracée (VERIFIE_MANUELLEMENT = 0)",
        })
    resume = {}
    for d in domaines:
        resume[d["statut_technique"]] = resume.get(d["statut_technique"], 0) + 1
    return {"genere_le": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
            "resume_statuts": resume,
            "scenarios": {"executes": sum(d["scenarios_executes"] for d in domaines),
                          "reussis": sum(d["scenarios_reussis"] for d in domaines),
                          "echoues": sum(d["scenarios_echoues"] for d in domaines),
                          "sans_objet": sum(d["scenarios_sans_objet"] for d in domaines)},
            "domaines": domaines}


def main():
    rapport = auditer()
    os.makedirs(os.path.dirname(SORTIE), exist_ok=True)
    with open(SORTIE, "w", encoding="utf-8") as flux:
        json.dump(rapport, flux, ensure_ascii=False, indent=1)
    for d in rapport["domaines"]:
        print("%2d %-50s %-22s fiches=%-2d textes=%-2d questions=%-2d scénarios %d/%d (sans objet %d)"
              % (d["code"], d["libelle"][:50], d["statut_technique"], len(d["fiches"]), len(d["textes"]),
                 len(d["questions"]), d["scenarios_reussis"], d["scenarios_executes"], d["scenarios_sans_objet"]))
    print("RÉSUMÉ", rapport["resume_statuts"], rapport["scenarios"])
    return 0 if rapport["scenarios"]["echoues"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
