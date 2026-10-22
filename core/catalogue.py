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


def reference_citable(domaine, numero_texte, article, chemin_db=None):
    """Première référence du domaine portant ce numéro OÙ L'ARTICLE EST CITABLE.

    Un même texte peut avoir deux références (deux exemplaires officiels, dont un
    scan resté sans texte) : la première dans l'ordre de la base est conservée si
    l'article y est citable — comportement historique —, sinon la suivante.
    Renvoie (référence, article) ou (référence_sans_article | None, None)."""
    premiere = None
    for candidat in base.lister_references(domaine=domaine, chemin=chemin_db):
        if (candidat.get("numero_texte") or None) != (numero_texte or None):
            continue
        premiere = premiere or candidat
        trouve = corpus.obtenir_article_par_reference(candidat["ref_id"], article, chemin=chemin_db)
        if trouve is not None:
            return candidat, trouve
    return premiere, None


def charger(chemin=None, chemin_db=None):
    """Charge et REVALIDE chaque fiche. Lève si une fiche ne tient pas."""
    donnees = _charge_brut(chemin)
    fiches, rejets = [], []
    for brute in donnees.get("fiches", []):
        domaine = brute["domaine"]
        reference, article = reference_citable(domaine, brute.get("numero_texte"), brute["article"], chemin_db)
        if reference is None:
            rejets.append((brute.get("id"), "référence absente du corpus"))
            continue
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


def _distance_au_plus_un(a, b):
    """Vrai si les deux mots diffèrent d'au plus une lettre (ajout, retrait, remplacement)."""
    if a == b:
        return True
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) > len(b):
        a, b = b, a
    if len(a) == len(b):
        return sum(1 for x, y in zip(a, b) if x != y) <= 1
    i = j = ecarts = 0
    while i < len(a) and j < len(b):
        if a[i] == b[j]:
            i += 1
        else:
            ecarts += 1
            if ecarts > 1:
                return False
        j += 1
    return True


def _mot_present(mot, mots_du_texte):
    """Mot entier présent, ou à une faute près pour les mots de 5 lettres et plus."""
    if mot in mots_du_texte:
        return True
    if len(mot) < 5:
        return False
    return any(len(m) >= 5 and _distance_au_plus_un(mot, m) for m in mots_du_texte)


def _correspond(declencheur, texte_normalise):
    """Un déclencheur tombe-t-il dans le texte ?

    Deux ponts : la phrase exacte, puis le TOUS-LES-MOTS (chacun de 4 lettres ou
    plus). Sans le second, « reprendre son logement » ne rencontrait pas le
    déclencheur « reprendre le logement » — un mot intercalé suffisait à perdre
    la fiche. Les mots courts (< 4 lettres) sont ignorés : ils n'ont pas de
    pouvoir discriminant.

    Correctifs du 19/10/2026 (audit des 24 domaines) :
      * MOTS ENTIERS uniquement : « reprise » tombait dans « entreprise » et
        servait le congé du bailleur à une question de marque ;
      * UNE FAUTE tolérée par mot de 5 lettres ou plus (« reconaitre »,
        « volan ») : l'utilisateur n'a pas à écrire sans faute.
    """
    declencheur = normaliser(declencheur)
    if not declencheur:
        return False
    if re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(declencheur), texte_normalise):
        return True
    mots_du_texte = set(re.findall(r"[a-z0-9']+", texte_normalise))
    mots_du_texte |= {m.split("'", 1)[1] for m in mots_du_texte if "'" in m}
    tous = re.findall(r"[a-z0-9']+", declencheur)
    mots = [mot for mot in tous if len(mot) >= 4]
    # Correctif du 20/10/2026 : une expression de plusieurs mots dont UN SEUL compte
    # 4 lettres ou plus (« garde a vue », « mon mari me bat ») se réduisait à ce mot :
    # « garde » servait la garde à vue à « la garde des enfants ». Une telle expression
    # doit figurer telle quelle ; un déclencheur d'un seul mot garde sa tolérance.
    if len(tous) > 1 and len(mots) < 2:
        return False
    return bool(mots) and all(_mot_present(mot, mots_du_texte) for mot in mots)


