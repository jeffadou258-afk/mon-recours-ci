# État documenté des sources

> Fichier **généré** par `python3 bin/rapport_sources.py`. Toute valeur ci-dessous
> est calculée sur la base `KNOWLEDGE/corpus_juridique.sqlite3` au moment de
> l'exécution. **Aucune validation juridique humaine n'a eu lieu.**

## 1. Chiffres mesurés

| Indicateur | Valeur |
|---|---|
| Documents | 26 |
| Articles indexés | 1777 |
| Intégrité | `INTEGRE` |
| Fiches cataloguées | 13 |
| Documents non citables | 3 |
| Articles non citables (conservés pour audit) | 179 |

### Provenance du texte

| Origine | Articles |
|---|---|
| `CALQUE_TEXTE` | 1111 |
| `OCR_AUTO` | 666 |
| `VERIFIE_MANUELLEMENT` | 0 |

**Aucun article n'a été relu manuellement.** Tous les articles sont donc
d'origine automatique (calque texte du PDF, ou OCR).

## 2. Textes fiables et textes à vérifier

« Fiable » signifie ici : **extrait d'un document officiel identifié par son
empreinte SHA-256**. Cela ne signifie pas « relu par un juriste ».

| Texte | Domaine | Origine | Articles | Qualité |
|---|---|---|---|---|
| sans numéro — ACTE UNIFORME PORTANT ORGANISATION DES SURETES (OHAD | `contrats_dettes_commerce` | CALQUE_TEXTE | 228 | citable |
| 2013-450 — LOI N° 2013-450 DU 19 JUIN 2013 RELATIVE A LA PROTEC | `donnees_personnelles_numerique` | OCR_VISION_AUTO | 53 | **non citable** · texte OCR (non recoupé : qualité mesurée structurelleme… |
| 2013-451 — LOI N° 2013-451 DU 19 JUIN 2013 RELATIVE A LA LUTTE  | `donnees_personnelles_numerique` | OCR_VISION_AUTO | 78 | **non citable** · texte OCR (non recoupé : qualité mesurée structurelleme… |
| 2013-546 — LOI N° 2013-546 DU 30 JUILLET 2013 RELATIVE AUX TRAN | `donnees_personnelles_numerique` | OCR_VISION_AUTO | 48 | **non citable** · texte OCR (non recoupé : qualité mesurée structurelleme… |
| sans numéro — Recueil de texte de lois adulte final 18-02-2026 | `famille_mariage_filiation` | TEXTE_DE_COMPILATION | 0 | citable |
| sans numéro — RECUEIL DES TEXTES JURIDIQUES : Protection des Droit | `famille_mariage_filiation` | TEXTE_DE_COMPILATION | 0 | citable |
| sans numéro — Décret Portant Règlementation des Familles d'Accueil | `famille_mariage_filiation` | CALQUE_TEXTE | 22 | citable |
| sans numéro — LOI RELATIVE A L’ADOPTION | `famille_mariage_filiation` | AUCUNE | 0 | citable · OCR tenté le 2026-10-17T01:18:00+00:00 — REFUSÉ : aucun… |
| sans numéro — CONVENTION SUR LA PROTECTION DES ENFANTS ET LA COOPÉ | `famille_mariage_filiation` | AUCUNE | 0 | citable · OCR tenté le 2026-10-17T01:18:00+00:00 — REFUSÉ : aucun… |
| 2015-539 — LOI No 2015-539 du 20 juillet 2015 portant Statut de | `famille_mariage_filiation` | AUCUNE | 0 | citable · OCR tenté le 2026-10-17T01:17:58+00:00 — REFUSÉ à l'ind… |
| 2018-862 — Loi n°2018-862 du 19 novembre 2018 relative à l’état | `famille_mariage_filiation` | AUCUNE | 0 | citable · OCR tenté le 2026-10-17T01:17:58+00:00 — REFUSÉ à l'ind… |
| 2018-863 — Loi n°2018-863 du 19 novembre 2018 instituant une pr | `famille_mariage_filiation` | AUCUNE | 26 | citable · texte OCR (non recoupé : qualité mesurée structurelleme… |
| 2019-571 — LOI n° 2019-571 du 26 juin 2019 relative à la filiat | `famille_mariage_filiation` | CALQUE_TEXTE | 0 | citable |
| 2019-572 — Loi n°2019-572 du 26 Juin 2019 relative à la minorit | `famille_mariage_filiation` | AUCUNE | 0 | citable · OCR tenté le 2026-10-17T01:17:58+00:00 — REFUSÉ à l'ind… |
| 2019-779 — DÉCRET No 2019-779 portant création, attributions, o | `famille_mariage_filiation` | AUCUNE | 9 | citable · texte OCR (non recoupé : qualité mesurée structurelleme… |
| 202-894 — LOI n° 202-894 du 21 décembre 2021 relative aux mesu | `famille_mariage_filiation` | AUCUNE | 16 | citable · texte OCR (non recoupé : qualité mesurée structurelleme… |
| 2020-907 — DECRET No 2020-907 DU 18 NOVEMBRE 2020 PORTANT ATTRI | `famille_mariage_filiation` | AUCUNE | 29 | citable · texte OCR (non recoupé : qualité mesurée structurelleme… |
| 2023-89 — DECRET No 2023-89 DU 15 FEVRIER 2023 FIXANT LES NORM | `famille_mariage_filiation` | AUCUNE | 68 | citable · texte OCR (non recoupé : qualité mesurée structurelleme… |
| 2023-90 — DECRET No 2023-90 DU 15 FEVRIER 2023 PORTANT REGLEME | `famille_mariage_filiation` | AUCUNE | 21 | citable · texte OCR (non recoupé : qualité mesurée structurelleme… |
| sans numéro — COMMUNIQUE DU CONSEIL DES MINISTRES DU 12 JUIN 2024  | `logement_baux_foncier` | TEXTE_NON_JURIDIQUE | 0 | citable |
| 2019-576 — LOI N° 2019-576 DU 26 JUIN 2019 INSTITUANT CODE DE L | `logement_baux_foncier` | CALQUE_TEXTE | 553 | citable |
| 2020-623 — LOI N° 2020-623 DU 14 AOUT 2020 PORTANT RATIFICATION | `logement_baux_foncier` | OCR_VISION_AUTO | 2 | citable |
| 2020-624 — LOI N° 2020-624 DU 14 AOÛT 2020 INSTITUANT CODE DE L | `logement_baux_foncier` | CALQUE_TEXTE | 302 | citable |
| 2020-624 — LOI N° 2020-624 DU 14 AOÛT 2020 INSTITUANT CODE DE L | `logement_baux_foncier` | OCR_VISION_AUTO | 287 | citable |
| 98-750 — LOI N° 98-750 DU 23 DECEMBRE 1998 RELATIVE AU DOMAIN | `logement_baux_foncier` | OCR_VISION_AUTO | 29 | citable |
| 2013-711 — DECRET N° 2013-711 DU 18 OCTOBRE 2013 PORTANT INTERD | `transport_responsabilite_civile` | CALQUE_TEXTE | 6 | citable |

## 3. Documents neutralisés (non citables)

Motif : l'OCR d'un Journal officiel a **entremêlé plusieurs actes sur la
même page** (l'article 1 citait une nomination et un autre décret). Les
articles sont **conservés** pour l'audit mais exclus de la recherche et de
la citation. Aucune méthode de correction suffisante n'est disponible.

| Document | Numéro | Articles neutralisés |
|---|---|---|
| REF-0F238AF26A8A — LOI N° 2013-546 DU 30 JUILLET 2013 RELATIVE AUX  | 2013-546 | 48 |
| REF-5E19CA5DF5AD — LOI N° 2013-451 DU 19 JUIN 2013 RELATIVE A LA LU | 2013-451 | 78 |
| REF-ADF0B09E1014 — LOI N° 2013-450 DU 19 JUIN 2013 RELATIVE A LA PR | 2013-450 | 53 |

## 4. Fiches cataloguées

| Fiche | Domaine | Article | État | Origine | Recoupé |
|---|---|---|---|---|---|
| Dépôt de garantie (caution) | `logement_baux_foncier` | 2019-576 art. 416 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Avance sur loyers | `logement_baux_foncier` | 2019-576 art. 415 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Révision du loyer | `logement_baux_foncier` | 2019-576 art. 423 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Forme du bail d'habitation | `logement_baux_foncier` | 2019-576 art. 414 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Congé donné par le bailleur | `logement_baux_foncier` | 2019-576 art. 440 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Demande de résiliation | `logement_baux_foncier` | 2019-576 art. 443 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Expulsion forcée | `logement_baux_foncier` | 2019-576 art. 445 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Domaine public urbain | `logement_baux_foncier` | 2020-624 art. 181 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Expropriation | `logement_baux_foncier` | 2020-624 art. 238 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Aménagement foncier | `logement_baux_foncier` | 2020-624 art. 69 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Téléphone au volant | `transport_responsabilite_civile` | 2013-711 art. 2 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Définition de la sûreté (OHADA) | `contrats_dettes_commerce` | — art. 1 | `VERIFIE` | `CALQUE_TEXTE` | non |
| Sûretés personnelles et cautionnement (OHADA) | `contrats_dettes_commerce` | — art. 4 | `VERIFIE` | `CALQUE_TEXTE` | non |

## 5. Domaines

| Domaine | Statut technique | Complétude juridique |
|---|---|---|
| `logement_baux_foncier` | `TERMINE_TECHNIQUEMENT` | `INCOMPLET` |
| `travail` | `BLOQUE_SOURCE` | `INCONNU` |
| `famille_mariage_filiation` | `CORPUS_PARTIEL` | `INCOMPLET` |
| `contrats_dettes_commerce` | `TERMINE_TECHNIQUEMENT` | `INCOMPLET` |
| `penal_procedure_penale` | `BLOQUE_SOURCE` | `INCONNU` |
| `consommation` | `BLOQUE_SOURCE` | `INCONNU` |
| `associations_organisations_religieuses` | `BLOQUE_SOURCE` | `INCONNU` |
| `donnees_personnelles_numerique` | `CORPUS_PARTIEL` | `INCOMPLET` |
| `administratif_voies_de_recours` | `BLOQUE_SOURCE` | `INCONNU` |
| `transport_responsabilite_civile` | `TERMINE_TECHNIQUEMENT` | `INCOMPLET` |
| `sante_droits_usagers` | `BLOQUE_SOURCE` | `INCONNU` |

Un statut `TERMINE_TECHNIQUEMENT` signifie : les textes sont intégrés et
interrogeables. Il ne signifie **pas** que le domaine est couvert en droit.

## 6. Textes manquants ou inaccessibles

| Texte | Situation | Cause |
|---|---|---|
| Loi n° 2025-221 (contentieux du bail, expulsions) | **non intégrée** | aucun exemplaire sur `*.gouv.ci` ; `civlii.laws.africa` → 404 |
| Journal officiel en ligne (`jorci.oneci.ci`) | inaccessible | HTTP 503 (maintenance) à chaque tentative |
| `sgg.gouv.ci/jo.php` | inaccessible | mur d'authentification — non contourné |
| `biblio.cndj.ci` | inaccessible | accès payant — non contourné |
| Décret 2013-225 (copropriété) et modificatif 2014-26 | non intégré | aucun exemplaire officiel téléchargeable trouvé |
| Lois 2019-868, décret 2024-850, ordonnance 2025-85 | non intégrés | non trouvés sur les sources officielles accessibles |

Journal détaillé de la recherche : `KNOWLEDGE/05_LACUNE_LOI_2025_221.md`.

## 7. Références ambiguës (non corrigées faute de source)

- **FAMILLE_ENFANTS** (`loi_n_202_894_du_21_d_cembre_2021_relative_aux_m`) : Numero tel que publie par la source : « 202-894 ». Il est douteux (les lois de 2021 sont numerotees 2021-xxx) et n'a PAS ete corrige : aucun exemplaire du Journal officiel n'a permis de trancher.
- **FAMILLE_ENFANTS** (`d_cret_portant_r_glementation_des_familles_d_acc`) : Probable seconde publication du decret n° 2023-90 : document distinct (empreinte differente) mais contenu annonce identique. A verifier avant de le citer comme un texte autonome.
- **FAMILLE_ENFANTS** (`d_cret_portant_r_glementation_des_familles_d_acc`) : Copie Laws.Africa : les pieds de page de l'editeur tombaient DANS le corps des articles (vérifié sur l'article 4). Retirés du texte indexé, conservés dans les métadonnées du document.
- **FAMILLE_ENFANTS** (`loi_relative_a_l_adoption`) : Texte publie sans numero : le numero n'est pas devine.
- **TRANSPORT** (`decret_2013_711_telephone_conduite`) : Ecart entre le nom de fichier de la source et le numero lu dans le document (711 contre 791, 18 octobre contre 20 novembre). Non tranche : aucun autre exemplaire.

Une référence ambiguë **n'est pas devinée** : elle reste signalée jusqu'à ce
qu'un exemplaire du Journal officiel permette de trancher.

## 8. Vérifications humaines requises

1. Relire un échantillon d'articles par domaine — seul chemin vers
   `VERIFIE_MANUELLEMENT`, et donc vers le statut `TERMINE_ET_VERIFIE` que le
   code refuse aujourd'hui d'attribuer.
2. Trancher la référence « 2013-711 » (nom de fichier « 791 »).
3. Confirmer les 10 fiches du domaine logement, qui engagent la réponse.
4. Décider du sort des articles neutralisés : re-OCR page par page, ou
   exclusion définitive.
5. Obtenir la loi 2025-221 auprès d'une source officielle (SGG ou CNDJ).

