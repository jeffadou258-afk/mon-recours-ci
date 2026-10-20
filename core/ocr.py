# -*- coding: utf-8 -*-
"""Qualité de l'OCR — mesures, seuils, provenance.

Ce module porte la POLITIQUE d'intégration d'un texte obtenu par OCR. Il ne fait
aucun appel réseau, ne lit aucun PDF : il compare des textes et rend un verdict.

Trois principes :

1. **Un texte OCR n'est pas un texte à calque.** La provenance est enregistrée
   par article (`origine_texte`), avec une confiance mesurée. Confondre les deux
   ferait passer une reconnaissance automatique pour une lecture de document.

2. **Un seuil, pas une impression.** Un article OCR dont la similarité avec une
   autre copie officielle est inférieure à `QUALITE_MINIMALE` est ÉCARTÉ : il
   n'est pas indexé du tout. Un article entre les deux seuils est indexé mais
   marqué « à surveiller ».

3. **La mesure se méfie d'elle-même.** `difflib.SequenceMatcher` active
   `autojunk` par défaut : au-delà de 200 éléments, il traite comme « junk » tout
   élément présent dans plus de 1 % de la séquence, ce qui détruit la mesure sur
   un texte long. Mesuré sur le même corpus : 0,0647 avec `autojunk=True`
   contre 0,9646 avec `autojunk=False` pour le même article. La désactivation
   n'est pas un détail de confort, c'est la condition pour que le chiffre veuille
   dire quelque chose.
"""

import difflib
import re
import statistics

from core.base import normaliser

# Seuils de décision.
QUALITE_MINIMALE = 0.80    # en dessous : article ECARTE, jamais indexé
QUALITE_RECOUPEE = 0.90    # à partir de là : recoupé avec une autre copie officielle

# Provenances possibles d'un texte d'article.
ORIGINES = ("CALQUE_TEXTE", "OCR_AUTO", "VERIFIE_MANUELLEMENT")

VERDICT_RECOUPE = "RECOUPE"
VERDICT_A_SURVEILLER = "A_SURVEILLER"
VERDICT_ECARTE = "ECARTE"

DECISION_CALQUE = "INTEGRER_CALQUE_TEXTE"
DECISION_OCR_RECOUPE = "INTEGRER_OCR_RECOUPE"
DECISION_OCR_A_CONFIRMER = "INTEGRER_OCR_A_CONFIRMER"
DECISION_REFUS = "REFUSER"


def similarite(a, b):
    """Similarité de 0 à 1 entre deux textes, sur leur forme normalisée.

    `autojunk=False` est obligatoire — voir l'en-tête du module.
    """
    gauche, droite = normaliser(a), normaliser(b)
    if not gauche or not droite:
        return 0.0
    return difflib.SequenceMatcher(None, gauche, droite, autojunk=False).ratio()


def recouvrement_mots(a, b):
    """Part de mots partagés (indépendant de l'ordre et de la longueur)."""
    gauche = set(normaliser(a).split())
    droite = set(normaliser(b).split())
    if not gauche or not droite:
        return 0.0
    return len(gauche & droite) / float(len(gauche | droite))


def verdict_de(similarite_valeur):
    if similarite_valeur >= QUALITE_RECOUPEE:
        return VERDICT_RECOUPE
    if similarite_valeur >= QUALITE_MINIMALE:
        return VERDICT_A_SURVEILLER
    return VERDICT_ECARTE


