#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige la provenance des documents du corpus dont le « calque texte » est un OCR.

Constat (collecte d'octobre 2026) : certains PDF officiels déjà indexés comme
`CALQUE_TEXTE` sont des scans du Journal officiel dont le texte a été produit par
un logiciel de reconnaissance (ABBYY FineReader, Acrobat Paper Capture). Leur
texte n'est donc pas une lecture du document mais un OCR, et doit être présenté
comme tel : c'est ce qui déclenche, dans le moteur, la déclaration d'incertitude.

Ce script ne SUPPRIME rien et ne modifie aucun texte : il passe `origine_texte` à
`OCR_AUTO` (sans confiance mesurée, sans recoupement) et `methode_extraction` à
`OCR_EDITEUR`, avec une note. Il ne s'applique qu'aux documents dont le PDF
rapatrié par la collecte a EXACTEMENT la même empreinte que celui du corpus.

    python3 bin/corriger_provenance_ocr.py            # simulation
    python3 bin/corriger_provenance_ocr.py --ecrire
"""

import argparse
import json
import os
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "bin"))

from core import corpus  # noqa: E402
import integrer_collecte  # noqa: E402


def candidats():
    inventaire = integrer_collecte.lire_json(integrer_collecte.INVENTAIRE)
    par_sha = {d["sha256"]: d for d in inventaire["documents"] if d.get("indices_ocr_editeur")}
    with corpus.connexion() as conn:
        lignes = conn.execute(
            "SELECT doc_id, numero_texte, titre, sha256, methode_extraction,"
            " (SELECT COUNT(*) FROM articles_corpus a WHERE a.doc_id = d.doc_id"
            "   AND a.origine_texte = 'CALQUE_TEXTE') FROM documents d").fetchall()
    for doc_id, numero, titre, sha, methode, n in lignes:
        if sha in par_sha and methode == "CALQUE_TEXTE":
            yield {"doc_id": doc_id, "numero_texte": numero, "titre": titre, "articles_calque": n,
                   "indices": par_sha[sha]["indices_ocr_editeur"], "cle_collecte": par_sha[sha]["cle"]}


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--ecrire", action="store_true")
    arguments = analyseur.parse_args(argv)
    liste = list(candidats())
    for c in liste:
        print(json.dumps(c, ensure_ascii=False))
    if not arguments.ecrire:
        print("Simulation : %d document(s) à corriger." % len(liste))
        return 0
    with corpus.connexion() as conn:
        for c in liste:
            note = ("provenance corrigée le %s : le calque texte de ce PDF est un OCR (%s), constaté sur "
                    "le même fichier (KNOWLEDGE/collecte/resultats/%s.json)"
                    % (corpus.horodatage()[:10], ", ".join(c["indices"]), c["cle_collecte"]))
            conn.execute("UPDATE articles_corpus SET origine_texte = 'OCR_AUTO', confiance_ocr = NULL,"
                         " recoupe = 0 WHERE doc_id = ? AND origine_texte = 'CALQUE_TEXTE'", (c["doc_id"],))
            conn.execute("UPDATE documents SET methode_extraction = 'OCR_EDITEUR',"
                         " note_ocr = ? WHERE doc_id = ?", (note, c["doc_id"]))
    print("Corrigé : %d document(s)." % len(liste))
    return 0


if __name__ == "__main__":
    sys.exit(main())
