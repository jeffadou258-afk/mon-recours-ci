# -*- coding: utf-8 -*-
"""État documenté des sources — généré depuis la base, jamais saisi à la main.

    python3 bin/rapport_sources.py

Écrit `KNOWLEDGE/ETAT_DES_SOURCES.md` et affiche un résumé. Chaque chiffre est
calculé sur le corpus réel ; aucune valeur n'est annoncée sans mesure.
"""

import json
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402
from core import catalogue, corpus, couverture  # noqa: E402

SORTIE = os.path.join(RACINE, "KNOWLEDGE", "ETAT_DES_SOURCES.md")


def _colonnes(conn, table):
    return [ligne[1] for ligne in conn.execute("PRAGMA table_info(%s)" % table)]


def _documents_non_citables(conn):
    """Articles des documents neutralisés, sans supposer le schéma."""
    colonnes = _colonnes(conn, "articles_corpus")
    # `article_id` est la clé primaire : ne pas la confondre avec la clé étrangère.
    fk = "doc_id" if "doc_id" in colonnes else next(
        (c for c in colonnes if c.endswith("_id") and c not in ("article_id", "id")), None)
    numero = "numero" if "numero" in colonnes else next(
        (c for c in colonnes if c.startswith("numero")), None)
    if fk is None or numero is None:
        return [], 0
    lignes = conn.execute(
        "SELECT d.ref_id, d.titre, d.numero_texte, COUNT(a.%s) "
        "FROM documents d LEFT JOIN articles_corpus a ON a.%s = d.doc_id "
        "WHERE d.articles_fiables = 0 GROUP BY d.ref_id ORDER BY d.ref_id"
        % (numero, fk)).fetchall()
    return lignes, sum(ligne[3] for ligne in lignes)


def _reserves_manifestes():
    """Réserves déjà consignées par les collectes (aucune n'est réécrite ici)."""
    trouvees = []
    base = os.path.join(RACINE, "KNOWLEDGE", "CORPUS")
    if not os.path.isdir(base):
        return trouvees
    for dossier in sorted(os.listdir(base)):
        chemin = os.path.join(base, dossier, "_sources.json")
        if not os.path.isfile(chemin):
            continue
        try:
            with open(chemin, encoding="utf-8") as flux:
                manifeste = json.load(flux)
        except (ValueError, OSError):
            continue
        for source in manifeste.get("sources", []):
            for reserve in source.get("reserves") or []:
                trouvees.append((dossier, source.get("cle"), reserve))
    return trouvees


