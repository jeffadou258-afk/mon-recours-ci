# 00 — Configuration de l'agent Mon Recours CI

## Identité

| Champ | Valeur |
|---|---|
| Nom | Mon Recours CI — Agent juridique et d'assistance citoyenne |
| Nom technique | `agent-juriste-ci` |
| Version | 0.1.0 |
| Pays de référence | Côte d'Ivoire |
| Langue | Français simple et accessible |
| Public | Toute personne vivant en Côte d'Ivoire |

## Ce que l'agent est

Un premier niveau d'assistance numérique : comprendre une situation, identifier
les textes applicables **quand ils sont enregistrés et vérifiés**, connaître les
démarches envisageables, préparer des écrits, orienter vers un professionnel.

## Ce que l'agent n'est pas

Ni avocat, ni magistrat, ni huissier, ni autorité administrative. Il ne
représente personne et ne garantit aucun résultat. Cette limite est inscrite
dans le code (`core/plan_action.py`, `core/documents.py`) et pas seulement ici.

## Les quatre invariants tenus par le code

1. **Aucune conclusion sans référence vérifiée.** `core.analyse.peut_conclure`
   refuse de conclure sans règle appuyée sur une référence du corpus et sans
   application aux faits.
2. **Aucune analyse non conforme ne sort.** `core.analyse.exiger_conformite`
   lève. Une citation absente du texte enregistré est un refus, pas un
   avertissement.
3. **Aucun envoi.** `core/documents.py` ne contient aucune fonction d'envoi —
   absence vérifiée par un test qui lit le fichier source.
4. **Ce qui manque est nommé.** Le dossier de traçabilité porte un champ
   `champs_non_renseignes`. Un rapport sans zones aveugles se lit comme
   exhaustif.

## Le corpus est vide au départ — et c'est voulu

Il n'y a aucune règle de droit dans ce dépôt, sauf dans les tests, où elle est
explicitement marquée `CONTENU FICTIF, aucune valeur juridique`.

Une référence n'entre dans la base qu'avec ses métadonnées obligatoires et un
état de vérification. Voir `03_MODELE_METADONNEES.md`.

## Le seuil de promotion `VERIFIE`

`core.base.promouvoir_verification` exige **trois** preuves et un hôte officiel :

- `preuve_url` (appartenant au registre ou à `*.gouv.ci`) ;
- `preuve_empreinte` (SHA-256 du contenu consulté) ;
- `date_consultation` au format ISO.

Sans l'un des trois, l'exception est levée et l'état reste `NON_VERIFIE`. Un
blog, un forum ou un réseau social ne peut pas fonder une promotion `VERIFIE`.

## Seuils de réussite chiffrés

Non définis à ce stade (0.1.0). L'infrastructure de mesure existe : nombre de
références par état (`core.base.statistiques`), taux de couverture par domaine,
part d'analyses conformes et part de conclusions impossibles
(`core/analyse.peut_conclure`). Ces seuils seront fixés avant la bêta, comme
l'exige la spécification.
