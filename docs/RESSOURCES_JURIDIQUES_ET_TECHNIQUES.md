# Ressources juridiques et techniques — Mon Recours CI

Document **généré** par `bin/rapport_ressources.py` le 2026-10-19 à partir de `KNOWLEDGE/collecte/inventaire_ressources.json`, `recoupements.json` et de la base du corpus. Ne pas modifier à la main : relancer le script.

> Télécharger un texte ne l'authentifie pas et ne prouve pas qu'il est en vigueur. « Officiel » signifie ici : publié sur un hôte officiel (registre du projet ou *.gouv.ci, ohada.org). Aucune ligne de ce document ne vaut validation juridique.

## 1. Chiffres de la collecte

| Mesure | Valeur |
|---|---|
| Entrées du manifeste | 88 |
| Documents téléchargés | 32 |
| PDF rapatriés et empreinte vérifiée | 32 |
| Pages de découverte lues | 20 |
| Échecs (HTTP, réseau, non-PDF) | 36 |
| Pas encore collectés | 0 |
| Statut de contrôle | EXPLOITABLE_OFFICIEL : 10, EXPLOITABLE_RECOUPEMENT_SEULEMENT : 5, QUARANTAINE : 17 |
| Catégorie de source | OFFICIEL_INSTITUTION : 1, OFFICIEL_ORGANISATION : 1, OFFICIEL_PORTAIL_GOUV : 24, SECONDAIRE_AUTRE : 2, SECONDAIRE_BASE_INTERNATIONALE : 2, SECONDAIRE_CONSOLIDE : 1, SECONDAIRE_FAC_SIMILE : 1 |
| Méthode d'extraction | CALQUE_TEXTE : 8, OCR_EDITEUR : 10, OCR_TESSERACT : 11, OCR_TESSERACT_PARTIEL : 3 |

## 2. Documents téléchargés

