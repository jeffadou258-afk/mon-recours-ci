# Étape 1 — Accueil et qualification

Module : `core/qualification.py` (`qualifier`), `core/urgence.py` (`detecter`)

## But

Comprendre la demande, situer le domaine, et **détecter immédiatement les
urgences** — avant toute analyse.

## Entrée

Le récit de l'utilisateur (texte libre), éventuellement des éléments déjà connus.

## Sortie

| Champ | Nature |
|---|---|
| `domaines_probables` | jusqu'à 3 domaines, par score de mots-clés |
| `scores_domaines` | mots détectés par domaine (traçable) |
| `nature_demande` | comprendre / préparer / connaître ses droits / vérifier / suivre / conflit |
| `urgence` | `CRITIQUE` / `ELEVEE` / `NORMALE` + déclencheurs cités |
| `ambiguite_domaine` | vrai si aucun domaine ou deux domaines à égalité |

## Règle de priorité

Si `urgence.niveau == "CRITIQUE"` : `analyse_longue_autorisee = False`. La
sécurité et l'orientation passent avant l'analyse. Aucune analyse ne doit
retarder cette orientation.

## Ce que cette étape ne fait jamais

- Elle ne dit pas ce que dit la loi.
- Elle ne prononce aucune qualification juridique : les domaines sont des
  **pistes de routage**, et la sortie le dit explicitement (`note`).
- Elle ne conclut pas qu'une situation est urgente « un peu » : trois niveaux,
  pas de dégradé implicite.

## Critère de réussite

Un domaine est retenu, l'urgence est positionnée avec ses déclencheurs cités
tels quels, et un cas critique porte `priorite = SECURITE_ET_ORIENTATION`.

## Piège connu et corrigé

La détection de menace a d'abord refusé **les victimes** (« mon mari menace de
me tuer »). Les motifs `MENACE` et `VIOLENCE` exigent maintenant un marqueur de
demande (aide, écris, rédige, je veux…) qui précède l'acte demandé. Décrire une
menace n'est pas demander une menace. Voir `tests/test_garde_fous.py`
(les témoins légitimes).
