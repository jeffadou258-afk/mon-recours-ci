# 02 — Constituer le corpus juridique

## Règle fondatrice

**Le corpus ne se remplit pas de mémoire. Il se remplit de consultation.**

Aucune référence ne peut être saisie « parce qu'on la connaît ». Chaque entrée
porte la preuve de sa consultation. C'est ce qui rend l'exactitude vérifiable.

## Procédure d'ajout d'une référence

1. **Consulter la source officielle** (voir `01_SOURCES_OFFICIELLES.md`).
   Le texte doit être lu, pas supposé.
2. **Vérifier l'accessibilité** : lancer `bin/verifier_sources.py`. Le résultat
   réel (200 / 503 / injoignable) est journalisé avec sa date.
3. **Calculer l'empreinte du contenu consulté** (SHA-256 du texte ou du PDF).
4. **Enregistrer la référence** avec ses métadonnées obligatoires :

   ```python
   from core import base
   ref_id = base.ajouter_reference(
       titre_officiel=..., type_texte=..., numero_texte=...,
       date_publication=..., articles=..., domaine=...,
       source_nom=..., source_url=..., date_consultation=...,
       extrait_texte=..., texte_complet_present=True|False,
       modifications=..., limites_interpretation=...,
   )
   ```

   `ajouter_reference` est **idempotent et non écrasant** : réenregistrer le
   même texte (même titre, même type, même numéro) renvoie la clé existante sans
   rien modifier. Une saisie naïve ne peut donc pas rétrograder une référence
   déjà vérifiée.

5. **Promouvoir l'état** uniquement avec la preuve complète :

   ```python
   base.promouvoir_verification(
       ref_id, "VERIFIE",
       preuve_url=..., preuve_empreinte="sha256:…", date_consultation="…",
       motif="consultation directe du texte",
   )
   ```

   La promotion est journalisée dans la table `verifications` (avant / après,
   preuve, motif, horodatage). Rien n'est silencieux.

## États de vérification

| État | Signification | Usage dans une analyse |
|---|---|---|
| `VERIFIE` | Texte lu, source officielle, empreinte enregistrée | utilisable |
| `PARTIELLEMENT_VERIFIE` | Source accessible, texte non confirmé en totalité | exige une incertitude déclarée |
| `NON_VERIFIE` | Référence saisie, non encore vérifiée (défaut) | exige une incertitude déclarée |
| `NON_CONFIRME` | Source injoignable ou contradictoire | exige une incertitude déclarée |
| `OBSOLETE` | Remplacement, abrogation ou modification connus | exige une incertitude déclarée |

Toute règle fondée sur une référence qui n'est pas `VERIFIE` **doit** être
accompagnée d'une incertitude qui la nomme, sinon `core.analyse.valider`
produit `INCERTITUDE_NON_DECLAREE` et l'analyse est refusée.

## Domaines à documenter (priorités de la spécification)

- Logement, baux, foncier
- Droit du travail
- Famille, mariage, séparation, filiation, obligations parentales
- Contrats, dettes, activités commerciales
- Droit pénal et procédures
- Consommation et protection des usagers
- Associations et organisations religieuses
- Données personnelles et droits numériques
- Procédures administratives et voies de recours

Les libellés machine de ces domaines sont dans `config.DOMAINES_JURIDIQUES`.

## Ce qui n'est PAS dans le corpus

- Des articles cités de mémoire.
- Des délais « généralement admis ».
- Des pratiques, coutumes ou usages présentés comme du droit.
- Des extraits de blog, de forum ou de réseau social.
- Des décisions de justice non publiées ou non accessibles.

Si une référence ne peut pas être confirmée, l'agent le dit et cherche une autre
source — il ne comble pas le vide.
