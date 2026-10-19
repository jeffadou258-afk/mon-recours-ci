# -*- coding: utf-8 -*-
"""Guide de clarification : des questions qui vérifient les conditions des articles.

Source : `KNOWLEDGE/questions_clarification.json`. Chaque question est rattachée à
une ou plusieurs fiches du catalogue et vérifie une condition ÉCRITE dans leur
article. Ses « effets » (un par réponse) reformulent cette condition : ce sont
des LECTURES, jamais des citations, et le guide entier porte le statut
`A_RELIRE_PAR_UN_JURISTE` tant qu'aucune relecture n'est tracée.

Contrôles faits AU CHARGEMENT (un guide non conforme n'est jamais servi) :

  * chaque question pointe vers des fiches qui existent dans le catalogue ;
  * clés uniques, réponses limitées à oui / non, conditions `si` résolubles ;
  * un effet ne cite que les articles de ses fiches (« article 416 ») ;
  * tout nombre écrit dans un effet (« deux mois », « trois cents jours »,
    « 18 ans ») figure dans le texte de l'un de ces articles : aucun délai,
    plafond ou âge ne peut être ajouté par le guide.

Le module ne fait aucune analyse juridique : il choisit des questions, lit les
réponses, signale les contradictions avec le récit et les manques.
"""

import json
import os
import re

from core import corpus
from core.base import normaliser

CHEMIN_GUIDE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "KNOWLEDGE", "questions_clarification.json")

VALEURS = ("oui", "non")
TOURS_MAX = 3

# Mots de nombre contrôlés (« un » et « une » sont exclus : ce sont aussi des articles).
_NOMBRES_MOTS = ("deux", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix",
                 "onze", "douze", "quinze", "vingt", "trente", "quarante", "cinquante",
                 "soixante", "cent", "cents", "mille")
_RE_ARTICLE = re.compile(r"\barticles?\s+(\d+)", re.IGNORECASE)
_RE_CHIFFRES = re.compile(r"\b\d+\b")


class GuideInvalide(Exception):
    """Le guide ne correspond plus au catalogue ou ajoute un nombre absent des articles."""


def _texte_articles(fiches, catalogue, chemin_db=None):
    textes = []
    for fid in fiches:
        fiche = catalogue[fid]
        article = corpus.obtenir_article_par_reference(fiche["ref_id"], fiche["article"],
                                                       chemin=chemin_db)
        textes.append((article or {}).get("texte") or fiche.get("citation") or "")
    return normaliser(" ".join(textes))


def _nombres(texte):
    """Nombres écrits dans un texte normalisé, hors numéros d'articles."""
    sans_articles = _RE_ARTICLE.sub(" ", texte)
    trouves = set(_RE_CHIFFRES.findall(sans_articles))
    mots = set(re.findall(r"[a-z]+", sans_articles))
    trouves.update(m for m in _NOMBRES_MOTS if m in mots)
    return trouves


def valider(guide, catalogue, chemin_db=None):
    """Lève `GuideInvalide` à la première non-conformité. Renvoie les questions."""
    questions = guide.get("questions")
    if not isinstance(questions, list) or not questions:
        raise GuideInvalide("guide vide")
    cles = set()
    for q in questions:
        cle = q.get("cle")
        if not cle or cle in cles:
            raise GuideInvalide("clé absente ou en double : %r" % cle)
        cles.add(cle)
        if not q.get("question") or not q.get("pourquoi"):
            raise GuideInvalide("%s : question ou motif manquant" % cle)
        fiches = q.get("fiches") or []
        inconnues = [f for f in fiches if f not in catalogue]
        if not fiches or inconnues:
            raise GuideInvalide("%s : fiches inconnues du catalogue %s" % (cle, inconnues))
        effets = q.get("effets") or {}
        if set(effets) - set(VALEURS) or not effets:
            raise GuideInvalide("%s : effets attendus pour oui / non uniquement" % cle)
        if q.get("alerte_si") not in (None,) + VALEURS:
            raise GuideInvalide("%s : alerte_si invalide" % cle)
        articles_permis = {str(catalogue[f]["article"]) for f in fiches}
        texte_articles = _texte_articles(fiches, catalogue, chemin_db)
        nombres_articles = _nombres(texte_articles)
        for valeur, effet in effets.items():
            cites = set(_RE_ARTICLE.findall(effet))
            hors = cites - articles_permis
            if hors:
                raise GuideInvalide("%s/%s : cite l'article %s, absent de ses fiches"
                                    % (cle, valeur, ", ".join(sorted(hors))))
            ajoutes = _nombres(normaliser(effet)) - nombres_articles
            if ajoutes:
                raise GuideInvalide("%s/%s : nombre absent des articles cités : %s"
                                    % (cle, valeur, ", ".join(sorted(ajoutes))))
    for q in questions:
        for parent, valeur in (q.get("si") or {}).items():
            if parent not in cles or valeur not in VALEURS:
                raise GuideInvalide("%s : condition `si` irrésoluble (%s=%s)"
                                    % (q["cle"], parent, valeur))
    return questions