| Clé | Texte | Catégorie | Pages | Extraction | Articles (couverture) | Contrôle | Motifs / avertissements |
|---|---|---|---|---|---|---|---|
| `aupsrve_2023_jo_ohadacom` | AUPSRVE-2023 — Acte uniforme du 17 octobre 2023 portant organisation des procédures simplifiées de recouv | SECONDAIRE_FAC_SIMILE | 122 | OCR_TESSERACT_PARTIEL conf. 91.5 | 332 (98 %) | **EXPLOITABLE_RECOUPEMENT_SEULEMENT** | qpdf signale des avertissements de structure; 1 page(s) OCR de confiance < 70 : [9]; même fichier que : ohada_jo_special_aupsrve_2023 |
| `aupsrve_2023_senlii` | AUPSRVE-2023 — Acte uniforme portant organisation des procédures simplifiées de recouvrement et des voies | SECONDAIRE_CONSOLIDE | 113 | CALQUE_TEXTE | 338 (100 %) | **EXPLOITABLE_RECOUPEMENT_SEULEMENT** | — |
| `gouvci_175043233774` | ? — Document gouv.ci non identifié (175043233774.pdf) | OFFICIEL_PORTAIL_GOUV | 11 | CALQUE_TEXTE | 0 (0 %) | **QUARANTAINE** | contenu non identifié |
| `ilo_textes_pertinents_rci` | ? — Textes pertinents applicables en République de Côte d'Ivoire (compilation diffusée par l'O | SECONDAIRE_BASE_INTERNATIONALE | 96 | CALQUE_TEXTE | 54 (100 %) | **EXPLOITABLE_RECOUPEMENT_SEULEMENT** | qpdf signale des avertissements de structure |
| `mariage_2019_570_faolex` | 2019-570 — Loi n° 2019-570 du 26 juin 2019 relative au mariage | SECONDAIRE_BASE_INTERNATIONALE | 7 | OCR_EDITEUR | 105 (100 %) | **EXPLOITABLE_RECOUPEMENT_SEULEMENT** | qpdf signale des avertissements de structure |
| `mffe_adoption` | ? — Loi relative à l'adoption (document mffe.ci « adoption_enfant ») | OFFICIEL_PORTAIL_GOUV | 3 | CALQUE_TEXTE | 0 (0 %) | **QUARANTAINE** | aucun article détecté |
| `mffe_code_penal_2019_574` | 2019-574 — Loi n° 2019-574 du 26 juin 2019 portant Code pénal | OFFICIEL_PORTAIL_GOUV | 52 | OCR_EDITEUR | 541 (96 %) | **EXPLOITABLE_OFFICIEL** | — |
| `mffe_constitution_2016` | 2016-886 — Loi n° 2016-886 du 8 novembre 2016 portant Constitution de la République de Côte d'Ivoire | OFFICIEL_PORTAIL_GOUV | 16 | OCR_TESSERACT conf. 93.8 | 160 (87 %) | **EXPLOITABLE_OFFICIEL** | — |
| `mffe_cpp_2018_975` | 2018-975 — Loi n° 2018-975 du 27 décembre 2018 portant Code de procédure pénale | OFFICIEL_PORTAIL_GOUV | 64 | OCR_EDITEUR | 831 (97 %) | **EXPLOITABLE_OFFICIEL** | qpdf signale des avertissements de structure |
| `mffe_etat_civil_2018_862` | 2018-862 — Loi n° 2018-862 du 19 novembre 2018 relative à l'état civil | OFFICIEL_PORTAIL_GOUV | 10 | OCR_TESSERACT conf. 88.3 | 85 (75 %) | **QUARANTAINE** | découpage en articles incomplet : 75% des articles 1..113; 1 page(s) OCR de confiance < 70 : [2] |
| `mffe_mariage_2019_570` | 2019-570 — Loi n° 2019-570 du 26 juin 2019 relative au mariage | OFFICIEL_PORTAIL_GOUV | 7 | OCR_EDITEUR | 105 (100 %) | **EXPLOITABLE_OFFICIEL** | qpdf signale des avertissements de structure |
| `mffe_naissance_2018_863` | 2018-863 — Loi n° 2018-863 du 19 novembre 2018 instituant une procédure spéciale de déclaration de na | OFFICIEL_PORTAIL_GOUV | 5 | OCR_TESSERACT conf. 93.2 | 7 (27 %) | **QUARANTAINE** | découpage en articles incomplet : 27% des articles 1..26; qpdf signale des avertissements de structure |
| `mffe_pupille_2015_539` | 2015-539 — Loi n° 2015-539 du 20 juillet 2015 portant statut de pupille de l'État | OFFICIEL_PORTAIL_GOUV | 2 | OCR_EDITEUR | 21 (39 %) | **QUARANTAINE** | découpage en articles incomplet : 39% des articles 1..54; le numéro 2015-539 n'apparaît pas dans le texte extrait; qpdf signale des avertissements de structure |
| `mffe_successions_2019_573` | 2019-573 — Loi n° 2019-573 du 26 juin 2019 relative aux successions | OFFICIEL_PORTAIL_GOUV | 10 | OCR_EDITEUR | 120 (75 %) | **QUARANTAINE** | découpage en articles incomplet : 75% des articles 1..160; qpdf signale des avertissements de structure; même fichier que : successions_2019_573_bice |
| `mffe_traite_2016_1111` | 2016-1111 — Loi n° 2016-1111 du 8 décembre 2016 relative à la lutte contre la traite des personnes | OFFICIEL_PORTAIL_GOUV | 3 | OCR_TESSERACT conf. 93.6 | 23 (85 %) | **EXPLOITABLE_OFFICIEL** | — |
| `officiel_famille_convention_sur_la_protection_des_enfants_et_la_c` | ? — CONVENTION SUR LA PROTECTION DES ENFANTS ET LA COOPÉRATION EN MATIÈRE D’ADOPTION INTERNATI | OFFICIEL_PORTAIL_GOUV | 10 | CALQUE_TEXTE | 48 (100 %) | **EXPLOITABLE_OFFICIEL** | qpdf signale des avertissements de structure |
| `officiel_famille_d_cret_no_2019_779_portant_cr_ation_attributions` | 2019-779 — DÉCRET No 2019-779 portant création, attributions, organisation et fonctionnement du comit | OFFICIEL_PORTAIL_GOUV | 3 | OCR_TESSERACT conf. 93.7 | 9 (100 %) | **EXPLOITABLE_OFFICIEL** | — |
| `officiel_famille_d_cret_portant_r_glementation_des_familles_d_acc` | ? — Décret Portant Règlementation des Familles d'Accueil, 2023 (Décret 90 de 2023) | OFFICIEL_PORTAIL_GOUV | 7 | CALQUE_TEXTE | 22 (100 %) | **QUARANTAINE** | déclaré officiel mais porte des marques d'éditeur tiers : creative commons, laws.africa |
| `officiel_famille_decret_no_2020_907_du_18_novembre_2020_portant_a` | 2020-907 — DECRET No 2020-907 DU 18 NOVEMBRE 2020 PORTANT ATTRIBUTIONS, ORGANISATION ET FONCTIONNEMEN | OFFICIEL_PORTAIL_GOUV | 8 | OCR_TESSERACT conf. 92.8 | 15 (54 %) | **QUARANTAINE** | découpage en articles incomplet : 54% des articles 1..28 |
| `officiel_famille_decret_no_2023_89_du_15_fevrier_2023_fixant_les_` | 2023-89 — DECRET No 2023-89 DU 15 FEVRIER 2023 FIXANT LES NORMES ET STANDARDS APPLICABLES AUX ETABLI | OFFICIEL_PORTAIL_GOUV | 16 | OCR_TESSERACT conf. 91.6 | 60 (85 %) | **QUARANTAINE** | découpage en articles incomplet : 85% des articles 1..71 |
| `officiel_famille_decret_no_2023_90_du_15_fevrier_2023_portant_reg` | 2023-90 — DECRET No 2023-90 DU 15 FEVRIER 2023 PORTANT REGLEMENTATION DES FAMILLES D'ACCUEIL | OFFICIEL_PORTAIL_GOUV | 5 | OCR_TESSERACT conf. 90.6 | 22 (100 %) | **EXPLOITABLE_OFFICIEL** | — |
| `officiel_famille_loi_n_2018_862_du_19_novembre_2018_relative_l_ta` | 2018-862 — Loi n°2018-862 du 19 novembre 2018 relative à l’état civil. | OFFICIEL_PORTAIL_GOUV | 10 | OCR_TESSERACT conf. 75.3 | 13 (12 %) | **QUARANTAINE** | découpage en articles incomplet : 12% des articles 1..108; le numéro 2018-862 n'apparaît pas dans le texte extrait; 2 page(s) OCR de confiance < 70 : [1, 2] |
| `officiel_famille_loi_n_2018_863_du_19_novembre_2018_instituant_un` | 2018-863 — Loi n°2018-863 du 19 novembre 2018 instituant une procédure spéciale de déclaration de nai | OFFICIEL_PORTAIL_GOUV | 5 | OCR_TESSERACT conf. 93.2 | 12 (46 %) | **QUARANTAINE** | découpage en articles incomplet : 46% des articles 1..26 |
| `officiel_famille_loi_n_2019_571_du_26_juin_2019_relative_la_filia` | 2019-571 — LOI n° 2019-571 du 26 juin 2019 relative à la filiation | OFFICIEL_PORTAIL_GOUV | 2 | OCR_EDITEUR | 33 (31 %) | **QUARANTAINE** | découpage en articles incomplet : 31% des articles 1..105; qpdf signale des avertissements de structure |
| `officiel_famille_loi_n_2019_572_du_26_juin_2019_relative_la_minor` | 2019-572 — Loi n°2019-572 du 26 Juin 2019 relative à la minorité | OFFICIEL_PORTAIL_GOUV | 13 | OCR_TESSERACT conf. 80.4 | 20 (13 %) | **QUARANTAINE** | découpage en articles incomplet : 13% des articles 1..149; 2 page(s) OCR de confiance < 70 : [1, 9] |
| `officiel_famille_loi_n_202_894_du_21_d_cembre_2021_relative_aux_m` | 202-894 — LOI n° 202-894 du 21 décembre 2021 relative aux mesures de protection des victimes de viol | OFFICIEL_PORTAIL_GOUV | 3 | OCR_EDITEUR | 17 (65 %) | **QUARANTAINE** | découpage en articles incomplet : 65% des articles 1..16; le numéro 202-894 n'apparaît pas dans le texte extrait; qpdf signale des avertissements de structure |
| `officiel_famille_loi_no_2015_539_du_20_juillet_2015_portant_statu` | 2015-539 — LOI No 2015-539 du 20 juillet 2015 portant Statut de pupille de l’Etat | OFFICIEL_PORTAIL_GOUV | 2 | OCR_EDITEUR | 21 (39 %) | **QUARANTAINE** | découpage en articles incomplet : 39% des articles 1..54; le numéro 2015-539 n'apparaît pas dans le texte extrait; qpdf signale des avertissements de structure |
| `officiel_famille_loi_relative_a_l_adoption` | ? — LOI RELATIVE A L’ADOPTION | OFFICIEL_PORTAIL_GOUV | 8 | CALQUE_TEXTE | 37 (100 %) | **EXPLOITABLE_OFFICIEL** | qpdf signale des avertissements de structure |
| `ohada_jo_special_aupsrve_2023` | AUPSRVE-2023 — Journal officiel de l'OHADA, numéro spécial du 15 novembre 2023 — Acte uniforme du 17 octo | OFFICIEL_ORGANISATION | 122 | OCR_TESSERACT_PARTIEL conf. 92.0 | 331 (98 %) | **EXPLOITABLE_OFFICIEL** | qpdf signale des avertissements de structure; même fichier que : aupsrve_2023_jo_ohadacom |
| `successions_2019_573_assnat` | 2019-573 — Loi relative aux successions (document de l'Assemblée nationale) | OFFICIEL_INSTITUTION | 23 | CALQUE_TEXTE | 135 (100 %) | **QUARANTAINE** | le numéro 2019-573 n'apparaît pas dans le texte extrait |
| `successions_2019_573_bice` | 2019-573 — Loi n° 2019-573 relative aux successions (document diffusé par le BICE) | SECONDAIRE_AUTRE | 10 | OCR_EDITEUR | 120 (75 %) | **QUARANTAINE** | découpage en articles incomplet : 75% des articles 1..160; qpdf signale des avertissements de structure; même fichier que : mffe_successions_2019_573 |
| `travail_2015_532_uvci` | 2015-532 — Le Code du travail ivoirien (document diffusé par l'UVCI) | SECONDAIRE_AUTRE | 563 | OCR_TESSERACT_PARTIEL conf. 89.3 | 463 (96 %) | **EXPLOITABLE_RECOUPEMENT_SEULEMENT** | 1 page(s) OCR de confiance < 70 : [202] |

Provenance complète (URL, URL finale, date de récupération, SHA-256, taille, version PDF) : `KNOWLEDGE/collecte/inventaire_ressources.json` et `KNOWLEDGE/collecte/resultats/<clé>.json`. PDF bruts : branche `corpus/archives-pdf` (fichier `SHA256SUMS`).

## 3. Recoupements entre lectures d'un même texte

| Texte | Lecture A | Lecture B | Articles communs | Similarité moyenne | Divergents (< 0,80) |
|---|---|---|---|---|---|
| 2015-539 | `mffe_pupille_2015_539` | `officiel_famille_loi_no_2015_539_du_20_juillet_2015_portant_statu` | 21 | 1.0 | 0 |
| 2016-1111 | `corpus:DOC-9213FE7D7C3F` | `mffe_traite_2016_1111` | 23 | 1.0 | 0 |
| 2016-886 | `corpus:DOC-B1897A009D35` | `mffe_constitution_2016` | 160 | 1.0 | 0 |
| 2018-862 | `mffe_etat_civil_2018_862` | `officiel_famille_loi_n_2018_862_du_19_novembre_2018_relative_l_ta` | 12 | 0.4585 | 9 |
| 2018-863 | `corpus:DOC-AC714CEB4E83` | `mffe_naissance_2018_863` | 7 | 0.5655 | 5 |
| 2018-863 | `corpus:DOC-AC714CEB4E83` | `officiel_famille_loi_n_2018_863_du_19_novembre_2018_instituant_un` | 12 | 0.8106 | 4 |
| 2018-863 | `mffe_naissance_2018_863` | `officiel_famille_loi_n_2018_863_du_19_novembre_2018_instituant_un` | 7 | 0.8838 | 1 |
| 2019-570 | `mariage_2019_570_faolex` | `mffe_mariage_2019_570` | 105 | 1.0 | 0 |
| 2019-571 | `corpus:DOC-B722D1F51881` | `officiel_famille_loi_n_2019_571_du_26_juin_2019_relative_la_filia` | 30 | 0.9235 | 3 |
| 2019-573 | `mffe_successions_2019_573` | `successions_2019_573_assnat` | 114 | 0.6522 | 80 |
| 2019-573 | `mffe_successions_2019_573` | `successions_2019_573_bice` | 120 | 1.0 | 0 |
| 2019-573 | `successions_2019_573_assnat` | `successions_2019_573_bice` | 114 | 0.651 | 80 |
| 2019-779 | `corpus:DOC-D754ACEE8E29` | `officiel_famille_d_cret_no_2019_779_portant_cr_ation_attributions` | 9 | 0.9925 | 0 |
| 202-894 | `corpus:DOC-3C674637A31E` | `officiel_famille_loi_n_202_894_du_21_d_cembre_2021_relative_aux_m` | 15 | 0.5993 | 12 |
| 2020-907 | `corpus:DOC-F9B2C53EB909` | `officiel_famille_decret_no_2020_907_du_18_novembre_2020_portant_a` | 15 | 0.7791 | 5 |
| 2023-89 | `corpus:DOC-DAFFEFDC4B7D` | `officiel_famille_decret_no_2023_89_du_15_fevrier_2023_fixant_les_` | 59 | 0.9303 | 7 |
| 2023-90 | `corpus:DOC-1EDDBBD930BF` | `officiel_famille_decret_no_2023_90_du_15_fevrier_2023_portant_reg` | 21 | 0.9718 | 1 |
| AUPSRVE-2023 | `aupsrve_2023_jo_ohadacom` | `aupsrve_2023_senlii` | 332 | 0.8987 | 41 |
| AUPSRVE-2023 | `aupsrve_2023_jo_ohadacom` | `corpus:DOC-2564CCED2D56` | 288 | 0.9961 | 0 |
| AUPSRVE-2023 | `aupsrve_2023_jo_ohadacom` | `ohada_jo_special_aupsrve_2023` | 331 | 0.9918 | 1 |
| AUPSRVE-2023 | `aupsrve_2023_senlii` | `corpus:DOC-2564CCED2D56` | 288 | 0.9601 | 0 |
| AUPSRVE-2023 | `aupsrve_2023_senlii` | `ohada_jo_special_aupsrve_2023` | 331 | 0.8972 | 43 |
| AUPSRVE-2023 | `corpus:DOC-2564CCED2D56` | `ohada_jo_special_aupsrve_2023` | 288 | 1.0 | 0 |

Une divergence est soit une erreur de lecture, soit une **modification du texte** (une version consolidée diffère de la version d'origine) : elle se tranche à la lecture.

## 4. Corpus de référence (base du moteur)

| Domaine du moteur | Texte | Extraction | Articles indexés | Citables | État de la référence |
|---|---|---|---|---|---|
| administratif_voies_de_recours | 2016-886 — Loi n° 2016-886 du 8 novembre 2016 portant Constitution de la Républiq | OCR_TESSERACT | 160 | oui | PARTIELLEMENT_VERIFIE |
| contrats_dettes_commerce | ? — ACTE UNIFORME PORTANT ORGANISATION DES SURETES (OHADA) — Journal Offic | CALQUE_TEXTE | 228 | oui | VERIFIE |
| contrats_dettes_commerce | AUPSRVE-2023 — Journal officiel de l'OHADA, numéro spécial du 15 novembre 2023 — Acte | OCR_TESSERACT_PARTIEL | 288 | oui | PARTIELLEMENT_VERIFIE |
| donnees_personnelles_numerique | 2013-450 — LOI N° 2013-450 DU 19 JUIN 2013 RELATIVE A LA PROTECTION DES DONNEES A | OCR_VISION_AUTO | 53 | non | PARTIELLEMENT_VERIFIE |
| donnees_personnelles_numerique | 2013-451 — LOI N° 2013-451 DU 19 JUIN 2013 RELATIVE A LA LUTTE CONTRE LA CYBERCRI | OCR_VISION_AUTO | 78 | non | PARTIELLEMENT_VERIFIE |
| donnees_personnelles_numerique | 2013-546 — LOI N° 2013-546 DU 30 JUILLET 2013 RELATIVE AUX TRANSACTIONS ELECTRONI | OCR_VISION_AUTO | 48 | non | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | ? — Recueil de texte de lois adulte final 18-02-2026 | TEXTE_DE_COMPILATION | 0 | oui | — |
| famille_mariage_filiation | ? — RECUEIL DES TEXTES JURIDIQUES : Protection des Droits des enfants, ado | TEXTE_DE_COMPILATION | 0 | oui | — |
| famille_mariage_filiation | ? — Décret Portant Règlementation des Familles d'Accueil, 2023 (Décret 90  | CALQUE_TEXTE | 22 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | ? — LOI RELATIVE A L’ADOPTION | AUCUNE | 0 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | ? — CONVENTION SUR LA PROTECTION DES ENFANTS ET LA COOPÉRATION EN MATIÈRE  | AUCUNE | 0 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2015-539 — LOI No 2015-539 du 20 juillet 2015 portant Statut de pupille de l’Etat | AUCUNE | 0 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2016-1111 — Loi n° 2016-1111 du 8 décembre 2016 relative à la lutte contre la trai | OCR_TESSERACT | 23 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2018-862 — Loi n°2018-862 du 19 novembre 2018 relative à l’état civil. | AUCUNE | 0 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2018-863 — Loi n°2018-863 du 19 novembre 2018 instituant une procédure spéciale d | AUCUNE | 26 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2019-571 — LOI n° 2019-571 du 26 juin 2019 relative à la filiation | CALQUE_TEXTE | 30 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2019-572 — Loi n°2019-572 du 26 Juin 2019 relative à la minorité | AUCUNE | 0 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2019-779 — DÉCRET No 2019-779 portant création, attributions, organisation et fon | AUCUNE | 9 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 202-894 — LOI n° 202-894 du 21 décembre 2021 relative aux mesures de protection  | AUCUNE | 16 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2020-907 — DECRET No 2020-907 DU 18 NOVEMBRE 2020 PORTANT ATTRIBUTIONS, ORGANISAT | AUCUNE | 29 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2023-89 — DECRET No 2023-89 DU 15 FEVRIER 2023 FIXANT LES NORMES ET STANDARDS AP | AUCUNE | 68 | oui | PARTIELLEMENT_VERIFIE |
| famille_mariage_filiation | 2023-90 — DECRET No 2023-90 DU 15 FEVRIER 2023 PORTANT REGLEMENTATION DES FAMILL | AUCUNE | 21 | oui | PARTIELLEMENT_VERIFIE |
| logement_baux_foncier | ? — COMMUNIQUE DU CONSEIL DES MINISTRES DU 12 JUIN 2024 — Porte-parolat du | TEXTE_NON_JURIDIQUE | 0 | oui | — |
| logement_baux_foncier | 2019-576 — LOI N° 2019-576 DU 26 JUIN 2019 INSTITUANT CODE DE LA CONSTRUCTION ET  | CALQUE_TEXTE | 553 | oui | VERIFIE |
| logement_baux_foncier | 2020-623 — LOI N° 2020-623 DU 14 AOUT 2020 PORTANT RATIFICATION DE L'ORDONNANCE N | OCR_VISION_AUTO | 2 | oui | PARTIELLEMENT_VERIFIE |
| logement_baux_foncier | 2020-624 — LOI N° 2020-624 DU 14 AOÛT 2020 INSTITUANT CODE DE L'URBANISME ET DU D | CALQUE_TEXTE | 302 | oui | VERIFIE |
| logement_baux_foncier | 2020-624 — LOI N° 2020-624 DU 14 AOÛT 2020 INSTITUANT CODE DE L'URBANISME ET DU D | OCR_VISION_AUTO | 287 | oui | PARTIELLEMENT_VERIFIE |
| logement_baux_foncier | 98-750 — LOI N° 98-750 DU 23 DECEMBRE 1998 RELATIVE AU DOMAINE FONCIER RURAL (e | OCR_VISION_AUTO | 29 | oui | PARTIELLEMENT_VERIFIE |
| transport_responsabilite_civile | 2013-711 — DECRET N° 2013-711 DU 18 OCTOBRE 2013 PORTANT INTERDICTION DE L'USAGE  | CALQUE_TEXTE | 6 | oui | VERIFIE |

## 5. Échecs et sources inaccessibles

| Clé | Catégorie | Statut | HTTP | Détail |
|---|---|---|---|---|
| `code_penal_2019_574_mffe` | OFFICIEL_PORTAIL_GOUV | ECHEC_HTTP | 404 |  |
| `code_penal_2019_574_civlii` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `cpp_2018_975_civlii` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `travail_2015_532_faolex` | SECONDAIRE_BASE_INTERNATIONALE | ECHEC_HTTP | 404 |  |
| `travail_2015_532_civlii` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `mariage_2019_570_civlii` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `successions_2019_573_civlii` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `minorite_2019_572_civlii` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `filiation_2019_571_civlii` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `dec_mffe_textes` | DECOUVERTE | ECHEC_HTTP | 403 |  |
| `dec_emploi_gouv` | DECOUVERTE | ECHEC_HTTP | 403 |  |
| `dec_civlii_publication_2019_570_eng@2023-10-13` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_publication_2019_571_fra@2023-10-13` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_publication_2019_572_fra@2023-10-13` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_publication_2019_573_fra@2023-10-13` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_publication_2019_574_fra@2024-06-23` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_publication_2018_975_fra@2024-06-23` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_publication_2015_532_fra@2023-08-10` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_legislation_p2` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_legislation_p3` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_legislation_p4` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_legislation_p5` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_legislation_p6` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_legislation_p7` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_legislation_p8` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_legislation_p9` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_legislation_p10` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `assnat_constitution` | OFFICIEL_INSTITUTION | ECHEC_HTTP | 404 |  |
| `civlii_code_penal_source_pdf` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `civlii_cpp_source_pdf` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `dec_civlii_oeuvre_cpp` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_oeuvre_penal` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_civlii_oeuvre_travail` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `dec_famille_gouv_publications` | DECOUVERTE | ECHEC_HTTP | 404 |  |
| `civlii_travail_enfants_2010_272` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |
| `civlii_travail_source_pdf` | SECONDAIRE_CONSOLIDE | ECHEC_HTTP | 404 |  |

## 6. Domaines concernés par les documents téléchargés

| Domaine | Documents |
|---|---|
| 1. Droit civil | aucun |
| 2. Droit de la famille | mariage_2019_570_faolex (EXPLOITABLE_RECOUPEMENT_SEULEMENT)<br>mffe_adoption (QUARANTAINE)<br>mffe_code_penal_2019_574 (EXPLOITABLE_OFFICIEL)<br>mffe_etat_civil_2018_862 (QUARANTAINE)<br>mffe_mariage_2019_570 (EXPLOITABLE_OFFICIEL)<br>mffe_naissance_2018_863 (QUARANTAINE)<br>mffe_successions_2019_573 (QUARANTAINE)<br>officiel_famille_convention_sur_la_protection_des_enfants_et_la_c (EXPLOITABLE_OFFICIEL)<br>officiel_famille_d_cret_portant_r_glementation_des_familles_d_acc (QUARANTAINE)<br>officiel_famille_loi_n_2018_862_du_19_novembre_2018_relative_l_ta (QUARANTAINE)<br>officiel_famille_loi_n_2018_863_du_19_novembre_2018_instituant_un (QUARANTAINE)<br>officiel_famille_loi_n_2019_571_du_26_juin_2019_relative_la_filia (QUARANTAINE)<br>officiel_famille_loi_n_2019_572_du_26_juin_2019_relative_la_minor (QUARANTAINE)<br>officiel_famille_loi_relative_a_l_adoption (EXPLOITABLE_OFFICIEL)<br>successions_2019_573_assnat (QUARANTAINE)<br>successions_2019_573_bice (QUARANTAINE) |
| 3. Droit immobilier, foncier et logement | aucun |
| 4. Droit du travail et droit social | ilo_textes_pertinents_rci (EXPLOITABLE_RECOUPEMENT_SEULEMENT)<br>travail_2015_532_uvci (EXPLOITABLE_RECOUPEMENT_SEULEMENT) |
| 5. Droit pénal et procédure pénale | mffe_code_penal_2019_574 (EXPLOITABLE_OFFICIEL)<br>mffe_cpp_2018_975 (EXPLOITABLE_OFFICIEL)<br>mffe_traite_2016_1111 (EXPLOITABLE_OFFICIEL) |
| 6. Droit commercial et droit des affaires | aucun |
| 7. Droit de la consommation | aucun |
| 8. Droit bancaire et crédit | aucun |
| 9. Droit administratif | aucun |
| 10. Droit constitutionnel et libertés fondamentales | mffe_constitution_2016 (EXPLOITABLE_OFFICIEL) |
| 11. Droit fiscal | aucun |
| 12. Droit des assurances | aucun |
| 13. Droit des transports et circulation routière | aucun |
| 14. Droit du numérique et données personnelles | aucun |
| 15. Droit de la santé | aucun |
| 16. Droit des associations et organisations | aucun |
| 17. Droit de l'éducation | aucun |
| 18. Droit rural et agricole | aucun |
| 19. Droit de l'environnement et de l'urbanisme | aucun |
| 20. Propriété intellectuelle | aucun |
| 21. Droit des étrangers et nationalité | aucun |
| 22. Protection de l'enfant et des personnes vulnérables | ilo_textes_pertinents_rci (EXPLOITABLE_RECOUPEMENT_SEULEMENT)<br>mffe_adoption (QUARANTAINE)<br>mffe_code_penal_2019_574 (EXPLOITABLE_OFFICIEL)<br>mffe_cpp_2018_975 (EXPLOITABLE_OFFICIEL)<br>mffe_naissance_2018_863 (QUARANTAINE)<br>mffe_pupille_2015_539 (QUARANTAINE)<br>mffe_traite_2016_1111 (EXPLOITABLE_OFFICIEL)<br>officiel_famille_d_cret_no_2019_779_portant_cr_ation_attributions (EXPLOITABLE_OFFICIEL)<br>officiel_famille_decret_no_2020_907_du_18_novembre_2020_portant_a (QUARANTAINE)<br>officiel_famille_decret_no_2023_89_du_15_fevrier_2023_fixant_les_ (QUARANTAINE)<br>officiel_famille_decret_no_2023_90_du_15_fevrier_2023_portant_reg (EXPLOITABLE_OFFICIEL)<br>officiel_famille_loi_n_2019_572_du_26_juin_2019_relative_la_minor (QUARANTAINE)<br>officiel_famille_loi_n_202_894_du_21_d_cembre_2021_relative_aux_m (QUARANTAINE)<br>officiel_famille_loi_no_2015_539_du_20_juillet_2015_portant_statu (QUARANTAINE) |
| 23. Droit OHADA, sûretés et voies d'exécution | aupsrve_2023_jo_ohadacom (EXPLOITABLE_RECOUPEMENT_SEULEMENT)<br>aupsrve_2023_senlii (EXPLOITABLE_RECOUPEMENT_SEULEMENT)<br>ohada_jo_special_aupsrve_2023 (EXPLOITABLE_OFFICIEL) |
| 24. Droit international privé et commerce international | aucun |

## 7. Outils utilisés

| Outil | Version | Où |
|---|---|---|
| pdftotext | pdftotext version 24.02.0 | runner GitHub Actions (paquets Ubuntu) |
| qpdf | qpdf version 11.9.0 | runner GitHub Actions (paquets Ubuntu) |
| tesseract | tesseract 5.3.4 | runner GitHub Actions (paquets Ubuntu) |
| Langues tesseract | eng, fra, osd | runner |
| Python (bibliothèque standard), sqlite3, difflib | — | runner et poste de travail |

Aucune dépendance Python ajoutée au projet. Aucune clé, aucun service payant, aucun fournisseur d'IA.

