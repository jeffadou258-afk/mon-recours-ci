# Étape 2 — Collecte des faits

Modules : `core/qualification.py` (`questions_a_poser`), `core/faits.py` (`Faits`)

## But

Poser **uniquement** les questions nécessaires, et enregistrer ce qui est
rapporté sans jamais le transformer en fait établi.

## Statuts d'un fait

| État | Signification | Preuve exigée |
|---|---|---|
| `DECLARE_PAR_L_UTILISATEUR` | récit reçu | aucune |
| `DOCUMENTE` | pièce fournie | **nom + empreinte SHA-256 calculée sur le fichier** |
| `A_CONFIRMER` | récit ambigu | une pièce trancherait |
| `MANQUANT` | information absente | aucune — et elle est **nommée** |

## Règles tenues par le code

1. **Un fait déclaré n'est jamais promu automatiquement.** `documenter()` exige
   le chemin d'une pièce qui existe réellement : `FileNotFoundError` sinon.
2. **L'empreinte est calculée, pas déclarée.** `documenter()` hache le fichier.
3. **Une information manquante ne se documente pas** : `documer()` sur un fait
   `MANQUANT` lève une `ValueError`.
4. **Une déclaration retirée n'est pas effacée** : `ecarter()` conserve la trace
   avec son motif.
5. **On ne repose pas une question déjà répondue** : `elements_connus` retire la
   question correspondante.

## Questions de base (clés)

`dates`, `ecrit`, `montants`, `demarches`, `objectif` — complétées par des
questions propres au domaine (ex. logement : `qualite`, `caution`,
`etat_des_lieux`).

## Critère de réussite

Chaque fait porte un statut explicite, aucune information manquante n'est
comblée par une supposition, et le résumé compte **tous** les états — y compris
ceux à zéro.