def charger(fiches, chemin=None, chemin_db=None):
    """Charge et valide le guide contre les fiches réellement chargées."""
    chemin = chemin or CHEMIN_GUIDE
    if not os.path.isfile(chemin):
        return {"statut_validation": None, "questions": []}
    with open(chemin, encoding="utf-8") as flux:
        guide = json.load(flux)
    catalogue = {f["id"]: f for f in fiches}
    guide["questions"] = valider(guide, catalogue, chemin_db)
    return guide


# -- lecture des réponses ---------------------------------------------------

def lire_valeur(reponse):
    """« oui », « non » ou None (je ne sais pas / vide). Tolère « oui, précision »."""
    if not isinstance(reponse, str):
        return None
    tete = normaliser(reponse).strip().split(",")[0].split()
    if not tete:
        return None
    return tete[0] if tete[0] in VALEURS else None


def suggestion(question, recit):
    """Ce que le récit laisse penser, s'il le dit clairement (sinon None)."""
    texte = normaliser(recit or "")
    oui = [i for i in question.get("indices_oui", []) if normaliser(i) in texte]
    non = [i for i in question.get("indices_non", []) if normaliser(i) in texte]
    if oui and not non:
        return {"valeur": "oui", "indice": oui[0]}
    if non and not oui:
        return {"valeur": "non", "indice": non[0]}
    return None


def questions_pour(fiches_retenues, guide, deja_posees=(), reponses=None):
    """Questions à poser maintenant : celles des fiches retenues, conditions remplies."""
    ids = {f["id"] for f in fiches_retenues}
    reponses = reponses or {}
    a_poser = []
    for q in guide.get("questions", []):
        if q["cle"] in deja_posees or not ids.intersection(q["fiches"]):
            continue
        condition = q.get("si") or {}
        if all(lire_valeur(reponses.get(p)) == v for p, v in condition.items()):
            a_poser.append(q)
    return a_poser


def contradictions(questions, reponses, recit):
    """Réponse « oui » / « non » contraire à ce que le récit dit explicitement."""
    trouvees = []
    for q in questions:
        valeur = lire_valeur(reponses.get(q["cle"]))
        indice = suggestion(q, recit)
        if valeur and indice and indice["valeur"] != valeur:
            trouvees.append({
                "cle": q["cle"], "question": q["question"],
                "reponse": valeur, "recit": indice["indice"],
                "message": ("Votre récit mentionne « %s », mais vous avez répondu « %s » "
                            "à : %s" % (indice["indice"], valeur, q["question"])),
            })
    return trouvees


def application(questions, reponses, catalogue):
    """Lecture conditionnelle des articles au vu des réponses. Jamais une citation."""
    lignes, manquantes = [], []
    for q in questions:
        valeur = lire_valeur(reponses.get(q["cle"]))
        if valeur is None:
            manquantes.append({"cle": q["cle"], "question": q["question"],
                               "pourquoi": q["pourquoi"]})
            continue
        effet = (q.get("effets") or {}).get(valeur)
        if not effet:
            continue
        lignes.append({
            "cle": q["cle"], "question": q["question"], "reponse": valeur,
            "lecture": effet,
            "articles": [{"article": catalogue[f]["article"],
                          "numero_texte": catalogue[f].get("numero_texte")}
                         for f in q["fiches"] if f in catalogue],
            "alerte": q.get("alerte_si") == valeur,
        })
    return lignes, manquantes
