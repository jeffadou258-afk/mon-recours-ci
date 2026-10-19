# -*- coding: utf-8 -*-
"""Détection d'urgence (spec §5 et §12).

Priorité absolue : la sécurité et l'orientation d'abord, l'analyse juridique
ensuite — et seulement si elle reste utile et sans retarder cette orientation.

Ce module ne rend pas d'avis juridique et n'évalue pas la gravité des faits :
il détecte des marqueurs explicites de danger et fixe la PRIORITÉ D'ACTION.
Un marqueur est cité tel qu'il a été détecté, jamais reformulé.
"""

import re

from core.garde_fous import normaliser

# Marqueurs de danger immédiat. La personne d'abord, le droit ensuite.
_MARQUEURS_CRITIQUES = (
    (r"\b(couteaux?|machettes?|armes?|pistolets?|fusils?|kalach\w*)\b", "arme mentionnee"),
    (r"menac\w*[^.]{0,25}(?:tuer|mort|frapper|blesser|faire du mal)", "menace de mort ou de blessures"),
    (r"\b(?:il|elle|ils|elles) (?:va|vont|veut|veulent) me tuer", "menace de mort"),
    (r"menace de mort", "menace de mort"),
    (r"(me|nous) (frappe|bat|batt?e|agresse|violente)", "violences physiques"),
    (r"m'a (frappe|battu|agresse|blesse|poignarde)", "violences physiques"),
    (r"(frappe|bat|battu|maltrait\w*|abuse\w*|enferm\w*)[^.]{0,25}\b(les|mes|nos|ses|son|un|une|l')\s?enfants?\b",
     "danger pour un enfant"),
    (r"\b(saigne|inconscient|ne respire plus|blesse grave|gravement blesse)\w*", "urgence medicale"),
    (r"menac\w*[^.]{0,30}(publier|diffuser)[^.]{0,30}(photos?|videos?)[^.]{0,20}(intimes?|nue?s?)",
     "chantage a la diffusion d'images intimes"),
    (r"violences? conjugales?", "violences conjugales"),
    (r"viol(er|e|s)?\b", "violences sexuelles"),
    (r"sequestr\w*", "sequestration"),
    (r"(est|sont) retenus? de force", "sequestration"),
    (r"garde a vue", "garde a vue"),
    (r"(je suis|il est|elle est) en (prison|detention)", "detention"),
    (r"\b(detenu|detenue|ecroue)\b", "detention"),
    (r"expulsion (a lieu |prevue )?(demain|aujourd'hui|cette semaine|ce matin)", "expulsion imminente"),
    (r"(les |on ) (huissier|force de l'ordre)\w* (sont|est) (devant|a) (ma|la) (porte|maison)", "execution en cours"),
    (r"(huissier|commissaire de justice|forces? de l'ordre|police)\w*[^.]{0,15} (est|sont) devant (ma|la|notre) (porte|maison)",
     "execution en cours"),
    (r"enfant[^.]{0,30}(danger|maltrait|frappe|bat|abuse)", "danger pour un enfant"),
    (r"mineur[^.]{0,25}(danger|maltrait|violence)", "danger pour un mineur"),
    (r"je (veux|vais) (me tuer|mourir|en finir)", "detresse / risque vital"),
    (r"je (n'ai plus|songe) a (vivre|en finir)", "detresse / risque vital"),
    (r"(on ) (va )?me couper (l'eau|l'electricite) (aujourd'hui|demain)", "coupure imminente"),
)

# Marqueurs d'urgence élevée : pas de danger physique, mais échéance ou
# vulnérabilité qui exigent une orientation humaine rapide.
_MARQUEURS_ELEVES = (
    (r"expuls\w*", "procedure d'expulsion"),
    (r"(mise en demeure|sommation)", "mise en demeure"),
    (r"(commandement de payer|saisie|saisie-vente|saisie des salaires)", "voie d'execution"),
    (r"\bsaisir\b", "voie d'execution"),
    # Injonction de payer : l'opposition n'est recevable que dans un délai bref
    # (article 10 de l'AUPSRVE) — le délai lui-même est donné par la fiche, pas ici.
    (r"injonction de payer|ordonnance (d'|portant )injonction", "injonction de payer (delai d'opposition)"),
    (r"(demolir|detruire|raser|deguerpi\w*)[^.]{0,40}(demain|aujourd'hui|cette semaine|ce matin)", "demolition imminente"),
    (r"(demain|aujourd'hui|cette semaine)[^.]{0,40}(demolir|detruire|raser|deguerpi\w*)", "demolition imminente"),
    (r"\b(il|elle|ils|elles|on) (me|nous) menac\w*", "menaces"),
    (r"\bmenace (de|d')\w*", "menaces"),
    (r"\bhuissier\w*", "commissaire de justice"),
    (r"licenciement", "licenciement"),
    (r"(convocation|entretien prealable) (de|a) licenciement", "procedure disciplinaire"),
    (r"(demande|mise) (au tribunal|en justice)", "procedure judiciaire"),
    (r"audience", "audience"),
    (r"(plainte|porter plainte)", "procedure penale"),
    (r"(assignation|convocation)[^.]{0,20}tribunal", "procedure judiciaire"),
    (r"delai de (24|48) heures|expire (demain|dans) ", "delai court"),
    (r"\b(vieill|handicap|malade|vulnerab)\w*", "vulnerabilite"),
    (r"(mon|le) (enfant|bebe) (a |de )", "presence d'un enfant"),
)


def detecter(texte):
    """Retourne l'évaluation d'urgence.

    niveau : CRITIQUE | ELEVEE | NORMALE
    priorite : SECURITE_ET_ORIENTATION pour CRITIQUE, sinon ANALYSE_ET_ORIENTATION
    analyse_longue_autorisee : False dès que CRITIQUE (on n'ajoute pas de retard)
    """
    norm = normaliser(texte)
    declencheurs_critiques = []
    for motif, libelle in _MARQUEURS_CRITIQUES:
        m = re.search(motif, norm)
        if m and libelle not in {d["libelle"] for d in declencheurs_critiques}:
            declencheurs_critiques.append({"libelle": libelle, "detecte": m.group(0)})

    if declencheurs_critiques:
        return {
            "niveau": "CRITIQUE",
            "priorite": "SECURITE_ET_ORIENTATION",
            "analyse_longue_autorisee": False,
            "declencheurs": declencheurs_critiques,
            "consigne": (
                "Sécurité d'abord. Orienter immédiatement vers un interlocuteur "
                "humain et les services d'urgence si nécessaire. Aucune analyse "
                "juridique longue ne doit retarder cette orientation."
            ),
        }

    declencheurs_eleves = []
    for motif, libelle in _MARQUEURS_ELEVES:
        m = re.search(motif, norm)
        if m and libelle not in {d["libelle"] for d in declencheurs_eleves}:
            declencheurs_eleves.append({"libelle": libelle, "detecte": m.group(0)})

    if declencheurs_eleves:
        return {
            "niveau": "ELEVEE",
            "priorite": "ANALYSE_ET_ORIENTATION",
            "analyse_longue_autorisee": True,
            "declencheurs": declencheurs_eleves,
            "consigne": (
                "Analyser avec diligence et signaler toute échéance vérifiée. "
                "Recommander une intervention humaine si un délai est en jeu."
            ),
        }

    return {
        "niveau": "NORMALE",
        "priorite": "ANALYSE_ET_ORIENTATION",
        "analyse_longue_autorisee": True,
        "declencheurs": [],
        "consigne": "Traitement standard : qualification, faits, vérification, analyse, orientations.",
    }
