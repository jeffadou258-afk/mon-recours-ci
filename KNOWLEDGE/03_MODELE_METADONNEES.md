# 03 — Modèle de métadonnées obligatoires

Chaque référence du corpus porte les champs suivants. Ceux marqués **obligatoire**
sont contraints par le schéma SQL : l'insertion échoue sans eux, même en
contournant l'API Python.

| Champ | Obligatoire | Contrainte |
|---|---|---|
| `ref_id` | oui (dérivé) | clé déterministe : `REF-` + SHA-256(titre, type, numéro)[:12] |
| `titre_officiel` | **oui** | non vide après `trim()` |
| `type_texte` | **oui** | non vide (loi, ordonnance, décret, arrêté, code…) |
| `numero_texte` | non | entre dans la clé : deux numéros ≠ deux références |
| `date_publication` | non | ISO si connue |
| `articles` | non | articles concernés |
| `domaine` | non | l'un de `config.DOMAINES_JURIDIQUES` |
| `source_nom` | **oui** | non vide |
| `source_url` | **oui** | doit commencer par `http` |
| `date_consultation` | **oui** | ISO `AAAA-MM-JJ…` |
| `etat_verification` | oui (défaut) | `NON_VERIFIE` à la création |
| `texte_complet_present` | oui (0/1) | conditionne la vérifiabilité d'une citation |
| `extrait_texte` | non | contenu consulté, base du contrôle de citation |
| `modifications` | non | abrogations, textes complémentaires identifiés |
| `limites_interpretation` | non | réserves d'interprétation |
| `empreinte_contenu` | dérivé | SHA-256 de l'extrait enregistré |
| `cree_le`, `maj_le` | oui | horodatage UTC |

## Pourquoi `texte_complet_present` est un champ, pas un détail

`core.base.verifier_citation` refuse toute citation lorsque ce champ vaut 0 :

> « texte intégral non présent pour REF-… : une citation ne peut pas être
> vérifiée, elle doit donc être signalée comme non vérifiable »

Un extrait partiel ne permet pas d'affirmer qu'une phrase est *dans* le texte.
Le distinguer est la différence entre « je peux citer » et « je paraphrase ».

## Pourquoi la clé est dérivée et non tirée au sort

Une clé aléatoire, horodatée ou incrémentée rendrait la déduplication
impossible et le corpus non rejouable. Une clé déterministe garantit :

- deux saisies du même texte → une seule entrée ;
- deux textes différents → deux entrées ;
- l'entrée existante n'est jamais modifiée par une nouvelle saisie.

## Table `verifications` — journal d'état

Chaque changement d'état écrit une ligne : `etat_precedent`, `etat_nouveau`,
`preuve_url`, `preuve_empreinte`, `date_consultation`, `motif`, `horodatage`.
L'historique complet est reconstituable par `core.base.historique_verifications`.

## Traçabilité dans le dossier utilisateur

Le dossier de traçabilité (spec §16) n'enregistre **pas** le texte des pièces
fournies : seulement le nom du fichier, son empreinte SHA-256 et sa date. Il
porte en plus `champs_non_renseignes`, la liste nommée de ce qui manque.
