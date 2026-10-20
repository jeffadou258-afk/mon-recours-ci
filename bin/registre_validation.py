# -*- coding: utf-8 -*-
"""Registre de validation juridique humaine — généré depuis la base et le catalogue.

    python3 bin/registre_validation.py                 # écrit KNOWLEDGE/registre_validation_humaine.md
    python3 bin/registre_validation.py --afficher      # affiche sans écrire

CE QUE CE DOCUMENT N'EST PAS
----------------------------
Ce n'est pas une validation. Le script ne change AUCUN statut : il lit
`references_juridiques.etat_verification`, `documents.articles_fiables` et le
catalogue, puis met en forme ce qui reste à contrôler par un juriste ivoirien.

Un texte n'est jamais promu `VERIFIE_MANUELLEMENT` par ce script. Le passage à
ce statut exige une relecture humaine réelle, tracée, article par article.
"""

import argparse
import collections
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402
from core import catalogue  # noqa: E402

SORTIE = os.path.join(RACINE, "KNOWLEDGE", "registre_validation_humaine.md")

PRIORITE = {"VERIFIE": 0, "PARTIELLEMENT_VERIFIE": 1, "A_VERIFIER": 2}


def collecter():
    fiches = catalogue.charger()
    par_reference = collections.defaultdict(list)
    for fiche in fiches:
        par_reference[str(fiche.get("numero_texte"))].append(fiche)

    connexion = sqlite3.connect(config.CHEMIN_DB)
    connexion.row_factory = sqlite3.Row
    try:
        references = [dict(l) for l in connexion.execute(
            "SELECT ref_id, numero_texte, titre_officiel, date_publication, source_url,"
            " empreinte_contenu, etat_verification"
            " FROM references_juridiques ORDER BY numero_texte").fetchall()]
        documents = collections.defaultdict(list)
        for ligne in connexion.execute(
                "SELECT d.ref_id, d.numero_texte, d.calque_texte, d.methode_extraction,"
                " d.articles_fiables, d.note_qualite, d.note_ocr,"
                " (SELECT COUNT(*) FROM articles_corpus a WHERE a.doc_id = d.doc_id) AS articles,"
                " (SELECT COUNT(*) FROM articles_corpus a WHERE a.doc_id = d.doc_id"
                "  AND a.origine_texte = 'OCR_AUTO') AS articles_ocr"
                " FROM documents d"):
            documents[ligne["ref_id"]].append(dict(ligne))
    finally:
        connexion.close()
    return references, documents, par_reference


