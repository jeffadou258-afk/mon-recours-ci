# Étape 5 — Plan d'action et suivi

Modules : `core/plan_action.py`, `core/documents.py`, `core/evidence.py`

## But

Proposer des étapes concrètes, préparer les documents nécessaires, identifier
les interlocuteurs compétents, et **indiquer les conditions justifiant une
intervention humaine**.

## Nature de chaque étape — déclarée, jamais implicite

| Nature | Signification |
|---|---|
| `automatisable` | l'agent peut la préparer seul |
| `manuel` | l'utilisateur doit agir (aucun automate : c'est une absence **déclarée**) |
| `orientation_humaine` | un professionnel ou un service doit intervenir |

## Plan type

1. Mettre les pièces en sécurité (automatisable) — copie, aucune modification.
2. *Si urgence critique* : assurer la sécurité avant toute démarche (orientation).
3. Réunir les informations manquantes (manuel) — liste issue de l'étape 2.
4. Vérifier chaque référence utilisée (automatisable).
5. *Si brouillons préparés* : les valider avant tout envoi (orientation).
6. Saisir l'interlocuteur compétent (manuel) + conserver la preuve de dépôt.
7. Conserver une trace de chaque échange (manuel).

Aucun délai, aucune sanction, aucune procédure n'est mentionné dans le plan :
ce sont des affirmations juridiques, et elles ne peuvent venir que d'une
référence vérifiée.

## Verrous humains (human gate)

Dix motifs typés (`plan_action.MOTIFS_VERROU`) : urgence critique, risque de
perte de droits, procédure judiciaire, violence ou menace, personne vulnérable,
sources contradictoires, expertise nécessaire, action engageante, risque
d'erreur sérieux, permission manquante.

**Un verrou ne se ferme jamais tout seul.** `HumanGate` naît `OUVERT`. Seule
`fermer_par_decision_humaine(decision, marqueur_humain, commentaire)` le ferme,
et elle exige un marqueur humain non vide : sans lui, exception, verrou
toujours ouvert.

Trois issues possibles : `autorise`, `refuse`, `revision_demandee` (statut
distinct).

Tant qu'un verrou est ouvert, `actions_externes_autorisees(plan)` retourne
`False` avec les motifs : aucun envoi, aucune procédure, aucun dépôt.

## Documents

`core.documents` produit des **brouillons** : en-tête « BROUILLON — NON ENVOYÉ »,
mention de non-représentation, contrôle anti-promesse avant écriture, champ non
fourni rendu **visible** (`[À COMPLÉTER : …]`).

Il n'existe **aucune fonction d'envoi** — absence vérifiée par un test qui lit
le fichier source.

## Traçabilité

`core/evidence` produit `DOSSIERS/<dossier_id>/DOSSIER_TRACABILITE.json` avec
les champs de la spécification §16, plus `champs_non_renseignes` : la liste
nommée de ce qui n'a pas pu être renseigné.

## Critère de réussite

Le plan est lisible, chaque étape porte sa nature et son interlocuteur, les
verrous requis sont listés avec leur motif, et aucun document n'a été envoyé.
