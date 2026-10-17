# Étape 4 — Analyse et explication

Module : `core/analyse.py`

## But

Présenter ce que dit le texte, son explication en français simple, son
application possible aux faits, et les éléments qui restent à vérifier —
**avec une traçabilité vérifiée mécaniquement**.

## Les quatre natures d'énoncé — jamais mélangées

| Nature | Contenu | Exigence |
|---|---|---|
| **FAIT** | ce qui est déclaré ou documenté | statut explicite (étape 2) |
| **RÈGLE** | ce que dit un texte | `ref_id` appuyé sur le corpus |
| **ANALYSE** | application de la règle aux faits | `ref_ids` **et** `faits_ids` |
| **HYPOTHÈSE** | piste | `pour_conclure` obligatoire, statut `NON_VERIFIEE` |

## Validations refusantes

| Code | Déclencheur |
|---|---|
| `REGLE_SANS_SOURCE` | règle sans `ref_id` |
| `REF_INCONNUE` | `ref_id` absent du corpus |
| `REF_VIDE` | référence sans contenu enregistré |
| `APPLICATION_SANS_REGLE` | application sans règle, ou citant une règle non énoncée |
| `APPLICATION_SANS_FAIT` | application rattachée à aucun fait |
| `HYPOTHESE_SANS_CONDITION` | hypothèse sans « ce qu'il faudrait pour conclure » |
| `CITATION_NON_VERIFIABLE` | citation absente de l'extrait enregistré |
| `INCERTITUDE_NON_DECLAREE` | règle fondée sur une référence non `VERIFIE` |
| `NOMBRE_NON_SOUTENU` | nombre (montant, durée, quantité) absent des faits et des références |
| `DOMAINE_INDETERMINE` | aucun domaine retenu |

## Le contrôle `NOMBRE_NON_SOUTENU`

C'est le garde mécanique anti-invention le plus rentable : il ne juge pas le
sens, il compare des chiffres. Tout nombre énoncé dans une règle, une
application ou une hypothèse doit se retrouver dans les faits fournis ou dans la
référence citée. Un délai inventé (« dans les 90 jours ») est donc refusé sans
qu'il faille comprendre la phrase.

Les espaces de milliers sont neutralisées : « 250 000 FCFA » et « 250000 FCFA »
sont le même jeton.

## Conclusion

`peut_conclure(analyse)` refuse de conclure si l'analyse est refusée, ou si elle
ne porte **aucune** règle appuyée sur une référence, ou aucune application aux
faits. Les raisons sont **nommées**.

## Critère de réussite

`analyse['validite'] == "CONFORME"` **et** `peut_conclure` vrai. Une analyse ne
sort jamais vers l'utilisateur sans ces deux conditions
(`exiger_conformite` lève sinon).
