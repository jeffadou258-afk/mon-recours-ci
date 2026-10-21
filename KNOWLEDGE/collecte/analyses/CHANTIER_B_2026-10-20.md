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

---

## Addendum du 20/10/2026 — bornes du Code du travail : démontrées, intégration bloquée par la provenance

### Les bornes SONT démontrables

Sonde page par page du recueil `mef_code_travail_2015_532.pdf` (519 pages, `pdftotext -layout`) :

| Page | Marqueur littéral | Interprétation |
|---|---|---|
| 3 | `2010-272` | table des matières — **à ignorer** |
| **7** | `LOI N° 2015-532 DU 20 JUILLET 2015 PORTANT CODE DU TRAVAIL` | **début de l'acte** |
| **184** | `LOI N° 2010-272 DU 30 SEPTEMBRE 2010 PORTANT INTERDICTION DE LA TRAITE ET DES PIRATERIES` | **début de l'acte suivant** |
| 428 | `2015-532` (dans une convention collective) | annexe, **hors acte** |

Le segment est donc **p. 7 → p. 183** (177 pages), encadré par deux en-têtes d'actes
explicitement imprimés. Les bornes ne sont pas devinées : elles sont lues dans le
document.

### Pourquoi l'intégration reste impossible aujourd'hui

`core.corpus.importer_document` refuse toute source hors périmètre :

```
est_hote_officiel("https://www.economie-ivoirienne.ci/…")  →  False
```

L'hôte est classé `CANDIDAT_OFFICIEL` : c'est une **republication ministérielle**,
pas un `*.gouv.ci`. Le garde-fou est volontaire et je ne l'ai pas désactivé.

**Conséquence** : même segmenté, ce fichier ne peut pas entrer dans le corpus sans
une décision explicite d'accepter `economie-ivoirienne.ci` comme source de
provenance — décision de gouvernance, pas de technique. Le pipeline est prêt
(`bin/indexer_segment.py --doc … --debut … --fin …`) ; il manque l'autorisation.

### Textes attendus, à obtenir sur un hôte officiel

**Travail** — Code du travail 2015-532 (ci-dessus) ; ordonnance 2021-902 modificative ;
décrets d'application déjà repérés (2013-554 maladies, 2013-555 organisation, 2013-791 SMIG,
2014-370 quotité cessible, 2017-210 indemnité de licenciement).

**Consommation** — loi 2016-412 du 15 juin 2016 relative à la consommation (aucun
exemplaire officiel accessible ; CIVLII en 404/paywall).

**Bancaire et crédit** — aucun texte identifié au manifeste. À établir avant toute
recherche : textes UEMOA/BCEAO applicables (réglementation bancaire, microfinance,
conditions de crédit) et textes nationaux de transposition.

Sans cette liste, chercher produirait des résultats invérifiables : c'est la cause
réelle du blocage, plus que l'absence de moteur de recherche.
