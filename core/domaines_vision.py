# -*- coding: utf-8 -*-
"""Les 24 domaines de la vision : reconnaître le domaine d'une question, même non couvert.

Source : `KNOWLEDGE/domaines_24.json` (aucune règle de droit : des mots de
reconnaissance et le rattachement des fiches existantes).

Usage : quand aucune fiche ne répond, le service NOMME le domaine probable et
dit honnêtement qu'il n'est pas couvert, au lieu d'un message vague. Le statut
d'un domaine n'est jamais déclaré : il se mesure (`bin/audit_domaines.py`).
"""

import json
import os

from core.base import normaliser

CHEMIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      "KNOWLEDGE", "domaines_24.json")


class RegistreInvalide(Exception):
    pass


def charger(fiches=None, chemin=None):
    with open(chemin or CHEMIN, encoding="utf-8") as flux:
        donnees = json.load(flux)
    domaines = donnees["domaines"]
    codes = [d["code"] for d in domaines]
    if codes != list(range(1, 25)):
        raise RegistreInvalide("les codes doivent aller de 1 à 24, dans l'ordre")
    if fiches is not None:
        ids = {f["id"] for f in fiches}
        for d in domaines:
            inconnues = [f for f in d["fiches"] if f not in ids]
            if inconnues:
                raise RegistreInvalide("domaine %d : fiches inconnues %s" % (d["code"], inconnues))
    return domaines


def reconnaitre(texte, domaines=None, maximum=3):
    """Domaines probables d'un récit, du plus au moins appuyé (mots de reconnaissance)."""
    from core.catalogue import _correspond  # même règle de correspondance que les fiches
    domaines = domaines if domaines is not None else charger()
    norm = normaliser(texte or "")
    scores = []
    for d in domaines:
        trouves = [m for m in d["reconnaissance"] if _correspond(m, norm)]
        if trouves:
            scores.append((len(trouves), d, trouves))
    scores.sort(key=lambda x: (-x[0], x[1]["code"]))
    return [{"code": d["code"], "libelle": d["libelle"], "fiches_disponibles": len(d["fiches"]),
             "mots": trouves} for _, d, trouves in scores[:maximum]]
