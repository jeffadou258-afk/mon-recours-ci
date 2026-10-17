# 04 — Corpus LOGEMENT, BAUX ET FONCIER : ce qui est prouvé, ce qui manque

Date de collecte : **2026-10-16 et 2026-10-17**. Tous les chiffres de ce document proviennent
de la base du projet, pas d'une estimation. Vérification d'intégrité :
`python3 -c "from core import corpus; print(corpus.verifier_integrite()['verdict'])"`
→ `INTEGRE`.

---

## 1. Documents réellement téléchargés (6 : 5 textes + 1 communiqué)

| Texte | Autorité | Pages | Lecture | Articles | SHA-256 (préfixe) |
|---|---|---|---|---|---|
| LOI n° 2019-576 du 26/06/2019 — **Code de la Construction et de l'Habitat** | DGI | 117 | calque texte (35 polices) | **553** | `fd81f7c724c073cf` |
| LOI n° 2020-624 du 14/08/2020 — **Code de l'Urbanisme et du Domaine Foncier Urbain** | Ministère de l'Urbanisme, du Logement et du Cadre de Vie | 66 | calque texte (522 polices) | **302** | `2dd1655d11d49e85` |
| LOI n° 2020-624 — même loi, exemplaire numérisé | DGI | 42 | **OCR** (macOS Vision) | **287** | `693b4007650a745d` |
| LOI n° 98-750 du 23/12/1998 — **Domaine foncier rural**, exemplaire numérisé | SGG (`photo_doc`) | 13 | **OCR** (macOS Vision) | **29** | `309fac2a8d7323e3` |
| LOI n° 2020-623 du 14/08/2020 — **ratification de l'ordonnance n° 2020-386** (suspension des expulsions, covid-19) | Ministère de l'Urbanisme, du Logement et du Cadre de Vie | 2 | **OCR** (macOS Vision) | **2** | — |
| *Communiqué du Conseil des ministres du 12/06/2024* — **document NON juridique** | Porte-parolat du Gouvernement | 15 | calque texte | 0 (aucune) | `6ca6225e07bcdf6f` |