def pour_demande(demande, domaines=(), fiches=None, chemin_db=None, scores=None):
    """Fiches qui répondent à la demande, par déclencheur puis par domaine.

    `scores` (facultatif) : scores de routage par domaine (`qualification`).
    Quand des fiches de plusieurs domaines tombent, seules celles du domaine le
    mieux classé sont gardées (ex aequo : toutes). Sans ce tri, « mon bailleur
    garde ma caution » servait aussi le cautionnement OHADA.
    """
    fiches = fiches if fiches is not None else charger(chemin_db=chemin_db)
    texte = normaliser(demande or "")
    retenues, par_domaine = [], []
    def note(domaine):
        return ((scores or {}).get(domaine) or {}).get("score", 0)

    for fiche in fiches:
        touches = [d for d in fiche.get("declencheurs", ()) if _correspond(d, texte)]
        # Un déclencheur d'UN SEUL mot (« préavis », « reprise », « résiliation »)
        # ne suffit que si le domaine de la fiche est reconnu dans le récit :
        # sinon « licencié sans préavis » servait le congé du BAILLEUR et
        # « ma police d'assurance résiliée » la résiliation du BAIL (audit 19/10).
        if touches and scores is not None and note(fiche["domaine"]) == 0 and \
                all(len(normaliser(d).split()) == 1 for d in touches):
            touches = []
        if touches:
            retenues.append(fiche)
        elif fiche["domaine"] in domaines:
            par_domaine.append(fiche)
    if scores and len({f["domaine"] for f in retenues}) > 1:
        meilleure = max(note(f["domaine"]) for f in retenues)
        retenues = [f for f in retenues if note(f["domaine"]) == meilleure]
    # Si aucun déclencheur ne tombe, on ne sert rien : proposer des articles au
    # hasard serait exactement le comportement qu'on veut éviter.
    return retenues, par_domaine


def valider_fiches_proposees(propositions, demande, fiches=None, domaines=(), scores=None):
    """Contrôle INDÉPENDANT de la pertinence d'une fiche proposée par un modèle.

    Un modèle de langage ne rend jamais une liste vide par prudence : il choisit
    toujours la fiche la plus plausible. « Plausible » n'est pas « pertinente » —
    c'est exactement l'écart qui a fait citer un article sur les personnes
    vulnérables pour une déclaration de naissance.

    Cette fonction rejoue donc la décision SANS le modèle. Une fiche n'entre que
    par deux portes, toutes deux calculées hors du modèle :

      A. un DÉCLENCHEUR tombe dans le récit, avec la même garde que
         `pour_demande` (un déclencheur d'un seul mot exige que le domaine de la
         fiche soit reconnu dans le récit) ;
      B. le DOMAINE de la fiche fait partie des domaines qualifiés pour le récit
         (`qualification`, déterministe). C'est la porte qui laisse au modèle son
         utilité réelle : reconnaître « l'argent versé à l'entrée » là où aucun
         mot-clé ne dit « caution ». Le modèle ne choisit donc pas le domaine ;
         il ne peut que désigner une fiche DANS un domaine déjà établi.

    Une fiche d'un domaine non qualifié est refusée même si ses mots ressemblent
    à ceux du récit : les mots ne contournent pas le routage.

    Retourne (retenues, rejets). Les rejets portent une raison exploitable par le
    journal — jamais le récit.
    """
    fiches = fiches if fiches is not None else charger()
    index = {f["id"]: f for f in fiches}
    texte = normaliser(demande or "")

    def note(domaine):
        return ((scores or {}).get(domaine) or {}).get("score", 0)

    retenues, rejets, vus = [], [], set()
    for proposition in propositions or []:
        identifiant = proposition.get("id") if isinstance(proposition, dict) else proposition
        fiche = index.get(identifiant)
        if fiche is None:
            rejets.append({"fiche": identifiant, "raison": "absente du catalogue"})
            continue
        if identifiant in vus:
            continue
        touches = [d for d in fiche.get("declencheurs", ()) if _correspond(d, texte)]
        if touches and scores is not None and note(fiche["domaine"]) == 0 and \
                all(len(normaliser(d).split()) == 1 for d in touches):
            touches = []
        if touches:
            vus.add(identifiant)
            retenues.append(fiche)
            continue
        if fiche["domaine"] in domaines:
            # Porte B : le domaine a été établi par la qualification déterministe.
            # Les mots du récit ne sont PAS nécessaires — c'est précisément ce que
            # le modèle apporte — mais le domaine, lui, n'est jamais choisi par lui.
            vus.add(identifiant)
            retenues.append(fiche)
            continue
        rejets.append({"fiche": identifiant, "raison": "domaine hors qualification"})
    return retenues, rejets


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
