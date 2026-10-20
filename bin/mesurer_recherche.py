# -*- coding: utf-8 -*-
"""Mesure ce que la recherche documentaire atteint réellement.

    python3 bin/mesurer_recherche.py                 # atteignabilité des textes sans fiche
    python3 bin/mesurer_recherche.py --questions F   # rappel/précision sur un jeu de questions
    python3 bin/mesurer_recherche.py --limite 5

DEUX MESURES DIFFÉRENTES, À NE PAS CONFONDRE
--------------------------------------------
1. **« inatteignable » (audit de cohérence)** = article dont le texte n'a AUCUNE fiche
   dans le catalogue. C'est une propriété de la couche CONVERSATIONNELLE (elle ne
   répond qu'à partir de fiches), pas de `corpus.chercher_articles`, qui peut très
   bien retrouver l'article.
2. **« retrouvable » (cet outil)** = pour une requête construite avec les mots de
   l'article lui-même, l'article ressort-il dans les N premiers résultats ?

La mesure 2 est une **auto-récupération** : elle prouve que l'index lexical contient
l'article et que le score le fait remonter sur son propre vocabulaire. Elle ne prouve
PAS qu'un citoyen le retrouverait avec ses mots — c'est ce que mesure `--questions`.

Aucune écriture : ni base, ni corpus, ni catalogue.
"""

import argparse
import json
import os
import re
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from core import catalogue, corpus  # noqa: E402

MOTIF_MOT = re.compile(r"[a-zà-ÿ]{5,}")


def _connexion():
    import sqlite3
    import config
    conn = sqlite3.connect(config.CHEMIN_DB)
    conn.row_factory = sqlite3.Row
    return conn


def references_couvertes(fiches):
    """ref_id que le catalogue sait réellement servir (résolution par le moteur)."""
    couvertes = set()
    for fiche in fiches:
        try:
            reference, article = catalogue.reference_citable(
                fiche["domaine"], fiche.get("numero_texte"), fiche["article"])
        except Exception:  # noqa: BLE001 — une fiche non résoluble ne couvre rien
            continue
        if article is not None and reference and reference.get("ref_id"):
            couvertes.add(reference["ref_id"])
    return couvertes


def _origine(conn, doc_id):
    ligne = conn.execute("SELECT origine_texte, COUNT(*) n FROM articles_corpus"
                         " WHERE doc_id = ? GROUP BY origine_texte"
                         " ORDER BY n DESC LIMIT 1", (doc_id,)).fetchone()
    return ligne["origine_texte"] if ligne else None


def _texte_pour_requete(conn, document, numero, texte):
    """Texte servant à construire la requête : le CALQUE s'il existe.

    Un article peut être indexé deux fois — calque propre et OCR imparfait.
    Interroger avec le texte OCR fabrique une requête contenant ses corruptions
    (« Lerropriation » pour « L'expropriation »), introuvable par construction.
    Ce n'est pas un défaut du corpus mais de la mesure : on interroge donc avec
    l'exemplaire propre quand il existe. Aucun score n'est modifié.
    """
    if (document.get("origine") or "") == "CALQUE_TEXTE":
        return texte
    numero_texte = document.get("numero_texte")
    if numero_texte:
        ligne = conn.execute(
            "SELECT a.texte FROM articles_corpus a JOIN documents d ON d.doc_id = a.doc_id"
            " WHERE d.numero_texte = ? AND a.numero = ? AND a.origine_texte = 'CALQUE_TEXTE'"
            " LIMIT 1", (numero_texte, str(numero))).fetchone()
        if ligne and ligne["texte"]:
            return ligne["texte"]
    return texte


def textes_sans_fiche(conn, fiches):
    """Documents citables, indexés, dont AUCUNE fiche ne couvre la référence."""
    couvertes = references_couvertes(fiches)
    lignes = conn.execute(
        "SELECT d.doc_id, d.ref_id, d.numero_texte, d.titre, d.domaine,"
        " (SELECT COUNT(*) FROM articles_corpus a WHERE a.doc_id = d.doc_id) AS articles"
        " FROM documents d WHERE d.articles_fiables = 1").fetchall()
    return [dict(l, origine=_origine(conn, l["doc_id"])) for l in lignes
            if l["articles"] and l["ref_id"] not in couvertes]


def requete_auto(texte, nombre=6):
    """Mots les plus longs de l'article : approximation de « ses mots-clés »."""
    mots, vus = [], set()
    for mot in MOTIF_MOT.findall(corpus.normaliser(texte or "")):
        if mot in corpus.MOTS_VIDES_RECHERCHE or mot in vus:
            continue
        vus.add(mot)
        mots.append(mot)
    return " ".join(sorted(mots, key=len, reverse=True)[:nombre])


