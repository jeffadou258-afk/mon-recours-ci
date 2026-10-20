#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Génère docs/RESSOURCES_JURIDIQUES_ET_TECHNIQUES.md depuis les inventaires RÉELS.

Sources lues (aucun chiffre saisi à la main) :
  * KNOWLEDGE/collecte/inventaire_ressources.json  (bin/integrer_collecte.py controler)
  * KNOWLEDGE/collecte/recoupements.json           (bin/integrer_collecte.py recouper)
  * KNOWLEDGE/corpus_juridique.sqlite3             (documents et articles indexés)
  * KNOWLEDGE/domaines_24.json                     (registre des 24 domaines)
"""

import collections
import json
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COLLECTE = os.path.join(RACINE, "KNOWLEDGE", "collecte")
SORTIE = os.path.join(RACINE, "docs", "RESSOURCES_JURIDIQUES_ET_TECHNIQUES.md")


def lire(chemin, defaut=None):
    try:
        with open(chemin, encoding="utf-8") as flux:
            return json.load(flux)
    except FileNotFoundError:
        return defaut


def corpus_par_domaine():
    sys.path.insert(0, RACINE)
    import config
    conn = sqlite3.connect(str(config.CHEMIN_DB))
    lignes = conn.execute(
        "SELECT d.domaine, d.numero_texte, d.titre, d.methode_extraction, d.articles_fiables,"
        " d.url_source, (SELECT COUNT(*) FROM articles_corpus a WHERE a.doc_id = d.doc_id),"
        " (SELECT etat_verification FROM references_juridiques r WHERE r.ref_id = d.ref_id)"
        " FROM documents d ORDER BY d.domaine, d.numero_texte").fetchall()
    conn.close()
    return lignes


def main():
    inv = lire(os.path.join(COLLECTE, "inventaire_ressources.json"))
    if not inv:
        raise SystemExit("inventaire absent : lancer bin/integrer_collecte.py controler")
    rec = lire(os.path.join(COLLECTE, "recoupements.json"), {"comparaisons": []})
    domaines = {d["code"]: d["libelle"] for d in lire(os.path.join(RACINE, "KNOWLEDGE", "domaines_24.json"))["domaines"]}
    t = inv["totaux"]
    o = []
    w = o.append
    w("# Ressources juridiques et techniques — Mon Recours CI\n")
    w("Document **généré** par `bin/rapport_ressources.py` le %s à partir de "
      "`KNOWLEDGE/collecte/inventaire_ressources.json`, `recoupements.json` et de la base du corpus. "
      "Ne pas modifier à la main : relancer le script.\n" % inv["genere_le"][:10])
    w("> Télécharger un texte ne l'authentifie pas et ne prouve pas qu'il est en vigueur. "
      "« Officiel » signifie ici : publié sur un hôte officiel (registre du projet ou *.gouv.ci, ohada.org). "
      "Aucune ligne de ce document ne vaut validation juridique.\n")

    w("## 1. Chiffres de la collecte\n")
    w("| Mesure | Valeur |\n|---|---|")
    for libelle, valeur in (("Entrées du manifeste", t["entrees_manifeste"]),
                            ("Documents téléchargés", t["documents_telecharges"]),
                            ("PDF rapatriés et empreinte vérifiée", t["pdf_rapatries_et_verifies"]),
                            ("Pages de découverte lues", t["pages_de_decouverte_lues"]),
                            ("Échecs (HTTP, réseau, non-PDF)", t["echecs"]),
                            ("Pas encore collectés", t["non_encore_collectes"])):
        w("| %s | %s |" % (libelle, valeur))
    for cle, titre in (("par_statut_controle", "Statut de contrôle"), ("par_categorie", "Catégorie de source"),
                       ("par_methode_extraction", "Méthode d'extraction")):
        w("| %s | %s |" % (titre, ", ".join("%s : %d" % kv for kv in t[cle].items()) or "—"))
    w("")

    w("## 2. Documents téléchargés\n")
    w("| Clé | Texte | Catégorie | Pages | Extraction | Articles (couverture) | Contrôle | Motifs / avertissements |")
    w("|---|---|---|---|---|---|---|---|")
    for d in inv["documents"]:
        motifs = "; ".join(d["motifs_quarantaine"] + d["avertissements"]) or "—"
        w("| `%s` | %s — %s | %s | %s | %s%s | %s (%.0f %%) | **%s** | %s |" % (
            d["cle"], d["numero_texte"] or "?", (d["titre"] or "")[:90], d["categorie_source"], d["pages"],
            d["methode_extraction"], (" conf. %s" % d["confiance_ocr_moyenne"]) if d["confiance_ocr_moyenne"] else "",
            d["articles_detectes"], 100 * d["couverture_articles"], d["statut_controle"], motifs.replace("|", "/")))
    w("\nProvenance complète (URL, URL finale, date de récupération, SHA-256, taille, version PDF) : "
      "`KNOWLEDGE/collecte/inventaire_ressources.json` et `KNOWLEDGE/collecte/resultats/<clé>.json`. "
      "PDF bruts : branche `corpus/archives-pdf` (fichier `SHA256SUMS`).\n")

    w("## 3. Recoupements entre lectures d'un même texte\n")
    if rec["comparaisons"]:
        w("| Texte | Lecture A | Lecture B | Articles communs | Similarité moyenne | Divergents (< 0,80) |")
        w("|---|---|---|---|---|---|")
        for c in rec["comparaisons"]:
            s = c["statistiques"] or {}
            w("| %s | `%s` | `%s` | %d | %s | %d |" % (c["numero_texte"], c["lecture_a"], c["lecture_b"],
                                                       c["articles_communs"], s.get("similarite_moyenne", "—"),
                                                       len(c["articles_divergents"])))
        w("\nUne divergence est soit une erreur de lecture, soit une **modification du texte** "
          "(une version consolidée diffère de la version d'origine) : elle se tranche à la lecture.\n")
    else:
        w("Aucun recoupement possible pour l'instant.\n")

    w("## 4. Corpus de référence (base du moteur)\n")
    w("| Domaine du moteur | Texte | Extraction | Articles indexés | Citables | État de la référence |")
    w("|---|---|---|---|---|---|")
    for dom, num, titre, methode, fiables, url, nb, etat in corpus_par_domaine():
        w("| %s | %s — %s | %s | %d | %s | %s |" % (dom, num or "?", titre[:70], methode, nb,
                                                    "oui" if fiables else "non", etat or "—"))
    w("")

    w("## 5. Échecs et sources inaccessibles\n")
    w("| Clé | Catégorie | Statut | HTTP | Détail |\n|---|---|---|---|---|")
    for e in inv["echecs"]:
        w("| `%s` | %s | %s | %s | %s |" % (e["cle"], e.get("categorie_source"), e["statut"], e.get("http") or "—",
                                          (e.get("erreur") or e.get("debut") or "")[:80].replace("|", "/")))
    w("")

    w("## 6. Domaines concernés par les documents téléchargés\n")
    par_domaine = collections.defaultdict(list)
    for d in inv["documents"]:
        for code in d["domaines"]:
            par_domaine[code].append("%s (%s)" % (d["cle"], d["statut_controle"]))
    w("| Domaine | Documents |\n|---|---|")
    for code in sorted(domaines):
        w("| %d. %s | %s |" % (code, domaines[code], "<br>".join(par_domaine.get(code, [])) or "aucun"))
    w("")

    w("## 7. Outils utilisés\n")
    outils = inv.get("outils_collecte") or {}
    w("| Outil | Version | Où |\n|---|---|---|")
    for nom in ("pdftotext", "qpdf", "tesseract"):
        w("| %s | %s | runner GitHub Actions (paquets Ubuntu) |" % (nom, outils.get(nom) or "?"))
    w("| Langues tesseract | %s | runner |" % ", ".join(l for l in (outils.get("tesseract_langues") or [])
                                                   if l in ("fra", "eng", "osd")))
    w("| Python (bibliothèque standard), sqlite3, difflib | — | runner et poste de travail |")
    w("\nAucune dépendance Python ajoutée au projet. Aucune clé, aucun service payant, aucun fournisseur d'IA.\n")
    with open(SORTIE, "w", encoding="utf-8") as flux:
        flux.write("\n".join(o) + "\n")
    print("écrit : %s (%d lignes)" % (os.path.relpath(SORTIE, RACINE), len(o)))


if __name__ == "__main__":
    sys.exit(main())
