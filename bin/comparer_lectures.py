# -*- coding: utf-8 -*-
"""Compare les lectures OCR d'un même scan et cartographie article -> page.

    python3 bin/comparer_lectures.py --cle ohada_jo_bulletin_1722_explnum_3974

N'ÉCRIT RIEN EN BASE. Produit `KNOWLEDGE/collecte/analyses/<cle>_comparaison.json` :

* les lectures disponibles du scan (moteur/modèle, dpi, texte source) ;
* les articles RETENUS par `preparer_ocr` (règle du projet : concordance >= 0,80
  avec une autre lecture) et ceux ÉCARTÉS, avec leur score ;
* la carte article -> page, calculée sur le texte brut de la lecture principale ;
* les trous de numérotation et les articles présents dans une seule lecture.

Aucune divergence n'est corrigée ici : elle est signalée, et la page source reste
retrouvable dans le fichier de lecture (marqueurs `--- PAGE n ---`).
"""

import argparse
import json
import os
import re
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)
sys.path.insert(0, os.path.join(RACINE, "bin"))

import integrer_collecte as IC  # noqa: E402
from core import corpus, ocr  # noqa: E402

SORTIE = os.path.join(RACINE, "KNOWLEDGE", "collecte", "analyses")
MOTIF_PAGE = re.compile(r"^--- PAGE (\d+) ---")


def pages_du_texte(texte):
    """Découpe un texte de lecture en {page: contenu}, via les marqueurs."""
    pages, courante = {}, None
    for ligne in (texte or "").splitlines():
        marque = MOTIF_PAGE.match(ligne)
        if marque:
            courante = int(marque.group(1))
            pages[courante] = []
            continue
        if courante is not None:
            pages[courante].append(ligne)
    return {n: "\n".join(lignes) for n, lignes in pages.items()}


def carte_article_page(texte):
    """Pour chaque numéro d'article, la PREMIÈRE page où son en-tête apparaît."""
    carte = {}
    for numero_page, contenu in sorted(pages_du_texte(texte).items()):
        for numero in corpus.extraire_articles(contenu):
            carte.setdefault(numero, numero_page)
    return carte


def trous(articles, maximum):
    presents = set()
    for numero in articles:
        if str(numero).isdigit():
            presents.add(int(numero))
    return [n for n in range(1, maximum + 1) if n not in presents]


