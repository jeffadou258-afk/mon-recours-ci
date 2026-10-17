# -*- coding: utf-8 -*-
"""Complète jusqu'à la fin de la phrase les citations tronquées du catalogue.

Les premières fiches portent une citation coupée à 180 caractères, parfois au
milieu d'un mot (« … en fin de cont »). Ce script ne réécrit rien à la main :
pour chaque fiche, il retrouve la citation dans le texte indexé de l'article
(espaces normalisés) et l'étend jusqu'à la première fin de phrase qui suit
(point, point-virgule final d'énumération exclu), sans dépasser `--max`
caractères. Le catalogue complet est revalidé par `core.catalogue.charger()`
avant écriture ; en cas d'échec, rien n'est écrit.

    python3 bin/completer_citations.py            # simulation
    python3 bin/completer_citations.py --ecrire
"""

import argparse
import json
import os
import re
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

from core import catalogue, corpus  # noqa: E402

FIN_DE_PHRASE = re.compile(r"[.!?](?=\s|$)")


def completer(citation, texte_article, maximum):
    texte = " ".join(texte_article.split())
    debut = " ".join(citation.split())
    if re.search(r"[.!?»]\s*$", debut):
        return citation, "déjà complète"
    i = texte.find(debut)
    if i < 0:
        return citation, "citation introuvable telle quelle : inchangée"
    fin = FIN_DE_PHRASE.search(texte, i + len(debut))
    if not fin:
        etendue = texte[i:]
    else:
        etendue = texte[i:fin.end()]
    if len(etendue) > maximum:
        return citation, "phrase trop longue (%d car.) : inchangée" % len(etendue)
    return etendue, "complétée"


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("--ecrire", action="store_true")
    analyseur.add_argument("--max", type=int, default=700)
    arguments = analyseur.parse_args(argv)

    fiches_valides = {f["id"]: f for f in catalogue.charger()}
    with open(catalogue.CHEMIN_CATALOGUE, encoding="utf-8") as flux:
        brut = json.load(flux)
    modifiees = 0
    for fiche in brut["fiches"]:
        valide = fiches_valides[fiche["id"]]
        article = corpus.obtenir_article_par_reference(valide["ref_id"], fiche["article"])
        nouvelle, etat = completer(fiche["citation"], article["texte"], arguments.max)
        print("%-12s %s" % (fiche["id"], etat))
        if nouvelle != fiche["citation"]:
            fiche["citation"] = nouvelle
            modifiees += 1
            print("             « %s »" % nouvelle)

    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(brut, tmp, ensure_ascii=False, indent=1)
        chemin_tmp = tmp.name
    try:
        catalogue.charger(chemin=chemin_tmp)
    except catalogue.CatalogueInvalide as refus:
        print("REFUS (validation du catalogue) : %s" % refus)
        return 2
    finally:
        os.unlink(chemin_tmp)
    print("%d citation(s) complétée(s) ; catalogue revalidé." % modifiees)
    if not arguments.ecrire:
        print("Simulation : catalogue.json non modifié (ajouter --ecrire).")
        return 0
    with open(catalogue.CHEMIN_CATALOGUE, "w", encoding="utf-8") as flux:
        json.dump(brut, flux, ensure_ascii=False, indent=1)
        flux.write("\n")
    print("Écrit : %s" % catalogue.CHEMIN_CATALOGUE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
