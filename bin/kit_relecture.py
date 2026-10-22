# -*- coding: utf-8 -*-
"""Kit de relecture juridique d'un lot de fiches — généré, lecture seule.

    python3 bin/kit_relecture.py --domaine logement_baux_foncier
    python3 bin/kit_relecture.py --domaine logement_baux_foncier --afficher

Écrit, pour le domaine demandé :

  KNOWLEDGE/relecture/<domaine>.md   le dossier à remettre au juriste : pour chaque
                                     fiche, l'article intégral tel qu'il est indexé,
                                     l'extrait cité, la lecture en français simple,
                                     les questions posées, la démarche proposée,
                                     la provenance, et une grille de décision ;
  KNOWLEDGE/relecture/<domaine>.csv  la même grille, une ligne par fiche, que le
                                     juriste remplit (tableur).

CE QUE CE SCRIPT NE FAIT PAS
----------------------------
Il ne valide rien et ne change AUCUN statut : ni `etat_verification`, ni
`origine_texte`, ni le statut `A_RELIRE_PAR_UN_JURISTE` des questions. Il lit la
base en lecture seule. L'enregistrement d'une relecture signée est une étape
distincte, qui n'existe pas encore.
"""

import argparse
import csv
import io
import json
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402

CATALOGUE = os.path.join(RACINE, "KNOWLEDGE", "catalogue.json")
QUESTIONS = os.path.join(RACINE, "KNOWLEDGE", "questions_clarification.json")
DOSSIER_SORTIE = os.path.join(RACINE, "KNOWLEDGE", "relecture")

COLONNES_DECISION = [
    "fiche", "texte", "article",
    "citation_conforme_au_texte_officiel (oui/non)",
    "texte_en_vigueur_a_la_date_de_relecture (oui/non/incertain)",
    "lecture_simple_exacte (oui/non)",
    "questions_pertinentes_et_sans_ajout (oui/non)",
    "demarche_correcte (oui/non)",
    "decision (VALIDEE / A_CORRIGER / A_RETIRER)",
    "corrections_proposees",
    "relu_par (nom, qualité)", "date_relecture",
]


def _base_lecture_seule():
    chemin = os.environ.get("MONRECOURS_CHEMIN_DB") or str(config.CHEMIN_DB)
    return sqlite3.connect("file:%s?mode=ro" % chemin, uri=True)


def _article(connexion, empreinte):
    ligne = connexion.execute(
        "SELECT a.texte, a.origine_texte, a.recoupe, r.titre_officiel, r.source_url, "
        "r.date_consultation, r.etat_verification "
        "FROM articles_corpus a JOIN references_juridiques r ON r.ref_id = a.ref_id "
        "WHERE a.sha256_article = ? ORDER BY a.origine_texte = 'CALQUE_TEXTE' DESC LIMIT 1",
        (empreinte.split(":", 1)[-1],),
    ).fetchone()
    if ligne is None:
        ligne = connexion.execute(
            "SELECT a.texte, a.origine_texte, a.recoupe, r.titre_officiel, r.source_url, "
            "r.date_consultation, r.etat_verification "
            "FROM articles_corpus a JOIN references_juridiques r ON r.ref_id = a.ref_id "
            "WHERE a.sha256_article = ? LIMIT 1",
            (empreinte,),
        ).fetchone()
    return ligne