def construire():
    integrite = corpus.verifier_integrite()
    origines = corpus.articles_par_origine()
    fiches = catalogue.charger()
    inventaire = couverture.inventaire()
    conn = sqlite3.connect(config.CHEMIN_DB)
    try:
        non_citables, total_non_citables = _documents_non_citables(conn)
    finally:
        conn.close()

    total_articles = sum(v["articles"] for v in origines.values())
    lignes = []
    ajouter = lignes.append

    ajouter("# État documenté des sources")
    ajouter("")
    ajouter("> Fichier **généré** par `python3 bin/rapport_sources.py`. Toute valeur ci-dessous")
    ajouter("> est calculée sur la base `KNOWLEDGE/corpus_juridique.sqlite3` au moment de")
    ajouter("> l'exécution. **Aucune validation juridique humaine n'a eu lieu.**")
    ajouter("")
    ajouter("## 1. Chiffres mesurés")
    ajouter("")
    ajouter("| Indicateur | Valeur |")
    ajouter("|---|---|")
    ajouter("| Documents | %d |" % integrite["nb_documents"])
    ajouter("| Articles indexés | %d |" % total_articles)
    ajouter("| Intégrité | `%s` |" % integrite["verdict"])
    ajouter("| Fiches cataloguées | %d |" % len(fiches))
    ajouter("| Documents non citables | %d |" % len(non_citables))
    ajouter("| Articles non citables (conservés pour audit) | %d |" % total_non_citables)
    ajouter("")
    ajouter("### Provenance du texte")
    ajouter("")
    ajouter("| Origine | Articles |")
    ajouter("|---|---|")
    for origine, valeurs in sorted(origines.items()):
        ajouter("| `%s` | %d |" % (origine, valeurs["articles"]))
    ajouter("")
    if not origines.get("VERIFIE_MANUELLEMENT", {}).get("articles"):
        ajouter("**Aucun article n'a été relu manuellement.** Tous les articles sont donc")
        ajouter("d'origine automatique (calque texte du PDF, ou OCR).")
        ajouter("")

    ajouter("## 2. Textes fiables et textes à vérifier")
    ajouter("")
    ajouter("« Fiable » signifie ici : **extrait d'un document officiel identifié par son")
    ajouter("empreinte SHA-256**. Cela ne signifie pas « relu par un juriste ».")
    ajouter("")
    ajouter("| Texte | Domaine | Origine | Articles | Qualité |")
    ajouter("|---|---|---|---|---|")
    conn = sqlite3.connect(config.CHEMIN_DB)
    try:
        comptes = dict(conn.execute(
            "SELECT ref_id, COUNT(*) FROM articles_corpus GROUP BY ref_id").fetchall())
        lignes_docs = conn.execute(
            "SELECT ref_id, numero_texte, titre, domaine, methode_extraction, "
            "note_ocr, articles_fiables FROM documents ORDER BY domaine, numero_texte"
        ).fetchall()
        for ref_id, numero, titre, domaine, methode, note_ocr, fiables in lignes_docs:
            compte = comptes.get(ref_id, 0)
            origine = "calque" if methode == "calque_texte" else (methode or "—")
            etat = "**non citable**" if fiables == 0 else "citable"
            note = (note_ocr or "").replace("\n", " ").replace("|", "/")
            if len(note) > 58:
                note = note[:55] + "…"
            ajouter("| %s — %s | `%s` | %s | %d | %s%s |"
                    % (numero or "sans numéro", titre[:52], domaine, origine, compte,
                       etat, " · " + note if note else ""))
    finally:
        conn.close()
    ajouter("")

    ajouter("## 3. Documents neutralisés (non citables)")
    ajouter("")
    if non_citables:
        ajouter("Motif : l'OCR d'un Journal officiel a **entremêlé plusieurs actes sur la")
        ajouter("même page** (l'article 1 citait une nomination et un autre décret). Les")
        ajouter("articles sont **conservés** pour l'audit mais exclus de la recherche et de")
        ajouter("la citation. Aucune méthode de correction suffisante n'est disponible.")
        ajouter("")
        ajouter("| Document | Numéro | Articles neutralisés |")
        ajouter("|---|---|---|")
        for ref_id, titre, numero, compte in non_citables:
            ajouter("| %s — %s | %s | %d |" % (ref_id, (titre or "")[:48], numero or "—", compte))
    else:
        ajouter("Aucun document neutralisé.")
    ajouter("")

    ajouter("## 4. Fiches cataloguées")
    ajouter("")
    ajouter("| Fiche | Domaine | Article | État | Origine | Recoupé |")
    ajouter("|---|---|---|---|---|---|")
    for fiche in fiches:
        ajouter("| %s | `%s` | %s art. %s | `%s` | `%s` | %s |"
                % (fiche["titre"], fiche["domaine"], fiche["numero_texte"] or "—",
                   fiche["article"], fiche["etat_verification"], fiche["origine_texte"],
                   "oui" if fiche["recoupe"] else "non"))
    ajouter("")

    ajouter("## 5. Domaines")
    ajouter("")
    ajouter("| Domaine | Statut technique | Complétude juridique |")
    ajouter("|---|---|---|")
    for ligne in inventaire["domaines"]:
        ajouter("| `%s` | `%s` | `%s` |"
                % (ligne["domaine"], ligne["statut"], ligne["completude_juridique"]))
    ajouter("")
    ajouter("Un statut `TERMINE_TECHNIQUEMENT` signifie : les textes sont intégrés et")
    ajouter("interrogeables. Il ne signifie **pas** que le domaine est couvert en droit.")
    ajouter("")

    ajouter("## 6. Textes manquants ou inaccessibles")
    ajouter("")
    ajouter("| Texte | Situation | Cause |")
    ajouter("|---|---|---|")
    ajouter("| Loi n° 2025-221 (contentieux du bail, expulsions) | **non intégrée** | "
            "aucun exemplaire sur `*.gouv.ci` ; `civlii.laws.africa` → 404 |")
    ajouter("| Journal officiel en ligne (`jorci.oneci.ci`) | inaccessible | HTTP 503 "
            "(maintenance) à chaque tentative |")
    ajouter("| `sgg.gouv.ci/jo.php` | inaccessible | mur d'authentification — non contourné |")
    ajouter("| `biblio.cndj.ci` | inaccessible | accès payant — non contourné |")
    ajouter("| Décret 2013-225 (copropriété) et modificatif 2014-26 | non intégré | "
            "aucun exemplaire officiel téléchargeable trouvé |")
    ajouter("| Lois 2019-868, décret 2024-850, ordonnance 2025-85 | non intégrés | "
            "non trouvés sur les sources officielles accessibles |")
    ajouter("")
    ajouter("Journal détaillé de la recherche : `KNOWLEDGE/05_LACUNE_LOI_2025_221.md`.")
    ajouter("")

    ajouter("## 7. Références ambiguës (non corrigées faute de source)")
    ajouter("")
    reserves = _reserves_manifestes()
    if reserves:
        for dossier, cle, reserve in reserves:
            ajouter("- **%s** (`%s`) : %s" % (dossier, cle, reserve))
    else:
        ajouter("Aucune réserve consignée dans les manifestes de collecte.")
    ajouter("")
    ajouter("Une référence ambiguë **n'est pas devinée** : elle reste signalée jusqu'à ce")
    ajouter("qu'un exemplaire du Journal officiel permette de trancher.")
    ajouter("")

    ajouter("## 8. Vérifications humaines requises")
    ajouter("")
    ajouter("1. Relire un échantillon d'articles par domaine — seul chemin vers")
    ajouter("   `VERIFIE_MANUELLEMENT`, et donc vers le statut `TERMINE_ET_VERIFIE` que le")
    ajouter("   code refuse aujourd'hui d'attribuer.")
    ajouter("2. Trancher la référence « 2013-711 » (nom de fichier « 791 »).")
    ajouter("3. Confirmer les 10 fiches du domaine logement, qui engagent la réponse.")
    ajouter("4. Décider du sort des articles neutralisés : re-OCR page par page, ou")
    ajouter("   exclusion définitive.")
    ajouter("5. Obtenir la loi 2025-221 auprès d'une source officielle (SGG ou CNDJ).")
    ajouter("")
    return "\n".join(lignes) + "\n", {
        "documents": integrite["nb_documents"], "articles": total_articles,
        "fiches": len(fiches), "documents_non_citables": len(non_citables),
        "articles_non_citables": total_non_citables, "reserves": len(reserves),
    }


def main():
    texte, resume = construire()
    with open(SORTIE, "w", encoding="utf-8") as flux:
        flux.write(texte)
    for cle, valeur in resume.items():
        print("  %-24s %s" % (cle, valeur))
    print("\nÉcrit : %s" % SORTIE)
    return 0


if __name__ == "__main__":
    sys.exit(main())