def evaluer_articles_ocr(articles_ocr, articles_reference=None):
    """Compare les articles issus de l'OCR à une copie officielle de référence.

    `articles_reference` : dict {numero: texte} d'une autre copie officielle du
    MÊME texte (idéalement celle qui porte un calque texte). Sans référence, le
    module ne peut pas mesurer : il le dit et ne prétend rien (`avec_reference`).

    Retourne un rapport complet, y compris ce qui a été écarté et ce qui manque.
    """
    rapport = {
        "avec_reference": bool(articles_reference),
        "nb_articles_ocr": len(articles_ocr or {}),
        "nb_articles_reference": len(articles_reference or {}),
        "apparies": {},
        "ecartes": [],
        "a_surveiller": [],
        "absents_de_l_ocr": [],
        "statistiques": None,
    }

    if not articles_ocr:
        rapport["raison"] = "aucun article détecté dans le texte OCR"
        return rapport

    if not articles_reference:
        rapport["raison"] = (
            "aucune copie officielle de référence pour ce texte : la qualité ne peut "
            "pas être mesurée, seulement contrôlée structurellement"
        )
        return rapport

    valeurs = []
    for numero, texte_reference in sorted(articles_reference.items(),
                                          key=lambda kv: _tri_numero(kv[0])):
        texte_ocr = articles_ocr.get(numero)
        if texte_ocr is None:
            rapport["absents_de_l_ocr"].append(numero)
            continue
        valeur = similarite(texte_reference, texte_ocr)
        mots = recouvrement_mots(texte_reference, texte_ocr)
        verdict = verdict_de(valeur)
        entree = {
            "numero": numero,
            "similarite": round(valeur, 4),
            "recouvrement_mots": round(mots, 4),
            "verdict": verdict,
            "taille_reference": len(texte_reference),
            "taille_ocr": len(texte_ocr),
        }
        if verdict == VERDICT_ECARTE:
            entree["raison"] = (
                "similarité %.2f < seuil %.2f : erreur OCR probable OU divergence entre "
                "les deux copies officielles — à trancher par un humain" % (valeur, QUALITE_MINIMALE)
            )
            rapport["ecartes"].append(entree)
        else:
            rapport["apparies"][numero] = entree
            if verdict == VERDICT_A_SURVEILLER:
                rapport["a_surveiller"].append(entree)
        valeurs.append(valeur)

    if valeurs:
        rapport["statistiques"] = {
            "similarite_moyenne": round(statistics.mean(valeurs), 4),
            "similarite_mediane": round(statistics.median(valeurs), 4),
            "similarite_minimale": round(min(valeurs), 4),
            "part_recoupee": round(sum(1 for v in valeurs if v >= QUALITE_RECOUPEE) / len(valeurs), 4),
            "part_ge_seuil": round(sum(1 for v in valeurs if v >= QUALITE_MINIMALE) / len(valeurs), 4),
            "taux_couverture": round(len(valeurs) / float(max(1, len(articles_reference))), 4),
        }
    return rapport


def _tri_numero(numero):
    m = re.match(r"(\d+)", str(numero))
    return (int(m.group(1)), str(numero)) if m else (999999, str(numero))


# --------------------------------------------------------------------------
# Contrôles structurels — pour les textes sans copie de référence
# --------------------------------------------------------------------------
LIGNES_MINIMALES = 20
PART_LIGNES_ALPHABETIQUES = 0.85


def controler_structure(texte_ocr, chaines_attendues=(), minimum_articles=1):
    """Contrôle structurel d'un texte OCR sans référence disponible.

    Trois critères mesurables, aucun jugement sémantique :
      * toutes les chaînes attendues sont présentes (titre, numéro, autorité) ;
      * la part de lignes contenant des lettres est suffisante — un OCR qui
        produit des symboles n'est pas un texte ;
      * le parseur d'articles trouve au moins `minimum_articles` articles.

    `minimum_articles` est un PLANCHER, pas une mesure de qualité : une loi de
    ratification peut légitimement ne compter que deux articles. Ce contrôle
    vérifie qu'un texte est exploitable, il ne garantit pas sa fidélité — seule
    la comparaison à une autre copie officielle le fait.
    """
    from core.corpus import extraire_articles  # import local : évite un cycle à l'import

    texte = texte_ocr or ""
    lignes = [l for l in texte.split("\n") if l.strip() and not l.startswith("--- PAGE")]
    normalise = normaliser(texte)

    manquantes = [c for c in chaines_attendues if normaliser(c) not in normalise]
    avec_lettres = [l for l in lignes if re.search(r"[A-Za-zÀ-ÿ]{3,}", l)]
    part_lettres = (len(avec_lettres) / float(len(lignes))) if lignes else 0.0
    articles = extraire_articles(texte)

    criteres = {
        "nb_lignes": len(lignes),
        "nb_articles_detectes": len(articles),
        "part_lignes_avec_lettres": round(part_lettres, 4),
        "chaines_attendues_manquantes": manquantes,
    }
    echecs = []
    if len(lignes) < LIGNES_MINIMALES:
        echecs.append("trop peu de lignes (%d < %d)" % (len(lignes), LIGNES_MINIMALES))
    if manquantes:
        echecs.append("chaînes attendues absentes : %s" % ", ".join(manquantes))
    if part_lettres < PART_LIGNES_ALPHABETIQUES:
        echecs.append("part de lignes alphabétiques insuffisante (%.0f%% < %.0f%%)"
                      % (100 * part_lettres, 100 * PART_LIGNES_ALPHABETIQUES))
    if len(articles) < minimum_articles:
        echecs.append("aucun article exploitable détecté (< %d)" % minimum_articles)

    return {"ok": not echecs, "echecs": echecs, "criteres": criteres,
            "articles_detectes": len(articles)}