def mesurer_atteignabilite(limite=5, bavard=True):
    conn = _connexion()
    fiches = catalogue.charger()
    sans_fiche = textes_sans_fiche(conn, fiches)
    total = sum(d["articles"] for d in sans_fiche)
    print("Textes sans fiche : %d | articles : %d" % (len(sans_fiche), total))

    resultats, debut = [], time.time()
    for document in sans_fiche:
        lignes = conn.execute(
            "SELECT numero, texte FROM articles_corpus WHERE doc_id = ?", (document["doc_id"],)).fetchall()
        trouves = 0
        trouves_ref = 0
        for ligne in lignes:
            requete = requete_auto(_texte_pour_requete(conn, document, ligne["numero"],
                                                       ligne["texte"]))
            if not requete:
                continue
            atteints = corpus.chercher_articles(requete, limite=limite)
            meme_ref = any(a.get("doc_id") == document["doc_id"]
                           and str(a.get("numero")) == str(ligne["numero"]) for a in atteints)
            meme_texte = any((a.get("numero_texte") or a.get("doc_id")) ==
                             (document["numero_texte"] or document["doc_id"])
                             and str(a.get("numero")) == str(ligne["numero"]) for a in atteints)
            if meme_texte:
                trouves += 1
            if meme_ref:
                trouves_ref += 1
        couverture = 100.0 * trouves / max(1, len(lignes))
        resultats.append({"numero_texte": document["numero_texte"], "titre": document["titre"],
                          "articles": len(lignes), "retrouves_top%d" % limite: trouves,
                          "refs_exactes": trouves_ref, "taux": round(couverture, 1)})
        if bavard:
            print("  %-14s %-40s %3d art. | %3d retrouves (%.0f %%) | %3d par ref exacte"
                  % (document["numero_texte"] or "—", (document["titre"] or "")[:40],
                     len(lignes), trouves, couverture, trouves_ref))
    retrouves = sum(r["retrouves_top%d" % limite] for r in resultats)
    refs = sum(r["refs_exactes"] for r in resultats)
    duree = time.time() - debut
    print("\nTOTAL : %d / %d articles retrouves (%.1f %%) en %.0f s"
          % (retrouves, total, 100.0 * retrouves / max(1, total), duree))
    print("        dont %d par la reference exacte (les autres : meme texte, autre exemplaire)"
          % refs)
    return {"textes": resultats, "articles": total, "retrouves": retrouves,
            "refs_exactes": refs, "limite": limite, "duree_s": round(duree, 1)}


def cle_article(article):
    """Identité d'un article pour comparer attendu et trouvé.

    Le numéro du texte d'abord : le même article peut exister en deux
    exemplaires (calque + OCR) et le dédoublonnage ne renvoie qu'un `ref_id`.
    """
    return (str(article.get("numero_texte") or article.get("ref_id")),
            str(article.get("numero")))


def mesurer_questions(chemin, limite=5):
    """Rappel@k, précision au rang 1 et MRR sur un jeu de questions documenté."""
    with open(chemin, encoding="utf-8") as flux:
        jeu = json.load(flux)
    details, rangs = [], []
    for cas in jeu["questions"]:
        attendus = {cle_article(a) for a in cas["attendus"]}
        resultats = corpus.chercher_articles(cas["question"], limite=limite)
        vus = [cle_article(a) for a in resultats]
        rang = next((i + 1 for i, v in enumerate(vus) if v in attendus), None)
        rangs.append(rang)
        details.append({"question": cas["question"], "attendu": cas["attendus"],
                        "rang": rang, "top": [(a.get("numero_texte"), a.get("numero"), a.get("score"))
                                              for a in resultats]})
        print("  %-58s -> %s" % (cas["question"][:58],
                                 ("rang %d" % rang) if rang else "ABSENT du top %d" % limite))
    trouves = [r for r in rangs if r]
    mrr = sum(1.0 / r for r in trouves) / max(1, len(rangs))
    print("\nRappel@%d : %d/%d (%.0f %%) | rang 1 : %d | MRR : %.2f"
          % (limite, len(trouves), len(rangs), 100.0 * len(trouves) / max(1, len(rangs)),
             sum(1 for r in rangs if r == 1), mrr))
    return {"rappel": len(trouves), "total": len(rangs), "mrr": round(mrr, 3),
            "limite": limite, "details": details}


ABSTENTIONS_ATTENDUES = [
    ("de la", "logement_baux_foncier", "aucun mot significatif"),
    ("le les des", None, "aucun mot significatif"),
    ("xyzabc", None, "vocabulaire absent du corpus"),
    ("quorum cooperative", "logement_baux_foncier", "hors du périmètre demandé"),
]


