# -*- coding: utf-8 -*-
"""Masquage des coordonnées avant tout envoi à un fournisseur extérieur.

Appliqué au récit AVANT qu'il ne quitte le serveur (couche de langage). Ce qui
est masqué : adresses électroniques, numéros de téléphone (9 chiffres ou plus,
espaces, points ou tirets tolérés, indicatif « +225 » compris) — ce qui couvre aussi les numéros longs de pièces
ou de comptes. Effet de bord assumé : un très grand montant écrit chiffre par
chiffre (« 150 000 000 ») est aussi masqué.

Ce qui ne l'est PAS, et doit être dit : les noms de personnes et les adresses
postales écrits en clair. Les reconnaître sans modèle est peu fiable ; c'est
pourquoi l'envoi à un tiers exige un accord explicite du propriétaire
(`MONRECOURS_LLM_ACCORD_DONNEES=oui`).
"""

import re

_COURRIEL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_TELEPHONE = re.compile(r"(?:\+\d{2,3}[\s.-]?)?(?:\d[\s.-]?){8,}\d")


def masquer(texte):
    """Renvoie (texte_masqué, nombre_de_masquages)."""
    if not texte:
        return "", 0
    compte = 0

    def _remplacer(etiquette):
        def _f(_):
            nonlocal compte
            compte += 1
            return "[%s MASQUÉ]" % etiquette
        return _f

    texte = _COURRIEL.sub(_remplacer("COURRIEL"), texte)
    texte = _TELEPHONE.sub(_remplacer("NUMÉRO"), texte)
    return texte, compte
