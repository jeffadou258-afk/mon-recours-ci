# -*- coding: utf-8 -*-
"""Coeur de l'agent Mon Recours CI.

Modules :
  garde_fous     refus typés, invariants
  urgence        priorité sécurité / orientation
  sources        vérification HTTP réelle des sources officielles
  base           corpus de références juridiques (SQLite) + métadonnées obligatoires
  faits          faits, statuts, informations manquantes
  qualification  domaine juridique + questions ciblées
  analyse        analyse structurée + validation anti-invention
  plan_action    plan d'action + verrous humains
  documents      brouillons de courriers (jamais envoyés)
  evidence       dossier de traçabilité
"""

from . import base, documents, evidence, faits, garde_fous, plan_action, qualification, sources, urgence

__all__ = [
    "base",
    "documents",
    "evidence",
    "faits",
    "garde_fous",
    "plan_action",
    "qualification",
    "sources",
    "urgence",
]