def mesurer_abstentions():
    """L'abstention est-elle prononcée quand elle doit l'être ?"""
    from core import service
    correctes, details = 0, []
    for question, domaine, motif in ABSTENTIONS_ATTENDUES:
        reponse = service.rechercher(question, domaine=domaine)
        abstenu = bool(reponse.get("ok") and reponse["data"]["abstention"])
        correctes += 1 if abstenu else 0
        details.append({"question": question, "domaine": domaine, "motif": motif,
                        "abstention": abstenu,
                        "resultats": len(reponse["data"]["resultats"]) if reponse.get("ok") else None})
    return {"correctes": correctes, "total": len(ABSTENTIONS_ATTENDUES), "details": details}


def mesurer_citations(questions, maximum=15):
    """Une citation exacte est acceptée ; la même citation altérée est refusée."""
    testees = valides = refusees = 0
    details = []
    for cas in questions[:maximum]:
        resultats = corpus.chercher_articles(cas["question"], limite=1)
        if not resultats:
            continue
        article = resultats[0]
        corps = corpus.obtenir_article_par_reference(article["ref_id"], article["numero"])
        if not corps:
            continue
        citation = " ".join((corps["texte"] or "").split())[:60]
        if len(citation) < 20:
            continue
        testees += 1
        acceptee, _ = corpus.verifier_citation_article(article["ref_id"], article["numero"],
                                                       citation)
        valides += 1 if acceptee else 0
        refusee, motif = corpus.verifier_citation_article(
            article["ref_id"], article["numero"], citation + " et le ciel est vert")
        refusees += 1 if not refusee else 0
        details.append({"article": "%s art.%s" % (article.get("numero_texte"),
                                                  article.get("numero")),
                        "acceptee": bool(acceptee), "alteree_refusee": bool(not refusee),
                        "motif": motif.get("raison") if motif else None})
    return {"testees": testees, "citations_valides": valides,
            "citations_alterees_refusees": refusees, "details": details}


def rapport_complet(limite=5, chemin_questions=None):
    """Les quatre mesures de qualité, dans un seul run reproductible."""
    rapport = {}
    print("=== 1. RAPPEL DOCUMENTAIRE (textes sans fiche) ===")
    rapport["rappel_documentaire"] = mesurer_atteignabilite(limite, bavard=False)
    d = rapport["rappel_documentaire"]
    print("  %d / %d articles retrouvés (%.1f %%), dont %d par référence exacte"
          % (d["retrouves"], d["articles"], 100.0 * d["retrouves"] / max(1, d["articles"]),
             d.get("refs_exactes", 0)))
    if chemin_questions and os.path.isfile(chemin_questions):
        print("\n=== 2. PERTINENCE SUR QUESTIONS (déclencheurs du catalogue) ===")
        rapport["questions"] = mesurer_questions(chemin_questions, limite)
        q = rapport["questions"]
        print("  rappel@%d : %d/%d | rang 1 : %d | MRR %.2f"
              % (limite, q["rappel"], q["total"],
                 sum(1 for x in q["details"] if x["rang"] == 1), q["mrr"]))
    print("\n=== 3. ABSTENTIONS ===")
    rapport["abstentions"] = mesurer_abstentions()
    a = rapport["abstentions"]
    for ligne in a["details"]:
        print("  %-24s %-24s abstention=%-5s (%s)"
              % (ligne["question"][:24], str(ligne["domaine"])[:24],
                 ligne["abstention"], ligne["motif"]))
    print("  correctes : %d/%d" % (a["correctes"], a["total"]))
    if chemin_questions and os.path.isfile(chemin_questions):
        print("\n=== 4. CITATIONS ===")
        with open(chemin_questions, encoding="utf-8") as flux:
            questions = json.load(flux)["questions"]
        rapport["citations"] = mesurer_citations(questions)
        c = rapport["citations"]
        print("  %d testées | %d exactes acceptées | %d altérées refusées"
              % (c["testees"], c["citations_valides"], c["citations_alterees_refusees"]))
    return rapport


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("--limite", type=int, default=5)
    analyseur.add_argument("--questions", help="fichier JSON de questions attendues")
    analyseur.add_argument("--rapport", action="store_true",
                           help="les quatre mesures de qualité dans un seul run")
    analyseur.add_argument("--json", help="écrit le résultat dans ce fichier")
    arguments = analyseur.parse_args(argv)
    if arguments.rapport:
        chemin = arguments.questions or os.path.join(RACINE, "KNOWLEDGE", "qualite",
                                                     "questions_recherche.json")
        resultat = rapport_complet(arguments.limite, chemin)
    elif arguments.questions:
        resultat = mesurer_questions(arguments.questions, arguments.limite)
    else:
        resultat = mesurer_atteignabilite(arguments.limite)
    if arguments.json:
        with open(arguments.json, "w", encoding="utf-8") as flux:
            json.dump(resultat, flux, ensure_ascii=False, indent=1)
        print("Écrit : %s" % arguments.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
