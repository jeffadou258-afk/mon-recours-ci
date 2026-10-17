# -*- coding: utf-8 -*-
"""Ajoute (ou met à jour) des fiches au catalogue à partir d'un fichier de définitions.

La citation de chaque fiche n'est JAMAIS retapée : elle est extraite du texte
indexé de l'article, entre deux bornes littérales (`citation_debut` et
`citation_fin`, incluses), espaces normalisés. Puis le catalogue complet est
rechargé par `core.catalogue.charger()`, qui revalide TOUTES les fiches contre
la base (référence, article citable, citation littérale, énoncé soutenu). Si
la validation échoue, `KNOWLEDGE/catalogue.json` n'est pas modifié.

    python3 bin/ajouter_fiches.py KNOWLEDGE/fiches_sources/famille.json          # simulation
    python3 bin/ajouter_fiches.py KNOWLEDGE/fiches_sources/famille.json --ecrire
"""

import argparse
import datetime
import json
import os
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

from core import base, catalogue, corpus  # noqa: E402


class FicheRefusee(Exception):
    pass


def reference(domaine, numero_texte, chemin_db=None):
    for candidat in base.lister_references(domaine=domaine, chemin=chemin_db):
        if (candidat.get("numero_texte") or None) == (numero_texte or None):
            return candidat
    raise FicheRefusee("référence %s absente du domaine %s" % (numero_texte, domaine))


def extraire_citation(texte_article, debut, fin):
    texte = " ".join(texte_article.split())
    debut, fin = " ".join(debut.split()), " ".join(fin.split())
    if texte.count(debut) != 1:
        raise FicheRefusee("borne de début absente ou ambiguë : %r" % debut)
    i = texte.index(debut)
    j = texte.find(fin, i)
    if j < 0:
        raise FicheRefusee("borne de fin absente après le début : %r" % fin)
    return texte[i:j + len(fin)]


def construire(definitions, chemin_db=None):
    ref = reference(definitions["domaine"], definitions.get("numero_texte"), chemin_db)
    fiches = []
    for d in definitions["fiches"]:
        article = corpus.obtenir_article_par_reference(ref["ref_id"], d["article"], chemin=chemin_db)
        if article is None:
            raise FicheRefusee("%s : article %s absent ou non citable" % (d["id"], d["article"]))
        fiches.append({
            "id": d["id"],
            "domaine": definitions["domaine"],
            "numero_texte": definitions.get("numero_texte"),
            "article": d["article"],
            "titre": d["titre"],
            "declencheurs": d["declencheurs"],
            "citation": extraire_citation(article["texte"], d["citation_debut"], d["citation_fin"]),
            "lecture": d["lecture"],
            "faits_requis": d.get("faits_requis", []),
            "etape_plan": d.get("etape_plan"),
        })
    return fiches


def fusionner(catalogue_brut, nouvelles):
    ids = {f["id"] for f in nouvelles}
    conservees = [f for f in catalogue_brut.get("fiches", []) if f["id"] not in ids]
    resultat = dict(catalogue_brut)
    resultat["fiches"] = conservees + nouvelles
    resultat["genere_le"] = datetime.date.today().isoformat()
    return resultat


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("definitions")
    analyseur.add_argument("--ecrire", action="store_true")
    arguments = analyseur.parse_args(argv)
    with open(arguments.definitions, encoding="utf-8") as flux:
        definitions = json.load(flux)
    try:
        nouvelles = construire(definitions)
    except FicheRefusee as refus:
        print("REFUS : %s" % refus)
        return 2
    with open(catalogue.CHEMIN_CATALOGUE, encoding="utf-8") as flux:
        actuel = json.load(flux)
    fusionne = fusionner(actuel, nouvelles)

    # Validation complète AVANT écriture, sur une copie temporaire.
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as tmp:
        json.dump(fusionne, tmp, ensure_ascii=False, indent=1)
        chemin_tmp = tmp.name
    try:
        valides = catalogue.charger(chemin=chemin_tmp)
    except catalogue.CatalogueInvalide as refus:
        print("REFUS (validation du catalogue) : %s" % refus)
        return 2
    finally:
        os.unlink(chemin_tmp)

    for f in nouvelles:
        print("%-10s art. %-4s %s\n           « %s »" % (f["id"], f["article"], f["titre"], f["citation"]))
    print("Catalogue validé : %d fiches au total." % len(valides))
    if not arguments.ecrire:
        print("Simulation : catalogue.json non modifié (ajouter --ecrire).")
        return 0
    with open(catalogue.CHEMIN_CATALOGUE, "w", encoding="utf-8") as flux:
        json.dump(fusionne, flux, ensure_ascii=False, indent=1)
        flux.write("\n")
    print("Écrit : %s" % catalogue.CHEMIN_CATALOGUE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