**1 173 articles** sont indexés et recherchables, chacun rattaché à son document et
à sa référence (`articles_corpus` porte une clé étrangère vers les deux, plus
l'empreinte SHA-256 de son texte).

Répartition par provenance : **855 `CALQUE_TEXTE`** (lecture de document),
**318 `OCR_AUTO`** (reconnaissance automatique), **0 `VERIFIE_MANUELLEMENT`**.

Le communiqué n'est **pas** un texte de droit : il n'a **aucune référence
juridique**, aucun article, et son `methode_extraction` est `TEXTE_NON_JURIDIQUE`.
Il documente le contexte (voir §4), il ne dit pas le droit applicable.

URL d'origine :

- `https://www.dgi.gouv.ci/assets/documents/transfert_propriete/lois_reglements/LOI N° 2019-576 DU 26 JUIN 2019 INSTITUANT CODE DE LA CONSTRUCTION ET DE L'HABITAT.pdf`
- `https://www.construction.gouv.ci/uploads/publications/178542377022.pdf`
- `https://www.dgi.gouv.ci/assets/documents/transfert_propriete/lois_reglements/LOI INSTITUANT CODE URBANISME ET DOMAINE FONCIER URBAIN-4-45.pdf`
- `https://www.sgg.gouv.ci/photo_doc/1339597849.pdf`
- `https://construction.gouv.ci/uploads/publications/178542265442.pdf`
- `https://communication.gouv.ci/uploads/publications/17204739632.pdf`

Toutes les sources sont sur un domaine `*.gouv.ci` — le périmètre est vérifié par
`core.sources.est_hote_officiel`, pas déclaré à la main.

## 2. Les scans : lus par OCR, mais jamais assimilés à une lecture humaine

Les trois exemplaires numérisés sont **accessibles et intégralement conservés**,
et leurs PDF d'origine portent toujours `calque_texte = 0` : **l'OCR n'a pas
transformé un scan en document à calque texte**. Le texte reconnu est conservé à
part (`.ocr.txt`) avec sa propre empreinte SHA-256.

Ce que l'OCR a produit, et sous quelles conditions :

| Document | Articles | Recoupé avec | Qualité mesurée |
|---|---|---|---|
| LOI 2020-624, exemplaire DGI | 287 | l'autre exemplaire officiel (302 art.) | **0,9792** de similarité moyenne · médiane **1,0000** · minimale **0,7947** · **99,7 %** ≥ 0,80 · **95,0 %** de couverture |
| LOI 98-750 (foncier rural) | 29 | *aucune copie de référence* | non mesurable — contrôle structurel seulement |
| LOI 2020-623 (ratification) | 2 | *aucune copie de référence* | non mesurable — contrôle structurel seulement |

Trois garde-fous, tous testés :

1. **Un article OCR sous le seuil de qualité est écarté, pas indexé.** Seuil
   `QUALITE_MINIMALE = 0,80`.
2. **Un article non recoupé oblige à déclarer une incertitude.** Refus
   `PROVENANCE_OCR_NON_DECLAREE` si l'analyse s'appuie dessus sans la nommer.
3. **Les deux documents sans copie de référence ne sont jamais marqués
   `VERIFIE`.** Ils restent en `PARTIELLEMENT_VERIFIE` avec
   `texte_complet_present = 0`.

Un article OCR sous le seuil n'est pas « perdu » : il est listé dans les articles
écartés du rapport d'OCR, avec son motif.

> **`VERIFIE_MANUELLEMENT` = 0.** Aucun article n'a été relu par un humain. Un
> test verrouille ce zéro : il ne peut pas devenir un affichage flatteur sans
> qu'un travail humain réel ait eu lieu.

## 3. Textes identifiés mais non accessibles

| Texte | Obstacle constaté | Statut |
|---|---|---|
| Journaux officiels (`jorci.oneci.ci`) | **HTTP 503 — « Maintenance en cours »** ; ONECI annonce un retour | non accessible |
| Journal Officiel (`sgg.gouv.ci/jo.php`) | **derrière un identifiant** ; le SGG précise que seule la version originale en ses locaux a valeur probante et renvoie à un « code de téléchargement » | non accessible |
| Codes et recueils (`biblio.cndj.ci/search/codes/<id>`) | les pages de détail **redirigent vers un mur de connexion** ; l'accès est payant (**10 000 FCFA/an** étudiant, 10 000 FCFA/mois Express) | non accessible librement |
| `web.construction.gouv.ci` | **DNS non résolvable** depuis ce poste | injoignable |
| Répertoire DGI `lois_reglements/` | renvoie une page XML « **ACCES INTERDIT** » au lieu d'un index | non énumérable |

**Aucune authentification n'a été forcée, aucun paywall contourné.** Les seuls
documents entrés sont ceux qui se téléchargent librement sur un domaine public.

## 4. Références dont la validité actuelle reste à confirmer

- **Loi n° 2025-221 du 28 mars 2025** « déterminant les procédures applicables au
  contentieux relatif au bail à usage d'habitation et à l'exécution des décisions
  d'expulsion d'un immeuble ». Trouvée sur des sources **non officielles**
  (cabinets d'avocats, `loidici.biz`, plateformes de documents). **Aucun
  exemplaire sur un domaine `*.gouv.ci` n'a été localisé** — pas même sur
  `construction.gouv.ci/textes-de-loi/`, qui a pourtant fourni la loi 2020-623.
  Elle n'est donc PAS dans le corpus : c'est la lacune la plus significative du
  domaine. **Le journal complet des recherches menées (URL appelées, codes HTTP,
  obstacles) est conservé dans `KNOWLEDGE/05_LACUNE_LOI_2025_221.md`.**
  Ce qui **est** établi par une source officielle : le communiqué du Conseil des
  ministres du **12 juin 2024** annonce un projet de loi sur ce sujet
  (contentieux du bail, exécution des expulsions par les commissaires de justice,
  bail professionnel, bail emphytéotique industriel) — **sans numéro de texte**,
  donc sans valeur de droit applicable. Il est enregistré comme
  `TEXTE_NON_JURIDIQUE` et ne peut pas être cité comme une règle.
- **Décret n° 2013-225 du 22 mars 2013** (statut de la copropriété), **modifié par
  le décret n° 2014-26 du 22 janvier 2014** : connu par la mention qu'en fait
  l'article 552 du Code, mais le texte lui-même n'a pas été téléchargé.
- **Loi n° 2019-868 du 14 octobre 2019** (modifiant la loi 98-750 sur le foncier
  rural), **décret n° 2024-850 du 30 septembre 2024**, **ordonnance n° 2025-85 du
  12 février 2025** (SIFOR-CI) : identifiés par des sources secondaires, non
  vérifiés sur source officielle.
- **État de vigueur des textes collectés** : il est vérifié **à la date de
  consultation**, pas au-delà. Un texte postérieur non publié au Journal officiel
  accessible pourrait les modifier.

## 5. Abrogations établies par lecture du texte officiel

L'**article 552** du Code de la Construction et de l'Habitat abroge expressément
« toutes les dispositions antérieures contraires », notamment :

- la loi n° 65-248 du 4 août 1965 (modifiée par la loi n° 97-523 du 4 septembre 1997) — permis de construire ;
- la loi n° 99-478 du 2 août 1999 — vente d'immeuble à construire et promotion immobilière ;
- **la loi n° 2018-575 du 13 juin 2018 relative au bail à usage d'habitation** ;
- le décret n° 79-718 du 2 octobre 1979 — agents immobiliers ;
- le décret n° 2013-225 du 22 mars 2013 — copropriété.

Conséquence pratique : **le droit du bail à usage d'habitation est désormais dans
le Code de la Construction et de l'Habitat**, sous-titre « Du bail à usage
d'habitation ». Chercher la loi de 2018 comme texte applicable est une erreur —
et l'agent peut maintenant le démontrer avec le texte, pas de mémoire.

## 6. Deux défauts d'interopérabilité trouvés ET corrigés

1. **Espaces parasites dans les références numériques.** Le texte extrait porte
   « la loi 99 -478 », « n°65 -248 ». Sans réparation, une citation contenant un
   numéro de texte était déclarée **absente** alors qu'elle était exacte.
   Correction dans `core.base.normaliser` + test de régression.
2. **Apostrophes typographiques supprimées.** « d'habitation » devenait
   « dhabitation », ce qui cassait la recherche et la citation sur les
   expressions les plus courantes du domaine. Correction + test.

## 7. Lacune de numérotation dans le document SOURCE

La loi 2020-624 indexe 302 articles sur une numérotation qui va jusqu'à 303 :
**l'article 151 est absent**. Vérification faite : la chaîne « 151 » n'apparaît
**nulle part** dans le texte extrait du PDF officiel, qui passe directement de
l'article 150 à l'article 152. La lacune est donc dans le document publié, pas
dans le parseur. Couverture réelle : **100 % de ce que le document contient**.
Un test verrouille ce constat pour qu'il soit revu si le PDF change.

## 8. Limite à connaître sur le contrôle anti-invention

`core.analyse.NOMBRE_NON_SOUTENU` compare les nombres d'un énoncé à ceux des
faits **et de la référence citée**. Quand la référence porte le texte intégral
d'une loi (290 000 caractères), ce contrôle perd de son pouvoir discriminant :
un petit nombre finit toujours par apparaître quelque part. D'où l'ajout de
`core.corpus.verifier_regle_article(ref_id, numero, énoncé)`, qui compare **au
seul texte de l'article cité**. C'est ce contrôle-là qui refuse réellement
« le plafond est de 95000 FCFA par trimestre » sur l'article 423.