def rediger(references, documents, par_reference):
    lignes = []
    ajouter = lignes.append
    total_fiches = sum(len(v) for v in par_reference.values())

    ajouter("# Registre de validation juridique humaine\n")
    ajouter("Document **généré** par `bin/registre_validation.py` depuis la base et le "
            "catalogue. Il ne modifie aucun statut.\n")
    ajouter("> **Aucune validation juridique humaine n'a été effectuée.** Tous les textes "
            "ci-dessous restent à faire relire par un juriste ivoirien compétent. "
            "Un statut technique (`VERIFIE`, `PARTIELLEMENT_VERIFIE`) décrit la qualité "
            "de l'extraction et de la provenance, **pas la justesse du droit**.\n")

    ajouter("## Synthèse\n")
    ajouter("| | Nombre |\n|---|---|")
    ajouter("| Références indexées | %d |" % len(references))
    ajouter("| dont `VERIFIE` (provenance établie) | %d |" %
            sum(1 for r in references if r["etat_verification"] == "VERIFIE"))
    ajouter("| dont `PARTIELLEMENT_VERIFIE` | %d |" %
            sum(1 for r in references if r["etat_verification"] == "PARTIELLEMENT_VERIFIE"))
    ajouter("| Fiches dépendant d'une référence | %d |" % total_fiches)
    ajouter("| Articles `VERIFIE_MANUELLEMENT` | 0 |\n")

    ajouter("## Ce qu'un juriste doit trancher, par ordre de priorité\n")
    ajouter("Priorité 1 = le plus de fiches servies au public ; priorité 3 = texte indexé "
            "sans fiche.\n")
    ajouter("| Prio | Référence | Texte | Statut | Art. | Fiches | Points à confirmer |")
    ajouter("|---|---|---|---|---|---|---|")

    classement = sorted(
        references,
        key=lambda r: (PRIORITE.get(r["etat_verification"], 9),
                       -len(par_reference.get(str(r["numero_texte"]), [])),
                       r["numero_texte"] or "zzz"))
    for reference in classement:
        cle_numero = str(reference["numero_texte"])
        numero = cle_numero if reference["numero_texte"] else "(sans numéro)"
        docs = documents.get(reference["ref_id"], [])
        articles = sum(d["articles"] for d in docs)
        fiches = par_reference.get(cle_numero, [])
        points = []
        if not reference["source_url"]:
            points.append("URL source absente")
        if any(d["articles_ocr"] for d in docs):
            points.append("%d art. issus d'OCR" % sum(d["articles_ocr"] for d in docs))
        if not any(d["calque_texte"] for d in docs):
            points.append("aucun calque de texte")
        if any(not d["articles_fiables"] for d in docs):
            points.append("un exemplaire neutralisé")
        if reference["etat_verification"] != "VERIFIE":
            points.append("provenance non établie")
        ajouter("| %d | %s | %s | `%s` | %d | %d | %s |" % (
            PRIORITE.get(reference["etat_verification"], 9) + 1, numero,
            (reference["titre_officiel"] or "")[:52].replace("|", "/"),
            reference["etat_verification"], articles, len(fiches),
            " ; ".join(points) or "—"))

    ajouter("\n## Questions juridiques ouvertes, déjà identifiées\n")
    ajouter("* **AUSCGIE-2014** : 32 articles écartés à l'OCR, 33 trous de numérotation, "
            "3 articles non localisés (art. 2, 103, 210) — "
            "`KNOWLEDGE/collecte/analyses/AUSCGIE_ARTICLES_A_VERIFIER.md`.")
    ajouter("* **AUSCGIE — portée par forme sociale** : les articles 17, 65, 108 et 274 ne "
            "distinguent pas SARL / SA / SAS ; chaque fiche le signale.")
    ajouter("* **Loi 2025-221** (contentieux du bail, exécution des expulsions) : introuvable "
            "en ligne, non intégrée — `KNOWLEDGE/05_LACUNE_LOI_2025_221.md`.")
    ajouter("* **179 articles neutralisés** (`donnees_personnelles_numerique`, JO OCR "
            "entremêlé) : conservés pour audit, jamais citables.")
    ajouter("* **Actualité** : la vigueur n'est établie qu'à la date de consultation "
            "(16–20/10/2026). Aucune recherche d'abrogation postérieure n'a été faite.\n")

    ajouter("## Ce que le produit ne peut pas encore affirmer\n")
    ajouter("1. Qu'une règle citée est **à jour** — aucune veille d'abrogation n'est branchée.")
    ajouter("2. Qu'une fiche est **juridiquement exacte** — elles ne sont pas relues.")
    ajouter("3. Qu'un **délai** ou une **procédure** est complet — le corpus ne couvre pas "
            "tous les textes d'application.")
    ajouter("4. Qu'une **adresse** ou un **contact administratif** est valide — le produit "
            "n'en invente aucune.\n")
    return "\n".join(lignes)


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("--afficher", action="store_true")
    arguments = analyseur.parse_args(argv)
    contenu = rediger(*collecter())
    if arguments.afficher:
        print(contenu)
        return 0
    with open(SORTIE, "w", encoding="utf-8") as flux:
        flux.write(contenu)
    print("Écrit : %s (%d caractères)" % (os.path.relpath(SORTIE, RACINE), len(contenu)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
