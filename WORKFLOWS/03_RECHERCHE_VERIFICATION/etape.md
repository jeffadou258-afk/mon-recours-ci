# Étape 3 — Recherche et vérification juridique

Modules : `core/sources.py`, `core/base.py`

## But

Rechercher les textes applicables dans des sources fiables, **contrôler** les
références, et identifier les incertitudes au lieu de les lisser.

## Trois niveaux distincts — à ne jamais confondre

| Niveau | Question | Outil | Ce qui est enregistré |
|---|---|---|---|
| Accessibilité | la source répond-elle ? | `sources.verifier_url` | HTTP réel, date, erreur éventuelle |
| Présence au corpus | la référence existe-t-elle ? | `base.rechercher` | `ref_id`, métadonnées, score |
| État de vérification | le texte a-t-il été lu ? | `base.promouvoir_verification` | preuve URL + empreinte + date |

Une source accessible **ne prouve pas** qu'un texte est en vigueur. C'est
pourquoi la promotion d'état est une opération distincte, manuelle, journalisée.

## Recherche dans le corpus

`base.rechercher(mots_cles)` : recherche tolérante aux accents et à la casse sur
titre, articles, type, numéro et extrait. Elle retourne un score.

**Une liste vide est une réponse**, pas un échec : elle signifie « aucune
information juridique vérifiée disponible ». L'agent le dit et n'y supplée pas
par sa mémoire.

## Promotion `VERIFIE` — trois preuves

`preuve_url` (hôte officiel obligatoire) + `preuve_empreinte` (SHA-256) +
`date_consultation` (ISO). Il en manque une : exception, état inchangé.

## Critère de réussite

Chaque référence utilisée dans une analyse porte un état de vérification connu,
sa source, sa date de consultation ; les références non vérifiées sont signalées
comme telles dans l'analyse (`INCERTITUDE_NON_DECLAREE` sinon).

## Arrêt légitime

Si une source essentielle ne peut pas être vérifiée et que la réponse en dépend :
l'agent s'arrête sur ce point, explique ce qui manque, et propose une voie sûre.
Il ne fabrique pas la réponse manquante (spec §14).
