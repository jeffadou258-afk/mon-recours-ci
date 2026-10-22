# -*- coding: utf-8 -*-
"""Aiguillage : quand plusieurs procédures restent candidates, on demande au citoyen.

Pourquoi une table écrite et non une heuristique : mesuré sur les fiches réelles,
aucun signal lexical ne sépare les deux cas qui comptent.

  « Mon propriétaire veut récupérer son appartement pour y habiter »
      → 0 mot commun avec LOGEME_440, 443, 445. Pourtant une fiche le couvre.
  « Je veux déclarer la naissance de mon enfant à l'état civil »
      → 3 mots communs avec FAMILL_20 (« naissance », « civil », « enfant »).
         Pourtant AUCUNE fiche ne traite de la déclaration de naissance.

Une règle fondée sur les mots aiguillerait donc le cas non couvert et refuserait
le cas couvert. C'est l'inverse de ce qu'il faut. La distinction n'est pas dans
le texte des fiches : elle demande un jugement. Ce jugement est donc écrit ici,
une fois, en clair, signé `A_VALIDER_PAR_JURISTE` — et non deviné à chaque appel.

Ce module ne dit pas le droit. Il nomme des situations pour permettre au citoyen
de dire laquelle est la sienne. Les libellés parlent de faits, jamais de notions
juridiques qu'il devrait connaître.

Règle d'application, volontairement étroite :
  * au moins deux fiches restent candidates ;
  * TOUTES les options d'une entrée font partie des fiches candidates — sinon la
    table ne correspond pas à la situation et on ne l'utilise pas ;
  * une seule entrée s'applique ; en cas de doute, aucune.
Sans entrée applicable : pas d'aiguillage, et le comportement prudent existant
(`CONCLUSION_IMPOSSIBLE`) s'applique.
"""
import json
import os

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHEMIN = os.path.join(RACINE, "KNOWLEDGE", "aiguillage.json")

STATUT_ATTENDU = "A_VALIDER_PAR_JURISTE"


class AiguillageInvalide(Exception):
    pass


def charger(chemin=None):
    chemin = chemin or CHEMIN
    if not os.path.isfile(chemin):
        return {"statut": None, "situations": []}
    with open(chemin, encoding="utf-8") as flux:
        contenu = json.load(flux)
    if not isinstance(contenu, dict):
        raise AiguillageInvalide("la table doit être un objet")
    situations = contenu.get("situations")
    if not isinstance(situations, list):
        raise AiguillageInvalide("« situations » doit être une liste")
    for entree in situations:
        if not isinstance(entree, dict) or not entree.get("cle"):
            raise AiguillageInvalide("entrée sans clé")
        options = entree.get("options")
        if not isinstance(options, list) or len(options) < 2:
            raise AiguillageInvalide("« %s » : au moins deux options" % entree["cle"])
        for option in options:
            if not (option.get("fiche") and option.get("libelle")):
                raise AiguillageInvalide("« %s » : option sans fiche ou sans libellé" % entree["cle"])
    return contenu


def situation_pour(retenues, catalogue=None, table=None):
    """L'entrée applicable, ou None.

    `retenues` : fiches candidates (dicts du catalogue). `catalogue` : ensemble
    complet, pour vérifier que les fiches citées existent encore.
    """
    if not retenues or len(retenues) < 2:
        return None
    identifiants = {f["id"] for f in retenues}
    domaines = {f.get("domaine") for f in retenues}
    if len(domaines) != 1:
        return None
    table = table if table is not None else charger()
    for entree in table.get("situations") or []:
        fiches = [o["fiche"] for o in entree["options"]]
        if not set(fiches) <= identifiants:
            continue
        if entree.get("domaine") and entree["domaine"] not in domaines:
            continue
        if catalogue is not None:
            connues = {f["id"] for f in catalogue}
            if not set(fiches) <= connues:
                continue
        return entree
    return None


def options(entree, catalogue):
    """Options à présenter, dans l'ordre de la table, avec le titre réel de la fiche."""
    index = {f["id"]: f for f in catalogue or []}
    resultat = []
    for option in entree["options"]:
        fiche = index.get(option["fiche"])
        if fiche is None:
            continue
        resultat.append({
            "cle": option["fiche"],
            "libelle": option["libelle"],
            "titre": fiche["titre"],
            "article": fiche["article"],
            "numero_texte": fiche.get("numero_texte"),
            "etat_verification": fiche["etat_verification"],
        })
    return resultat


def choix_valide(reponse, entree):
    """La sélection du citoyen est-elle l'une des options ? (« aucune » compris.)"""
    if not isinstance(reponse, str):
        return None
    reponse = reponse.strip()
    if reponse == "aucune":
        return "aucune"
    if reponse in {o["fiche"] for o in entree["options"]}:
        return reponse
    return None