def decision(evaluation, controle_structurel=None):
    """Verdict d'intégration, avec ses raisons. Aucune décision silencieuse."""
    raisons = []
    if not evaluation.get("avec_reference"):
        if controle_structurel and controle_structurel.get("ok"):
            raisons.append("contrôle structurel réussi ; qualité non mesurable par recoupement")
            return {"decision": DECISION_OCR_A_CONFIRMER, "raisons": raisons,
                    "articles_integrables": evaluation.get("nb_articles_ocr", 0),
                    "articles_ecartes": 0}
        raisons.append("contrôle structurel échoué : %s"
                       % " ; ".join((controle_structurel or {}).get("echecs", ["non exécuté"])))
        return {"decision": DECISION_REFUS, "raisons": raisons,
                "articles_integrables": 0, "articles_ecartes": 0}

    statistiques = evaluation.get("statistiques") or {}
    integrables = len(evaluation.get("apparies", {}))
    ecartes = len(evaluation.get("ecartes", []))
    part = statistiques.get("part_ge_seuil", 0.0)

    if integrables == 0:
        raisons.append("aucun article n'atteint le seuil de similarité %.2f" % QUALITE_MINIMALE)
        return {"decision": DECISION_REFUS, "raisons": raisons,
                "articles_integrables": 0, "articles_ecartes": ecartes}

    if part >= QUALITE_RECOUPEE:
        raisons.append("%.0f%% des articles recoupés au-delà de %.2f"
                       % (100 * part, QUALITE_RECOUPEE))
        return {"decision": DECISION_OCR_RECOUPE, "raisons": raisons,
                "articles_integrables": integrables, "articles_ecartes": ecartes,
                "statistiques": statistiques}

    raisons.append("%.0f%% des articles seulement atteignent %.2f : intégration partielle"
                   % (100 * part, QUALITE_MINIMALE))
    return {"decision": DECISION_OCR_A_CONFIRMER, "raisons": raisons,
            "articles_integrables": integrables, "articles_ecartes": ecartes,
            "statistiques": statistiques}


# ---------------------------------------------------------------------------
# En-têtes d'articles mal lus par l'OCR (Journal officiel)
# ---------------------------------------------------------------------------
# Le Journal officiel ivoirien compose ses articles « Art. 21. — Texte… ».
# Sur un scan de qualité médiocre, l'OCR lit « Ait 20. — », « An 21, — »,
# « Art.6. — » (sans espace) : le découpage perd alors l'article entier.
# La correction ne porte QUE sur l'en-tête en début de ligne, exige le tiret
# typographique après le numéro (aucune phrase ordinaire ne commence ainsi) et
# ne touche jamais au corps de la disposition. Chaque correction est comptée et
# rapportée : c'est une lecture, déclarée comme telle dans la provenance.
_EN_TETE_OCR = re.compile(
    r"(?m)^(?P<pre>[ \t]*)(?P<mot>Art|Ait|Aït|An|Arl|Ari|Aft|Ant|Aru|Arı|Arts|Artt|Aart|Ar|At|Avt|Atr)"
    r"(?P<pt>[ \t]*[\.,']?[ \t]*)(?P<num>\d{1,3})(?P<apres>[ \t]*[\.,]?[ \t]*)(?P<tiret>[—–]|-{1,2}(?=[ \t]*\S))")


_EN_TETE_DEJA_LISIBLE = re.compile(r"^[ \t]*Art\.?[ \t]+\d{1,3}[ \t]*[\.,]?[ \t]*[—–-]")


def normaliser_en_tetes_jo(texte):
    """Renvoie (texte, corrections) ; `corrections` liste [(numéro, en-tête lu)].

    Un en-tête déjà lisible par le parseur (« Art. 5. — », « Art 5. — »,
    « Art. 14, — ») est laissé tel quel et n'est pas compté. Réservé aux textes OCR."""
    corrections = []

    def remplacer(m):
        original = m.group(0)
        if _EN_TETE_DEJA_LISIBLE.match(original):
            return original
        corrections.append((m.group("num"), original.strip()))
        return "%sArt. %s. %s" % (m.group("pre"), m.group("num"), m.group("tiret"))

    return _EN_TETE_OCR.sub(remplacer, texte or ""), corrections