def analyser(cle):
    inventaire = IC.lire_json(IC.INVENTAIRE)
    manifeste = {s["cle"]: s for s in IC.lire_json(IC.MANIFESTE)["sources"]}
    document = next((d for d in inventaire["documents"] if d["cle"] == cle), None)
    if document is None:
        raise SystemExit("document absent de l'inventaire : %s" % cle)
    resultat = IC.lire_json(os.path.join(IC.DOSSIER_RESULTATS, cle + ".json"))

    brut = dict(IC._textes_bruts(document, resultat))
    preparation = IC.preparer_ocr(document, inventaire, manifeste)
    rapport = {
        "cle": cle,
        "titre": document.get("titre") or (manifeste.get(cle) or {}).get("titre"),
        "pages": document.get("pages"),
        "lectures": [{"nom": nom, "caracteres": len(texte)} for nom, texte in brut.items()],
        "preparation_disponible": preparation is not None,
    }
    if preparation is None:
        rapport["motif"] = "aucune lecture exploitable pour preparer_ocr"
    else:
        articles = preparation["articles"]
        confiance = preparation["confiance"] or {}
        # `ecartes` est une LISTE de couples (numéro, texte) : ne pas la traiter en dict.
        bruts_ecartes = preparation["ecartes"] or []
        ecartes = []
        for element in bruts_ecartes:
            if isinstance(element, (list, tuple)) and len(element) >= 2:
                ecartes.append((element[0], element[1]))
            elif isinstance(element, dict):
                ecartes.append((element.get("numero"), element.get("texte")))
            else:
                ecartes.append((str(element), None))
        principal = preparation.get("principal_brut") or preparation["principal"] or ""
        titre_principal = preparation["nom_principal"]
        # Le texte brut peut couvrir PLUSIEURS actes (bulletin contenant deux textes) :
        # on applique le segment du manifeste, sinon la carte de pages attribuerait des
        # articles du second acte au premier.
        segment = (IC.lire_json(IC.MANIFESTE).get("sources") or [])
        segment = next((s.get("segment") for s in segment if s.get("cle") == cle), None)
        if segment:
            try:
                principal = IC.segmenter(principal, segment)
            except ValueError as erreur:
                rapport["erreur_segment"] = str(erreur)
        texte_principal = principal
        carte = carte_article_page(texte_principal)
        numeros = [int(n) for n in articles if str(n).isdigit()]
        maximum = max(numeros) if numeros else 0
        scores = [v for v in confiance.values() if isinstance(v, (int, float))]
        rapport.update({
            "lecture_principale": titre_principal,
            "comparateur": preparation.get("comparateur"),
            "articles_retenus": len(articles),
            "articles_ecartes": [{"article": str(n), "extrait": (t or "")[:160]}
                                 for n, t in ecartes],
            "nombre_ecartes": len(ecartes),
            "confiance": {"minimum": min(scores) if scores else None,
                          "moyenne": round(sum(scores) / len(scores), 4) if scores else None,
                          "maximum": max(scores) if scores else None,
                          "sous_seuil": sorted(n for n, v in confiance.items()
                                               if isinstance(v, (int, float)) and v < 0.80)},
            "numerotation": {"premier": min(numeros) if numeros else None,
                             "dernier": max(numeros) if numeros else None,
                             "maximum_annonce": maximum,
                             "trous": trous(articles, maximum)},
            "carte_article_page": {str(k): v for k, v in sorted(carte.items(),
                                                                key=lambda x: str(x[0]))},
            "pages_source": {nom: (resultat.get(k) or {}).get("fichier_ocr")
                             for nom, k in (("principal", "extraction_locale"),
                                            ("comparateur", "extraction_locale_fast"))},
            "corrections_en_tetes": len(preparation.get("corrections_en_tetes") or []),
            "retraits_en_tetes_pieds": preparation.get("retraits"),
            "nombres_divergents": preparation.get("nombres_divergents") or [],
            "hors_principale": preparation.get("hors_principale"),
            "illisibles": preparation.get("illisibles") or [],
        })
    return rapport


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("--cle", required=True)
    arguments = analyseur.parse_args(argv)
    rapport = analyser(arguments.cle)
    os.makedirs(SORTIE, exist_ok=True)
    chemin = os.path.join(SORTIE, arguments.cle + "_comparaison.json")
    with open(chemin, "w", encoding="utf-8") as flux:
        json.dump(rapport, flux, ensure_ascii=False, indent=1)
        flux.write("\n")

    print("Document     : %s (%s pages)" % (rapport.get("titre"), rapport.get("pages")))
    print("Lectures     : %s" % ", ".join("%s (%d car.)" % (l["nom"], l["caracteres"])
                                        for l in rapport["lectures"]))
    if not rapport.get("preparation_disponible"):
        print("Préparation  : INDISPONIBLE — %s" % rapport.get("motif"))
        return 1
    conf = rapport["confiance"]
    num = rapport["numerotation"]
    print("Principale   : %s | comparateur : %s" % (rapport["lecture_principale"],
                                                   rapport["comparateur"]))
    print("Articles     : %d retenus, %d écartés" % (rapport["articles_retenus"],
                                                    rapport["nombre_ecartes"]))
    print("Concordance  : min %.3f  moy %.3f  max %.3f  (sous 0,80 : %d)"
          % (conf["minimum"] or 0, conf["moyenne"] or 0, conf["maximum"] or 0,
             len(conf["sous_seuil"])))
    print("Numérotation : %s..%s (max annoncé %s), %d trou(s)"
          % (num["premier"], num["dernier"], num["maximum_annonce"], len(num["trous"])))
    if num["trous"]:
        print("  trous : %s" % num["trous"][:30])
    print("Carte pages  : %d article(s) localisé(s) sur une page"
          % len(rapport["carte_article_page"]))
    print("Écrit        : %s" % os.path.relpath(chemin, RACINE))
    return 0


if __name__ == "__main__":
    sys.exit(main())
