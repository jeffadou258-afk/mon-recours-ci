# Recherche prioritaire — plan du Research Agent

Document **généré** par `bin/recherche_priorites.py` depuis les lacunes déclarées dans `KNOWLEDGE/domaines_24.json`. Il ne modifie rien : ni base, ni statut.

## Règles que le Research Agent ne franchit pas

1. **Aucune écriture en base.** La collecte produit des constats ; l'intégration passe par `bin/integrer_collecte.py`, avec ses contrôles.
2. **Aucun contournement de mur.** CNDJ (`biblio.cndj.ci`) est payant, `sgg.gouv.ci/jo.php` demande une authentification : on ne les force pas.
3. **Aucune promotion de statut.** Un texte téléchargé reste `A_VERIFIER` ; `VERIFIE` exige une URL officielle, une empreinte et une date ; `VERIFIE_MANUELLEMENT` exige une relecture humaine, qui n'a pas eu lieu.
4. **Aucune source secondaire présentée comme officielle.** Une reproduction d'éditeur est signalée comme telle.

## Lot 1 — documents déjà repérés, identité ou intégration à établir

Ces domaines ont un candidat mais rien de citable : c'est le meilleur rendement par heure de travail.

| Code | Domaine | Textes repérés | Fiches servies | Lacune |
|---|---|---|---|---|
| 2 | Droit de la famille | 6 | 31 | Filiation (2019-571), mariage (2019-570) et successions (2019-573) ont des fiches ; aucune n'est relue par un juriste. ; Divorce et séparation de corps : la loi 2019-570 ne les rég |
| 5 | Droit pénal et procédure pénale | 1 | 16 | Code pénal 2019-574 (version d'origine, JO du 10/07/2019) : les modifications postérieures ne sont pas vérifiées. ; Code de procédure pénale 2018-975 : exemplaire officiel collecté |
| 23 | Droit OHADA, sûretés et voies d'exécution | 2 | 11 | Sûretés (AUS) et voies d'exécution (AUPSRVE 2023) couverts ; quotités saisissables du salaire : droit national, absentes. ; Procédures collectives (AUPCAP 2015) : texte du JO OHADA |
| 3 | Droit immobilier, foncier et logement | 2 | 7 | Loi 2025-221 (contentieux du bail, exécution des expulsions) non intégrée : la procédure d'expulsion n'est couverte que par les articles 443 et 445 du Code de la construction. ; Ba |
| 22 | Protection de l'enfant et des personnes vuln | 6 | 4 | Protection pénale de l'enfant couverte par 4 fiches (violences, privation de soins, excision, viol sur mineur de quinze ans, âge du mariage). ; Décrets 2023-89, 2023-90, 2019-779,  |
| 19 | Droit de l'environnement et de l'urbanisme | 1 | 3 | Trois fiches de définition (domaine public, expropriation, réserves foncières) sans question de clarification. ; Code de l'environnement absent ; procédure et indemnisation d'expro |
| 13 | Droit des transports et circulation routière | 1 | 1 | Une seule situation couverte (téléphone au volant, décret 2013-711, 6 articles). ; Code de la route, accidents et indemnisation : absents. ; Aucune question de clarification pour l |
| 6 | Droit commercial et droit des affaires | 2 | 0 | Coopératives (AUCOOP 2010, JO OHADA n° 23) : 365 articles intégrés par OCR (couverture 92 %, deux lectures tesseract), aucune fiche ; relecture humaine nécessaire. ; Procédures col |
| 14 | Droit du numérique et données personnelles | 3 | 0 | Lois 2013-450, 2013-451 et 2013-546 indexées par OCR non recoupé : 179 articles neutralisés (non citables), aucune fiche. |
| 18 | Droit rural et agricole | 1 | 0 | Loi 98-750 (foncier rural) indexée par OCR non recoupé, 29 articles, aucune fiche ni relecture. |

## Lot 2 — domaines sans aucun texte identifié

| Code | Domaine | Fiches servies | Lacune |
|---|---|---|---|
| 1 | Droit civil | 0 | Aucun texte de droit civil général (Code civil, obligations, responsabilité) dans le corpus. |
| 4 | Droit du travail et droit social | 0 | Code du travail 2015-532 : aucun exemplaire sur un hôte officiel (emploi.gouv.ci refuse l'accès, CIVLII réservé aux abonnés). ; Fac-similé du JO n° 74 du 14/09/2015 (FAOLEX) analys |
| 7 | Droit de la consommation | 0 | Aucun texte de droit de la consommation. |
| 8 | Droit bancaire et crédit | 0 | Aucun texte bancaire (UEMOA, BCEAO, microfinance). |
| 9 | Droit administratif | 0 | Aucun texte de procédure administrative. |
| 10 | Droit constitutionnel et libertés fondamenta | 0 | Constitution absente du corpus. |
| 11 | Droit fiscal | 0 | Code général des impôts et lois de finances absents. |
| 12 | Droit des assurances | 0 | Code CIMA (édition 2019, 608 pages) collecté sur cima-afrique.org : hôte au registre des sources CANDIDATES (identité non établie de façon indépendante) ; non intégré. ; Le domaine |
| 15 | Droit de la santé | 0 | Aucun texte de santé ou de droits des patients. |
| 16 | Droit des associations et organisations | 0 | Aucun texte sur les associations. |
| 17 | Droit de l'éducation | 0 | Aucun texte sur l'éducation. |
| 20 | Propriété intellectuelle | 0 | Accord de Bangui révisé collecté sur oapi.int (identité établie par l'annuaire de l'OMPI) ; non intégré : le domaine n'a pas de rattachement au moteur (décision de périmètre). |
| 21 | Droit des étrangers et nationalité | 0 | Code de la nationalité et textes sur le séjour absents. |
| 24 | Droit international privé et commerce intern | 0 | Aucune règle de conflit de lois ; Convention de La Haye 1993 (adoption internationale) présente mais 0 article indexé. |

## Comment exécuter un lot

```bash
# 1. vérifier l'accessibilité réelle des sources (réseau requis)
python3 bin/verifier_sources.py
# 2. télécharger, mesurer, extraire — constats seulement, pas de base
python3 bin/collecte_distante.py --cle <cle_du_manifeste>
# 3. intégrer en local, avec les garde-fous de couverture et d'hôte
python3 bin/integrer_collecte.py
# 4. mesurer ce que la recherche en tire réellement
python3 bin/mesurer_recherche.py --rapport
```

## État des références (mesuré)

| État | Nombre |
|---|---|
| `VERIFIE` | 3 |
| `PARTIELLEMENT_VERIFIE` | 26 |
| `A_VERIFIER` | 0 |
| **Total** | 29 |

Aucune de ces références n'est juridiquement validée par un humain. Voir `KNOWLEDGE/registre_validation_humaine.md`.

## Lacune connue, non résoluble automatiquement

* **Loi n° 2025-221** (contentieux du bail, exécution des expulsions) : introuvable en ligne (`civlii.laws.africa` → 404, aucun exemplaire sur `*.gouv.ci`). Voir `KNOWLEDGE/05_LACUNE_LOI_2025_221.md`. Aucune reconstitution ne doit être tentée.