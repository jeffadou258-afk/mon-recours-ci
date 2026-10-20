# -*- coding: utf-8 -*-
"""Lot de recherche prioritaire — plan du Research Agent, dérivé des lacunes mesurées.

    python3 bin/recherche_priorites.py            # écrit KNOWLEDGE/RECHERCHE_PRIORITES.md
    python3 bin/recherche_priorites.py --afficher

CE QUE FAIT CE SCRIPT, ET CE QU'IL NE FAIT PAS
----------------------------------------------
Il LIT `KNOWLEDGE/domaines_24.json` (lacunes déclarées), le registre de validation
et la base, puis ordonne le travail de recherche. Il n'ouvre aucune connexion
réseau, n'écrit pas dans la base, ne télécharge rien, ne promeut aucun statut.

L'exécution appartient aux outils existants, qui portent déjà leurs garde-fous :
  * `bin/collecte_distante.py` — télécharge, mesure, extrait ; n'écrit QUE des constats
    (aucune écriture en base, aucune promotion de référence) ;
  * `bin/integrer_collecte.py` — intègre en local, avec les contrôles de couverture,
    de contaminants et d'hôte officiel.
Ce script ne remplace ni l'un ni l'autre : il dit quoi chercher, dans quel ordre,
et pourquoi. Un texte candidat reste `A_VERIFIER` jusqu'à intégration contrôlée.
"""

import argparse
import json
import os
import sqlite3
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

import config  # noqa: E402

SORTIE = os.path.join(RACINE, "KNOWLEDGE", "RECHERCHE_PRIORITES.md")
DOMAINES = os.path.join(RACINE, "KNOWLEDGE", "domaines_24.json")


def _references_par_etat():
    connexion = sqlite3.connect(config.CHEMIN_DB)
    try:
        return {ligne[0]: ligne[1] for ligne in connexion.execute(
            "SELECT numero_texte, etat_verification FROM references_juridiques")}
    finally:
        connexion.close()


def classer():
    with open(DOMAINES, encoding="utf-8") as flux:
        domaines = json.load(flux)["domaines"]
    references = _references_par_etat()

    lot1, lot2 = [], []
    for domaine in domaines:
        fiches = domaine.get("fiches") or []
        textes = domaine.get("textes") or []
        lacunes = domaine.get("lacunes") or []
        if not lacunes:
            continue
        entree = {"code": domaine.get("code"), "libelle": domaine.get("libelle"),
                  "fiches": len(fiches), "textes": len(textes),
                  "lacunes": lacunes,
                  "cles_moteur": domaine.get("cles_moteur") or []}
        # Lot 1 : un document existe déjà mais son identité ou son intégration
        # n'est pas établie — la reprise coûte moins qu'une recherche neuve.
        if textes:
            lot1.append(entree)
        else:
            lot2.append(entree)

    # Priorité interne : les domaines qui portent déjà des fiches servent des gens.
    lot1.sort(key=lambda e: (-e["fiches"], e["code"]))
    lot2.sort(key=lambda e: (-e["fiches"], e["code"]))
    return lot1, lot2, references


def rediger(lot1, lot2, references):
    lignes = []
    a = lignes.append
    a("# Recherche prioritaire — plan du Research Agent\n")
    a("Document **généré** par `bin/recherche_priorites.py` depuis les lacunes déclarées "
      "dans `KNOWLEDGE/domaines_24.json`. Il ne modifie rien : ni base, ni statut.\n")
    a("## Règles que le Research Agent ne franchit pas\n")
    a("1. **Aucune écriture en base.** La collecte produit des constats ; l'intégration "
      "passe par `bin/integrer_collecte.py`, avec ses contrôles.")
    a("2. **Aucun contournement de mur.** CNDJ (`biblio.cndj.ci`) est payant, "
      "`sgg.gouv.ci/jo.php` demande une authentification : on ne les force pas.")
    a("3. **Aucune promotion de statut.** Un texte téléchargé reste `A_VERIFIER` ; "
      "`VERIFIE` exige une URL officielle, une empreinte et une date ; "
      "`VERIFIE_MANUELLEMENT` exige une relecture humaine, qui n'a pas eu lieu.")
    a("4. **Aucune source secondaire présentée comme officielle.** Une reproduction "
      "d'éditeur est signalée comme telle.\n")
    a("## Lot 1 — documents déjà repérés, identité ou intégration à établir\n")
    a("Ces domaines ont un candidat mais rien de citable : c'est le meilleur rendement "
      "par heure de travail.\n")
    a("| Code | Domaine | Textes repérés | Fiches servies | Lacune |")
    a("|---|---|---|---|---|")
    for e in lot1:
        a("| %s | %s | %d | %d | %s |" % (e["code"], (e["libelle"] or "")[:44],
                                          e["textes"], e["fiches"],
                                          " ; ".join(e["lacunes"])[:180].replace("|", "/")))
    a("\n## Lot 2 — domaines sans aucun texte identifié\n")
    a("| Code | Domaine | Fiches servies | Lacune |")
    a("|---|---|---|---|")
    for e in lot2:
        a("| %s | %s | %d | %s |" % (e["code"], (e["libelle"] or "")[:44], e["fiches"],
                                     " ; ".join(e["lacunes"])[:180].replace("|", "/")))
    a("\n## Comment exécuter un lot\n")
    a("```bash")
    a("# 1. vérifier l'accessibilité réelle des sources (réseau requis)")
    a("python3 bin/verifier_sources.py")
    a("# 2. télécharger, mesurer, extraire — constats seulement, pas de base")
    a("python3 bin/collecte_distante.py --cle <cle_du_manifeste>")
    a("# 3. intégrer en local, avec les garde-fous de couverture et d'hôte")
    a("python3 bin/integrer_collecte.py")
    a("# 4. mesurer ce que la recherche en tire réellement")
    a("python3 bin/mesurer_recherche.py --rapport")
    a("```\n")
    a("## État des références (mesuré)\n")
    a("| État | Nombre |")
    a("|---|---|")
    for etat in ("VERIFIE", "PARTIELLEMENT_VERIFIE", "A_VERIFIER"):
        a("| `%s` | %d |" % (etat, sum(1 for v in references.values() if v == etat)))
    a("| **Total** | %d |\n" % len(references))
    a("Aucune de ces références n'est juridiquement validée par un humain. "
      "Voir `KNOWLEDGE/registre_validation_humaine.md`.\n")
    a("## Lacune connue, non résoluble automatiquement\n")
    a("* **Loi n° 2025-221** (contentieux du bail, exécution des expulsions) : "
      "introuvable en ligne (`civlii.laws.africa` → 404, aucun exemplaire sur "
      "`*.gouv.ci`). Voir `KNOWLEDGE/05_LACUNE_LOI_2025_221.md`. "
      "Aucune reconstitution ne doit être tentée.")
    return "\n".join(lignes)


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("--afficher", action="store_true")
    arguments = analyseur.parse_args(argv)
    lot1, lot2, references = classer()
    contenu = rediger(lot1, lot2, references)
    if arguments.afficher:
        print(contenu)
        return 0
    with open(SORTIE, "w", encoding="utf-8") as flux:
        flux.write(contenu)
    print("Écrit : %s — lot 1 : %d domaine(s), lot 2 : %d domaine(s)"
          % (os.path.relpath(SORTIE, RACINE), len(lot1), len(lot2)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
