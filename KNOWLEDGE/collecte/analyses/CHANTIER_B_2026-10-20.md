# Chantier B — Recherche et collecte juridique (20/10/2026)

Mesures réelles du 20 octobre 2026. Aucune source n'a été inventée, aucun accès
payant ou protégé n'a été contourné, et **aucune référence n'a changé de statut**.

## Résultat d'ensemble

| Domaine | Sources au manifeste | Téléchargements | Intégrés | Couverture avant | Couverture après |
|---|---|---|---|---|---|
| Travail | 23 | **3** (HTTP 200) | **0** | `BLOQUE_SOURCE` | `BLOQUE_SOURCE` |
| Consommation | 4 (toutes CIVLII) | 0 | 0 | `BLOQUE_SOURCE` | `BLOQUE_SOURCE` |
| Bancaire et crédit | **0** | 0 | 0 | aucune source | aucune source |

## Travail — trois copies récupérées, aucune intégrable

| Clé | Octets | SHA-256 (début) | Verdict du contrôle |
|---|---|---|---|
| `mef_code_travail_2015_532` | 1 689 360 | `548417ee…` | **QUARANTAINE** — 462 art., couverture 0,9591, « le document contient d'autres actes (2010-272, 2013-554, 2013-555, 2013-791, 2014-370, 2017-210) : segmentation requise » |
| `travail_2015_532_uvci` | 2 147 893 | `db00d96f…` | **QUARANTAINE** — 463 art., couverture 0,9614, mêmes actes étrangers détectés |
| `travail_2015_532_faolex_210897` | 6 875 176 | `0b8ea7c6…` | **QUARANTAINE** — couverture 0,3864 (découpage incomplet : 39 % des articles 1..110) |
| `travail_2015_532_faolex` | — | — | ÉCHEC HTTP 404 |
| `travail_2015_532_civlii*` (4 clés) | — | — | ÉCHEC HTTP 404 (œuvre réservée aux abonnés) |

**Cause du refus, mesurée et non supposée** : le PDF du portail `economie-ivoirienne.ci`
n'est pas le Code du travail seul, mais un **recueil de codes sectoriels**. Le
pipeline a raison de refuser : indexer ce fichier comme « Code du travail »
attribuerait des articles d'autres lois au texte 2015-532.

**Ce qu'il faudrait pour intégrer** : une segmentation par bornes de pages, comme
celle appliquée à l'AUSCGIE (`bin/indexer_segment.py`), puis une vérification de
l'en-tête de chaque segment. Ce n'est pas fait ici : la découpe demanderait de
localiser précisément le début et la fin de l'acte dans un recueil de plusieurs
centaines de pages, et une erreur de borne produirait exactement le défaut que le
contrôle vient d'éviter.

**Provenance** : `economie-ivoirienne.ci` est une **republication ministérielle**,
pas un hôte `*.gouv.ci`. Même segmenté, ce document ne pourrait donc pas être
promu `VERIFIE` — au mieux `PARTIELLEMENT_VERIFIE`, après relecture.

## Consommation — aucune source officielle identifiable

Les quatre entrées du manifeste pointent toutes vers CIVLII / Laws.Africa :

* `consommation_2016_412_civlii_source` et `_jo` : **404**, œuvre réservée aux abonnés ;
* `petits_litiges_2015_904_civlii_*` : textes **secondaires**, utilisables pour
  recoupement seulement, jamais comme source officielle.

Aucun constat nouveau. Le domaine reste `BLOQUE_SOURCE`, ce qui est exact : ce
n'est pas « le texte n'existe pas », c'est « aucun exemplaire accessible sur un
hôte officiel ».

## Bancaire et crédit — rien à collecter

**Aucune source au manifeste** pour ce domaine. Il n'existe ni texte identifié, ni
URL candidate. Chercher au hasard produirait des résultats non vérifiables ;
mieux vaut le dire que remplir un tableau.

## Ce que ce chantier n'a pas fait, volontairement

* aucune écriture en base, aucun statut promu, aucune fiche créée ;
* aucun contournement des murs CIVLII ou CNDJ ;
* aucune source secondaire présentée comme officielle ;
* aucune segmentation improvisée sur un recueil multi-actes.

## Prochaine action utile, pour un humain ou une session dédiée

1. Obtenir un exemplaire **isolé** du Code du travail 2015-532 sur `*.gouv.ci`
   (SGG, ministère du Travail) — la voie normale, non contournée ici.
2. À défaut, segmenter le recueil `economie-ivoirienne.ci` avec `bin/indexer_segment.py`,
   en vérifiant l'en-tête de chaque borne, puis intégrer en `PARTIELLEMENT_VERIFIE`.
3. Pour la consommation et le bancaire : établir la liste des textes attendus
   (loi 2016-412, textes UEMOA/BCEAO) **avant** de chercher, comme pour les 23
   entrées « travail » — l'absence de liste est la vraie cause du blocage.