def construire(domaine):
    with open(CATALOGUE, encoding="utf-8") as f:
        fiches = [x for x in json.load(f)["fiches"] if x.get("domaine") == domaine]
    with open(QUESTIONS, encoding="utf-8") as f:
        questions = json.load(f)["questions"]
    if not fiches:
        raise SystemExit("aucune fiche pour le domaine %r" % domaine)

    connexion = _base_lecture_seule()
    md = io.StringIO()
    md.write("# Relecture juridique — lot « %s »\n\n" % domaine)
    md.write("Document **généré** par `bin/kit_relecture.py` depuis la base et le catalogue. "
             "Il ne valide rien et ne modifie aucun statut.\n\n")
    md.write("**À la personne qui relit.** Chaque fiche ci-dessous est ce que le service montre "
             "au public : l'extrait cité, sa lecture en français simple, les questions posées et "
             "la démarche proposée. Merci de vérifier, pour chacune : (1) que l'extrait est "
             "conforme au texte officiel, (2) que le texte est en vigueur à la date de votre "
             "relecture, (3) que la lecture simple ne dit rien de plus ni de moins que l'article, "
             "(4) que les questions n'ajoutent aucune condition, (5) que la démarche est correcte. "
             "Les réponses se notent dans le fichier CSV joint, une ligne par fiche.\n\n"
             "Le corpus ne contient que les textes téléchargés en octobre 2026. Merci de signaler "
             "tout texte postérieur ou absent qui modifierait ces articles"
             + (" — en particulier la loi n° 2025-221 du 28 mars 2025 (contentieux des baux, "
                "exécution des expulsions), que le corpus ne contient pas" if domaine == "logement_baux_foncier" else "")
             + ". Les numéros de page ou coupures visibles dans « article intégral » viennent de "
             "l'extraction du PDF : les signaler s'ils faussent le sens.\n\n")
    md.write("| | |\n|---|---|\n| Fiches du lot | %d |\n| Statut actuel | toutes `A_RELIRE_PAR_UN_JURISTE` |\n\n"
             % len(fiches))

    lignes_csv = []
    for numero, fiche in enumerate(fiches, 1):
        art = _article(connexion, fiche.get("sha256_article", ""))
        md.write("---\n\n## %d. %s — `%s`\n\n" % (numero, fiche["titre"], fiche["id"]))
        md.write("**Texte** : %s, article %s  \n" % (art[3] if art else fiche["numero_texte"], fiche["article"]))
        if art:
            md.write("**Source** : %s (consultée le %s)  \n" % (art[4], art[5]))
            md.write("**Provenance du texte indexé** : `%s`%s · référence `%s`\n\n"
                     % (art[1], " (recoupé)" if art[2] else "", art[6]))
            md.write("**Article intégral, tel qu'indexé** :\n\n> %s\n\n" % art[0].replace("\n", "\n> "))
        else:
            md.write("\n**Article introuvable dans la base par son empreinte : à signaler.**\n\n")
        md.write("**Extrait cité au public** :\n\n> « %s »\n\n" % fiche["citation"])
        md.write("**Lecture en français simple** : %s\n\n" % fiche["lecture"])
        md.write("**Démarche proposée** : %s\n\n" % fiche.get("etape_plan", "—"))
        posees = [q for q in questions if fiche["id"] in q.get("fiches", [])]
        faits = fiche.get("faits_requis") or []
        if faits or posees:
            md.write("**Questions posées à la personne** :\n\n")
            for cle, texte in faits:
                md.write("- %s *(condition d'application)*\n" % texte)
            for q in posees:
                md.write("- %s — *pourquoi* : %s\n" % (q["question"], q.get("pourquoi", "")))
                for reponse, effet in (q.get("effets") or {}).items():
                    md.write("  - si « %s » : %s\n" % (reponse, effet))
            md.write("\n")
        md.write("**Décision** : ☐ VALIDÉE  ☐ À CORRIGER  ☐ À RETIRER — corrections : …………\n\n")
        lignes_csv.append([fiche["id"], fiche["numero_texte"], fiche["article"]] + [""] * (len(COLONNES_DECISION) - 3))
    connexion.close()

    sortie_csv = io.StringIO()
    ecrivain = csv.writer(sortie_csv, delimiter=";")
    ecrivain.writerow(COLONNES_DECISION)
    ecrivain.writerows(lignes_csv)
    return md.getvalue(), sortie_csv.getvalue()


def main():
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--domaine", required=True)
    analyseur.add_argument("--afficher", action="store_true", help="affiche sans écrire")
    args = analyseur.parse_args()
    md, tableau = construire(args.domaine)
    if args.afficher:
        print(md)
        return 0
    os.makedirs(DOSSIER_SORTIE, exist_ok=True)
    base = os.path.join(DOSSIER_SORTIE, args.domaine)
    with open(base + ".md", "w", encoding="utf-8") as f:
        f.write(md)
    # BOM UTF-8 : le tableur ouvre les accents correctement.
    with open(base + ".csv", "w", encoding="utf-8-sig", newline="") as f:
        f.write(tableau)
    print("écrit : %s.md et %s.csv" % (os.path.relpath(base, RACINE), os.path.relpath(base, RACINE)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
