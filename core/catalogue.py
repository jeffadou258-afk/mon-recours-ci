# -*- coding: utf-8 -*-
"""Catalogue de fiches : une question courante -> un article réel, vérifié.

Une fiche ne CONTIENT pas de droit : elle POINTE vers un article du corpus et
reprend son texte mot pour mot. La couche conversationnelle n'invente donc
jamais d'énoncé — elle ne peut servir que ce que le corpus contient.

Chaque fiche est **revalidée au chargement** contre la base :

  * la référence existe et l'article est citables (document `articles_fiables=1`) ;
  * la citation se retrouve littéralement dans le texte indexé ;
  * l'énoncé ne dépasse pas l'article (contrôle lexical mécanique).

Si une seule vérification échoue, `charger()` lève. Une fiche fausse ne peut
donc pas être servie en silence — c'est le point de tout ce module.

Le fichier `KNOWLEDGE/catalogue.json` est GÉNÉRÉ : voir
`bin/generer_catalogue.py`. Les citations y sont dérivées du corpus, jamais
retapées à la main, ce qui élimine la faute de recopie.
"""

import json
import os
import re

from core import base, corpus
from core.base import normaliser

CHEMIN_CATALOGUE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "KNOWLEDGE", "catalogue.json")

# Motifs d'artefact OCR fréquents : un mot coupé par un espace (« e st »,
# « volan t »). On ne RÉÉCRIT pas la citation — ce serait falsifier le texte —
# on signale à la lecture qu'elle est verbatim, artefact compris.
_ARTEFACT = re.compile(r"\b\w{1,3} \w{1,3}\b")
# Césure de fin de ligne reprise telle quelle par l'extraction (« engage- ment »).
_CESURE = re.compile(r"\b\w+- \w+")


class CatalogueInvalide(Exception):
    """Une fiche ne correspond pas au corpus : rien ne doit être servi."""


def _charge_brut(chemin=None):
    chemin = chemin or CHEMIN_CATALOGUE
    if not os.path.isfile(chemin):
        raise CatalogueInvalide("catalogue absent : %s (lancer bin/generer_catalogue.py)"
                                % chemin)
    with open(chemin, encoding="utf-8") as flux:
        return json.load(flux)


def charger(chemin=None, chemin_db=None):
    """Charge et REVALIDE chaque fiche. Lève si une fiche ne tient pas."""
    donnees = _charge_brut(chemin)
    fiches, rejets = [], []
    for brute in donnees.get("fiches", []):
        domaine = brute["domaine"]
        reference = None
        for candidat in base.lister_references(domaine=domaine, chemin=chemin_db):
            if (candidat.get("numero_texte") or None) == (brute.get("numero_texte") or None):
                reference = candidat
                break
        if reference is None:
            rejets.append((brute.get("id"), "référence absente du corpus"))
            continue
        article = corpus.obtenir_article_par_reference(
            reference["ref_id"], brute["article"], chemin=chemin_db)
        if article is None:
            rejets.append((brute.get("id"), "article absent ou non citable"))
            continue
        ok, details = corpus.verifier_citation_article(
            reference["ref_id"], brute["article"], brute["citation"], chemin=chemin_db)
        if not ok:
            rejets.append((brute.get("id"), "citation NON présente : %s"
                           % details.get("raison")))
            continue
        controle = corpus.verifier_enonce_contre_article(
            reference["ref_id"], brute["article"], brute["citation"], chemin=chemin_db)
        if not controle["ok"]:
            rejets.append((brute.get("id"), "énoncé non soutenu par l'article : %s"
                           % controle["mots_absents"]))
            continue
        fiche = dict(brute)
        fiche.update({
            "ref_id": reference["ref_id"],
            "etat_verification": reference["etat_verification"],
            "titre_texte": reference["titre_officiel"],
            "url_source": reference["source_url"],
            "limites_texte": reference.get("limites_interpretation"),
            "origine_texte": article.get("origine_texte"),
            "recoupe": bool(article.get("recoupe")),
            "confiance_ocr": article.get("confiance_ocr"),
            "sha256_article": article.get("sha256_article"),
        })
        if _ARTEFACT.search(brute["citation"]) and article.get("origine_texte") == "OCR_AUTO":
            fiche["note_lecture"] = (
                "Citation reproduite mot pour mot depuis un texte lu par OCR : elle peut "
                "porter une coupure de mot (« e st » pour « est »). Le texte n'a pas été "
                "corrigé ici.")
        elif _CESURE.search(brute["citation"]):
            fiche["note_lecture"] = (
                "Citation reproduite mot pour mot : une césure de fin de ligne du document "
                "d'origine apparaît à l'intérieur d'un mot (« engage- ment »). Le texte n'a "
                "pas été corrigé ici.")
        fiches.append(fiche)
    if rejets:
        raise CatalogueInvalide(
            "fiches non conformes au corpus : %s" % "; ".join("%s (%s)" % r for r in rejets))
    if not fiches:
        raise CatalogueInvalide("catalogue vide : aucune fiche exploitable")
    return fiches


def _correspond(declencheur, texte_normalise):
    """Un déclencheur tombe-t-il dans le texte ?

    Deux ponts : la phrase exacte, puis le TOUS-LES-MOTS (chacun de 4 lettres ou
    plus). Sans le second, « reprendre son logement » ne rencontrait pas le
    déclencheur « reprendre le logement » — un mot intercalé suffisait à perdre
    la fiche. Les mots courts (< 4 lettres) sont ignorés : ils n'ont pas de
    pouvoir discriminant.
    """
    declencheur = normaliser(declencheur)
    if not declencheur:
        return False
    if declencheur in texte_normalise:
        return True
    mots = [mot for mot in declencheur.split() if len(mot) >= 4]
    return bool(mots) and all(mot in texte_normalise for mot in mots)


def pour_demande(demande, domaines=(), fiches=None, chemin_db=None):
    """Fiches qui répondent à la demande, par déclencheur puis par domaine."""
    fiches = fiches if fiches is not None else charger(chemin_db=chemin_db)
    texte = normaliser(demande or "")
    retenues, par_domaine = [], []
    for fiche in fiches:
        if any(_correspond(d, texte) for d in fiche.get("declencheurs", ())):
            retenues.append(fiche)
        elif fiche["domaine"] in domaines:
            par_domaine.append(fiche)
    # Si aucun déclencheur ne tombe, on ne sert rien : proposer des articles au
    # hasard serait exactement le comportement qu'on veut éviter.
    return retenues, par_domaine


def par_domaine(domaine, fiches=None, chemin_db=None):
    fiches = fiches if fiches is not None else charger(chemin_db=chemin_db)
    return [f for f in fiches if f["domaine"] == domaine]


def couverture(fiches=None, chemin_db=None):
    """Ce que le catalogue sait traiter, domaine par domaine — en toute clarté."""
    fiches = fiches if fiches is not None else charger(chemin_db=chemin_db)
    compte = {}
    for fiche in fiches:
        compte.setdefault(fiche["domaine"], []).append(fiche["titre"])
    return compte
