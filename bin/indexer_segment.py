# -*- coding: utf-8 -*-
"""Indexe UN texte de loi situé à l'intérieur d'un extrait de Journal officiel.

Cas réel : le PDF officiel de la loi n° 2019-571 (filiation), publié par
famille.gouv.ci, est un extrait du Journal officiel du 12 juillet 2019 qui
contient TROIS textes à la suite : la fin de la loi sur le mariage (articles
103 à 105), la loi sur la filiation (articles 1 à 30) et un décret sur les
cartes d'identité (articles 1 à 3). Indexé d'un bloc, le découpage mélange les
numéros (couverture 31 %) : la collecte l'a donc refusé, à juste titre.

Ce script n'assouplit AUCUNE règle. Il :
  1. vérifie l'empreinte SHA-256 du calque texte enregistré pour le document
     (refus si le fichier a changé depuis la collecte) ;
  2. ne garde que le segment compris entre deux marqueurs littéraux fournis
     (l'intitulé du texte et l'intitulé du texte suivant) ;
  3. répare deux artefacts de mise en page, sans toucher aux mots :
       - césure de fin de ligne par trait d'union conditionnel (U+00AD + saut
         de ligne) : le mot est recollé, comme dans le document imprimé ;
       - en-tête de page du Journal officiel inséré par l'extraction
         (saut de page puis « 260 JOURNAL OFFICIEL DE LA REPUBLIQUE… ») ;
  4. découpe avec `corpus.extraire_articles` et enregistre avec
     `corpus.enregistrer_articles`, qui REFUSE toute couverture < 85 % ;
  5. trace l'opération dans `documents.note_qualite`.

Il refuse les documents lus par OCR : leurs règles de recoupement sont
différentes et ce script ne doit pas servir à les contourner. L'état de
vérification de la référence n'est PAS modifié.

    python3 bin/indexer_segment.py --doc DOC-B722D1F51881 \
        --debut "LOI n° 2019-571 du 26 juin 2019 relative à la filiation." \
        --fin "DECRET n° 2019-590"            # simulation, rien n'est écrit
    ... --ecrire                              # enregistre
"""

import argparse
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

import config  # noqa: E402
from core import corpus  # noqa: E402

CESURE = re.compile("­[ \t]*\r?\n[ \t]*")
ENTETE_PAGE_JO = re.compile(
    r"\n*\x0c\s*\d{1,4}\s+JOURNAL OFFICIEL DE LA REPUBLIQUE DE COTE D ?[’']IVOIRE[^\n]*\n?"
)


class RefusIndexation(Exception):
    pass


def chemin_local(chemin_enregistre):
    """Les chemins en base sont absolus (machine de collecte) : on retrouve le
    fichier dans ce dépôt par sa partie relative à KNOWLEDGE/."""
    if chemin_enregistre and os.path.isfile(chemin_enregistre):
        return chemin_enregistre
    if chemin_enregistre and "KNOWLEDGE/" in chemin_enregistre:
        relatif = chemin_enregistre.split("KNOWLEDGE/", 1)[1]
        candidat = os.path.join(str(config.KNOWLEDGE_DIR), relatif)
        if os.path.isfile(candidat):
            return candidat
    raise RefusIndexation("calque texte introuvable : %s" % chemin_enregistre)


def nettoyer_mise_en_page(segment):
    sans_entetes, nb_entetes = ENTETE_PAGE_JO.subn("\n", segment)
    recolle, nb_cesures = CESURE.subn("", sans_entetes)
    return recolle, {"entetes_de_page_retires": nb_entetes, "cesures_recollees": nb_cesures}


def preparer(doc_id, debut, fin, chemin_db=None):
    document = corpus.obtenir_document(doc_id, chemin=chemin_db)
    if not document:
        raise RefusIndexation("document inconnu : %s" % doc_id)
    if document.get("methode_extraction") != "CALQUE_TEXTE" or not document.get("calque_texte"):
        raise RefusIndexation("seuls les calques texte sont acceptés (pas l'OCR) : %s"
                              % document.get("methode_extraction"))
    chemin = chemin_local(document.get("fichier_texte"))
    with open(chemin, encoding="utf-8") as flux:
        texte = flux.read()
    empreinte = corpus.empreinte_texte(texte)
    if document.get("sha256_texte") and empreinte != document["sha256_texte"]:
        raise RefusIndexation("empreinte du calque texte différente de la collecte : %s != %s"
                              % (empreinte, document["sha256_texte"]))
    if texte.count(debut) != 1:
        raise RefusIndexation("marqueur de début absent ou ambigu (%d occurrence(s))"
                              % texte.count(debut))
    i = texte.index(debut)
    j = texte.find(fin, i + len(debut)) if fin else len(texte)
    if j < 0:
        raise RefusIndexation("marqueur de fin introuvable après le début")
    segment, reparations = nettoyer_mise_en_page(texte[i:j])
    articles = corpus.extraire_articles(segment)
    taux, maximum = corpus.taux_couverture(articles)
    return {
        "document": document,
        "articles": articles,
        "rapport": {
            "doc_id": doc_id,
            "segment": {"debut": debut, "fin": fin, "position": [i, j]},
            "sha256_calque_verifie": empreinte,
            "reparations": reparations,
            "articles_detectes": len(articles),
            "article_max": maximum,
            "couverture": round(taux, 4),
        },
    }


def ecrire(preparation, chemin_db=None):
    document, articles, rapport = (preparation["document"], preparation["articles"],
                                   preparation["rapport"])
    resultat = corpus.enregistrer_articles(document["ref_id"], document["doc_id"], articles,
                                           origine_texte="CALQUE_TEXTE", chemin=chemin_db)
    note = ("segment indexé seul (%s → %s) : extrait du Journal officiel contenant "
            "plusieurs textes ; %d articles, couverture %.0f %% ; %d césure(s) de fin de "
            "ligne recollée(s), %d en-tête(s) de page retiré(s) ; empreinte du calque "
            "vérifiée avant indexation"
            % (rapport["segment"]["debut"], rapport["segment"]["fin"] or "fin du fichier",
               resultat["articles_indexes"], 100 * resultat["couverture"],
               rapport["reparations"]["cesures_recollees"],
               rapport["reparations"]["entetes_de_page_retires"]))
    with corpus.connexion(chemin_db) as conn:
        conn.execute("UPDATE documents SET note_qualite = ? WHERE doc_id = ?",
                     (note, document["doc_id"]))
    resultat["note_qualite"] = note
    return resultat


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("--doc", required=True)
    analyseur.add_argument("--debut", required=True)
    analyseur.add_argument("--fin", default="")
    analyseur.add_argument("--ecrire", action="store_true")
    arguments = analyseur.parse_args(argv)
    try:
        preparation = preparer(arguments.doc, arguments.debut, arguments.fin)
    except RefusIndexation as refus:
        print("REFUS : %s" % refus)
        return 2
    print(json.dumps(preparation["rapport"], ensure_ascii=False, indent=1))
    if not arguments.ecrire:
        print("Simulation : rien n'a été écrit (ajouter --ecrire).")
        return 0
    try:
        print(json.dumps(ecrire(preparation), ensure_ascii=False, indent=1))
    except ValueError as refus:
        print("REFUS : %s" % refus)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
