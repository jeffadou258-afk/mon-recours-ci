# Audit des 24 domaines juridiques — Mon Recours CI

Branche `audit/24-domaines` (créée depuis `feature/produit-fonctionnel`). Données mesurées le 2026-10-19 08:53 par `bin/audit_domaines.py` (fichier `reports/inventaire_24_domaines.json`) ; ce rapport est rédigé à partir de ce fichier par `bin/rapport_audit_domaines.py`.

**Trois notions distinctes, jamais confondues :** fonctionnement du code (les scénarios s'exécutent comme voulu), couverture documentaire (textes et fiches disponibles), fiabilité juridique (relecture humaine). **Aucun domaine n'a de relecture juridique tracée.**

## Résumé

- **FONCTIONNEL** : 0 domaine(s)
- **PARTIEL** : 5 domaine(s) — n° 2, 3, 13, 19, 23
- **BLOQUÉ POUR VALIDATION** : 0 domaine(s)
- **NON COUVERT** : 19 domaine(s) — n° 1, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 15, 16, 17, 18, 20, 21, 22, 24
- Scénarios : 136 exécutés, 136 réussis, 0 échoués, 32 sans objet (sur 24 × 7 = 168).

Règle de statut (dans `bin/audit_domaines.py`) : NON COUVERT = aucune fiche ; BLOQUÉ = fiches sans référence citable ; FONCTIONNEL = 7 types de cas exécutés et réussis **et** aucune lacune recensée ; PARTIEL = sinon. Aucun domaine n'atteint FONCTIONNEL : chacun des 5 domaines traités a des lacunes documentées ci-dessous.

## Matrice de conformité

| Domaine | Textes disponibles | Situations réellement traitées | Questions disponibles | Tests exécutés | Lacunes | Statut technique | Validation juridique |
|---|---|---|---|---|---|---|---|
| 1. Droit civil | aucun | aucune | 0 | 6/6 réussis, 1 sans objet | Aucun texte de droit civil général (Code civil, obligations, responsabilité) dans le corpus. | **NON COUVERT** | non réalisée |
| 2. Droit de la famille | 2019-571 (30 art. citables / 30 indexés); 2018-862 (0 art. citables / 0 indexés); 2018-863 (26 art. citables / 26 indexés); 2019-572 (0 art. citables / 0 indexés) | Droit de l'enfant à sa filiation (art. 1); Paternité de l'enfant né pendant le mariage (art. 2); Contester la paternité (désaveu par le mari) (art. 4); Délai pour contester la paternité (art. 6); Prouver la filiation d'un enfant né dans le mariage (art. 9); Filiation de l'enfant né hors mariage (art. 19); Reconnaître un enfant (art. 20); Reconnaissance après l'acte de naissance (art. 21); Homme marié qui reconnaît un enfant né hors mariage (art. 22); Faire déclarer la paternité par le juge (art. 24); Qui peut agir en recherche de paternité (art. 26) | 7 | 7/7 réussis, 0 sans objet | Seule la filiation (loi 2019-571) a des fiches. Mariage, divorce, pension alimentaire, successions : aucun texte au corpus. État civil (2018-862), minorité (2019-572), adoption, pupilles : textes présents mais 0 article indexé. Loi « 202-894 » du 21 décembre 2021 : numéro tel qu'il figure dans la base, à vérifier sur l'exemplaire officiel. | **PARTIEL** | non réalisée |
| 3. Droit immobilier, foncier et logement | 2019-576 (553 art. citables / 553 indexés); 2020-623 (2 art. citables / 2 indexés) | Forme du bail d'habitation (art. 414); Avance sur loyers (art. 415); Dépôt de garantie (caution) (art. 416); Révision du loyer (art. 423); Congé donné par le bailleur (art. 440); Demande de résiliation (art. 443); Expulsion forcée (art. 445) | 11 | 7/7 réussis, 0 sans objet | Loi 2025-221 (contentieux du bail, exécution des expulsions) non intégrée : la procédure d'expulsion n'est couverte que par les articles 443 et 445 du Code de la construction. Bail commercial, copropriété, titre foncier, ACD : aucune fiche. Les lectures des fiches et les questions ne sont pas relues par un juriste. | **PARTIEL** | non réalisée |
| 4. Droit du travail et droit social | aucun | aucune | 0 | 6/6 réussis, 1 sans objet | Aucun texte du droit du travail (Code du travail, conventions collectives, CNPS). | **NON COUVERT** | non réalisée |
| 5. Droit pénal et procédure pénale | aucun | aucune | 0 | 6/6 réussis, 1 sans objet | Aucun texte pénal (Code pénal, Code de procédure pénale). | **NON COUVERT** | non réalisée |
| 6. Droit commercial et droit des affaires | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Aucun Acte uniforme de droit commercial ou des sociétés. | **NON COUVERT** | non réalisée |
| 7. Droit de la consommation | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Aucun texte de droit de la consommation. | **NON COUVERT** | non réalisée |
| 8. Droit bancaire et crédit | aucun | aucune | 0 | 6/6 réussis, 1 sans objet | Aucun texte bancaire (UEMOA, BCEAO, microfinance). | **NON COUVERT** | non réalisée |
| 9. Droit administratif | aucun | aucune | 0 | 6/6 réussis, 1 sans objet | Aucun texte de procédure administrative. | **NON COUVERT** | non réalisée |
| 10. Droit constitutionnel et libertés fondamentales | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Constitution absente du corpus. | **NON COUVERT** | non réalisée |
| 11. Droit fiscal | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Code général des impôts et lois de finances absents. | **NON COUVERT** | non réalisée |
| 12. Droit des assurances | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Code CIMA absent. | **NON COUVERT** | non réalisée |
| 13. Droit des transports et circulation routière | 2013-711 (6 art. citables / 6 indexés) | Téléphone au volant (art. 2) | 0 | 6/6 réussis, 1 sans objet | Une seule situation couverte (téléphone au volant, décret 2013-711, 6 articles). Code de la route, accidents et indemnisation : absents. Aucune question de clarification pour la fiche. | **PARTIEL** | non réalisée |
| 14. Droit du numérique et données personnelles | 2013-450 (0 art. citables / 53 indexés); 2013-451 (0 art. citables / 78 indexés); 2013-546 (0 art. citables / 48 indexés) | aucune | 0 | 6/6 réussis, 1 sans objet | Lois 2013-450, 2013-451 et 2013-546 indexées par OCR non recoupé : 179 articles neutralisés (non citables), aucune fiche. | **NON COUVERT** | non réalisée |
| 15. Droit de la santé | aucun | aucune | 0 | 6/6 réussis, 1 sans objet | Aucun texte de santé ou de droits des patients. | **NON COUVERT** | non réalisée |
| 16. Droit des associations et organisations | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Aucun texte sur les associations. | **NON COUVERT** | non réalisée |
| 17. Droit de l'éducation | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Aucun texte sur l'éducation. | **NON COUVERT** | non réalisée |
| 18. Droit rural et agricole | 98-750 (29 art. citables / 29 indexés) | aucune | 0 | 6/6 réussis, 1 sans objet | Loi 98-750 (foncier rural) indexée par OCR non recoupé, 29 articles, aucune fiche ni relecture. | **NON COUVERT** | non réalisée |
| 19. Droit de l'environnement et de l'urbanisme | 2020-624 (302 art. citables / 302 indexés); 2020-624 (287 art. citables / 287 indexés) | Domaine public urbain (art. 181); Expropriation (art. 238); Aménagement foncier (art. 69) | 0 | 6/6 réussis, 1 sans objet | Trois fiches de définition (domaine public, expropriation, réserves foncières) sans question de clarification. Code de l'environnement absent ; procédure et indemnisation d'expropriation non détaillées dans les fiches. | **PARTIEL** | non réalisée |
| 20. Propriété intellectuelle | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Accord de Bangui (OAPI) et textes de propriété intellectuelle absents. | **NON COUVERT** | non réalisée |
| 21. Droit des étrangers et nationalité | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Code de la nationalité et textes sur le séjour absents. | **NON COUVERT** | non réalisée |
| 22. Protection de l'enfant et des personnes vulnérables | 2023-89 (68 art. citables / 68 indexés); 2023-90 (21 art. citables / 21 indexés); 202-894 (16 art. citables / 16 indexés); 2019-779 (9 art. citables / 9 indexés); 2020-907 (29 art. citables / 29 indexés) | aucune | 0 | 6/6 réussis, 1 sans objet | Décrets 2023-89, 2023-90, 2019-779, 2020-907 et loi « 202-894 » indexés, mais aucune fiche. Loi 2019-572 (minorité) et loi 2015-539 (pupilles) : 0 article indexé. | **NON COUVERT** | non réalisée |
| 23. Droit OHADA, sûretés et voies d'exécution | Acte uniforme OHADA (sûretés) (228 art. citables / 228 indexés) | Définition de la sûreté (OHADA) (art. 1); Sûretés personnelles et cautionnement (OHADA) (art. 4) | 0 | 6/6 réussis, 1 sans objet | Seul l'Acte uniforme portant organisation des sûretés est présent (2 fiches de définition). Acte uniforme sur le recouvrement et les voies d'exécution absent : saisies non couvertes. Aucune question de clarification. | **PARTIEL** | non réalisée |
| 24. Droit international privé et commerce international | aucun | aucune | 0 | 5/5 réussis, 2 sans objet | Aucune règle de conflit de lois ; Convention de La Haye 1993 (adoption internationale) présente mais 0 article indexé. | **NON COUVERT** | non réalisée |

## Détail par domaine

### 1. Droit civil — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`contrats_dettes_commerce`, `transport_responsabilite_civile`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Mon voisin a construit un mur qui empiète sur ma parcelle, je veux des dommages et intérêts | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [1] |
| courant | mon voizin a cassé ma voiture et refuse de payer les domages et interets | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [1] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | j'ai un probleme avec quelqu'un | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Je veux faire un bornage avec mon voisin | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [1] |
| urgent | mon voisin me menace avec une machette | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [1] |
| abstention | Quel est le délai de prescription pour réclamer une dette à un voisin ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [1] |

**Lacunes** : Aucun texte de droit civil général (Code civil, obligations, responsabilité) dans le corpus.

**Corrections techniques réalisées** : Domaine désormais nommé quand la question n'est pas couverte (reconnaissance « dommages et intérêts », « voisin », « bornage »).

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Code civil applicable en Côte d'Ivoire et textes sur la responsabilité civile, en version officielle.

### 2. Droit de la famille — PARTIEL

**Code concerné** : routage `core/qualification.py` (`famille_mariage_filiation`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** :
- 2019-571 — LOI n° 2019-571 du 26 juin 2019 relative à la filiation (2019-06-26) ; 30 articles indexés, 30 citables ; lecture CALQUE_TEXTE ; référence PARTIELLEMENT_VERIFIE ; source https://famille.gouv.ci/uploads/publications/176937124389.pdf.
- 2018-862 — Loi n°2018-862 du 19 novembre 2018 relative à l’état civil. (2018-11-19) ; 0 articles indexés, 0 citables ; lecture AUCUNE ; référence PARTIELLEMENT_VERIFIE ; source https://famille.gouv.ci/uploads/publications/176937063397.pdf.
- 2018-863 — Loi n°2018-863 du 19 novembre 2018 instituant une procédure spéciale de déclaration de naissance, de rétablissement d’identité et de transcription d’acte de naissance. (2018-11-19) ; 26 articles indexés, 26 citables ; lecture AUCUNE ; référence PARTIELLEMENT_VERIFIE ; source https://famille.gouv.ci/uploads/publications/176936984489.pdf.
- 2019-572 — Loi n°2019-572 du 26 Juin 2019 relative à la minorité (2019-06-26) ; 0 articles indexés, 0 citables ; lecture AUCUNE ; référence PARTIELLEMENT_VERIFIE ; source https://famille.gouv.ci/uploads/publications/17693691723.pdf.

**Situations traitées (fiches)** :
- `FAMILL_1` Droit de l'enfant à sa filiation — article 1, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : aucune
- `FAMILL_2` Paternité de l'enfant né pendant le mariage — article 2, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : mere_mariee
- `FAMILL_4` Contester la paternité (désaveu par le mari) — article 4, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : aucune
- `FAMILL_6` Délai pour contester la paternité — article 6, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : mari_present_naissance, plus_de_deux_mois
- `FAMILL_9` Prouver la filiation d'un enfant né dans le mariage — article 9, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : mere_mariee
- `FAMILL_19` Filiation de l'enfant né hors mariage — article 19, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : pere_a_reconnu
- `FAMILL_20` Reconnaître un enfant — article 20, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : pere_a_reconnu
- `FAMILL_21` Reconnaissance après l'acte de naissance — article 21, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : enfant_plus_18_ans
- `FAMILL_22` Homme marié qui reconnaît un enfant né hors mariage — article 22, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : pere_marie_autre
- `FAMILL_24` Faire déclarer la paternité par le juge — article 24, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : pere_a_reconnu
- `FAMILL_26` Qui peut agir en recherche de paternité — article 26, texte 2019-571, référence PARTIELLEMENT_VERIFIE ; questions : enfant_mineur_mere_agit

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Le père de mon enfant refuse de le reconnaître | reussi | étape clarification ; fiches FAMILL_20, FAMILL_24, FAMILL_26 ; 2 question(s) ; urgence NORMALE |
| courant | le pere de mon enfan refuse de le reconaitre | reussi | étape clarification ; fiches FAMILL_20, FAMILL_24, FAMILL_26 ; 2 question(s) ; urgence NORMALE |
| clarif | Je suis le mari et je veux contester la paternité de l'enfant né pendant notre mariage | reussi | étape clarification ; fiches FAMILL_2, FAMILL_4 ; 1 question(s) ; urgence NORMALE |
| ambigu | j'ai un souci avec mon mari | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Je veux divorcer de mon mari | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [2] |
| urgent | Mon mari frappe les enfants et me menace | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [5] |
| abstention | Combien de temps j'ai pour contester la paternité, quel délai ? | reussi | étape clarification ; fiches FAMILL_4, FAMILL_6 ; 2 question(s) ; urgence NORMALE ; fin : ANALYSE_CONFORME |

**Lacunes** : Seule la filiation (loi 2019-571) a des fiches. Mariage, divorce, pension alimentaire, successions : aucun texte au corpus. État civil (2018-862), minorité (2019-572), adoption, pupilles : textes présents mais 0 article indexé. Loi « 202-894 » du 21 décembre 2021 : numéro tel qu'il figure dans la base, à vérifier sur l'exemplaire officiel.

**Corrections techniques réalisées** : Une faute d'une lettre tolérée (« reconaitre ») ; « paternité », « désaveu » reconnus ; déclencheur « faire reconnaître » restreint (il captait « reconnaître un jugement étranger ») ; urgence « frappe les enfants » détectée (elle restait NORMALE).

**Questions pour un juriste** : Relire les 11 fiches de filiation, leurs lectures et les 7 questions ; confirmer le numéro de la loi « 202-894 ».

**Sources à obtenir ou vérifier** : Textes sur le mariage, le divorce, la pension alimentaire et les successions ; indexation des textes déjà présents (état civil, minorité, adoption).

### 3. Droit immobilier, foncier et logement — PARTIEL

**Code concerné** : routage `core/qualification.py` (`logement_baux_foncier`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** :
- 2019-576 — LOI N° 2019-576 DU 26 JUIN 2019 INSTITUANT CODE DE LA CONSTRUCTION ET DE L'HABITAT (2019-06-26) ; 553 articles indexés, 553 citables ; lecture CALQUE_TEXTE ; référence VERIFIE ; source https://www.dgi.gouv.ci/assets/documents/transfert_propriete/lois_reglements/LOI%20N%C2%B0%202019-576%20DU%2026%20JUIN%202019%20INSTITUANT%20CODE%20DE%20LA%20CONSTRUCTION%20ET%20DE%20L%27HABITAT.pdf.
- 2020-623 — LOI N° 2020-623 DU 14 AOUT 2020 PORTANT RATIFICATION DE L'ORDONNANCE N° 2020-386 DU 15 AVRIL 2020 PORTANT SUSPENSION DES PROCEDURES D'EXPULSION DES LOCATAIRES ET DE REVISION A LA HAUSSE DU LOYER DES BAUX D'HABITATION (2020-08-14) ; 2 articles indexés, 2 citables ; lecture OCR_VISION_AUTO ; référence PARTIELLEMENT_VERIFIE ; source https://construction.gouv.ci/uploads/publications/178542265442.pdf.

**Situations traitées (fiches)** :
- `LOGEME_414` Forme du bail d'habitation — article 414, texte 2019-576, référence VERIFIE ; questions : bail_ecrit
- `LOGEME_415` Avance sur loyers — article 415, texte 2019-576, référence VERIFIE ; questions : avance_plus_deux_mois, autres_sommes
- `LOGEME_416` Dépôt de garantie (caution) — article 416, texte 2019-576, référence VERIFIE ; questions : depot_plus_deux_mois, logement_quitte, manquement_invoque
- `LOGEME_423` Révision du loyer — article 423, texte 2019-576, référence VERIFIE ; questions : revision_moins_trois_ans
- `LOGEME_440` Congé donné par le bailleur — article 440, texte 2019-576, référence VERIFIE ; questions : conge_trois_mois, conge_forme
- `LOGEME_443` Demande de résiliation — article 443, texte 2019-576, référence VERIFIE ; questions : lettre_resiliation_ecrite
- `LOGEME_445` Expulsion forcée — article 445, texte 2019-576, référence VERIFIE ; questions : lettre_resiliation_ecrite, decision_juge

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Mon bailleur refuse de me rendre ma caution | reussi | étape clarification ; fiches LOGEME_416 ; 3 question(s) ; urgence NORMALE |
| courant | mon baileur veut pas me rendre ma caution | reussi | étape clarification ; fiches LOGEME_416 ; 3 question(s) ; urgence NORMALE |
| clarif | Mon propriétaire veut augmenter mon loyer | reussi | étape clarification ; fiches LOGEME_423 ; 2 question(s) ; urgence NORMALE |
| ambigu | j'ai un problème avec mon propriétaire | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [3] |
| hors | Je loue une boutique et le propriétaire veut résilier mon bail commercial | reussi | étape clarification ; fiches LOGEME_443 ; 2 question(s) ; urgence NORMALE |
| urgent | On veut m'expulser demain matin avec la police, le bailleur a changé les serrures | reussi | étape clarification ; fiches LOGEME_445 ; 3 question(s) ; urgence ELEVEE |
| abstention | Dans combien de jours le bailleur doit me rendre ma caution ? | reussi | étape clarification ; fiches LOGEME_416 ; 3 question(s) ; urgence NORMALE ; fin : ANALYSE_CONFORME |

**Lacunes** : Loi 2025-221 (contentieux du bail, exécution des expulsions) non intégrée : la procédure d'expulsion n'est couverte que par les articles 443 et 445 du Code de la construction. Bail commercial, copropriété, titre foncier, ACD : aucune fiche. Les lectures des fiches et les questions ne sont pas relues par un juriste.

**Corrections techniques réalisées** : Correspondance par mots entiers ; un déclencheur d'un seul mot (« préavis », « résiliation ») n'est retenu que si le logement est reconnu ; « expulser », « dépôt de garantie », « expropriation » reconnus.

**Questions pour un juriste** : Relire les 7 fiches de bail, leurs lectures et les 11 questions ; dire si la loi 2025-221 modifie la portée des articles 443 et 445 (expulsion) ; décider de l'usage d'une reproduction CIVLII.

**Sources à obtenir ou vérifier** : Loi 2025-221 en exemplaire officiel (JO n° 32 du 21/04/2025) ; textes sur le bail commercial (Acte uniforme OHADA) et le titre foncier.

### 4. Droit du travail et droit social — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`travail`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Mon employeur ne me paie plus mon salaire depuis trois mois | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [4] |
| courant | mon patron veu pas me payé mon salair | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [4] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | j'ai des soucis au travail | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | On m'a licencié sans préavis, ai-je droit à une indemnité ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [4] |
| urgent | mon patron m'a frappé au travail et menace de me tuer | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [4, 5] |
| abstention | Combien de mois de salaire mon employeur doit-il me verser après un licenciement ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence ELEVEE ; domaine reconnu [4] |

**Lacunes** : Aucun texte du droit du travail (Code du travail, conventions collectives, CNPS).

**Corrections techniques réalisées** : « licencié sans préavis » ne reçoit plus la fiche du congé donné par le BAILLEUR ; domaine nommé.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Code du travail et textes de prévoyance sociale.

### 5. Droit pénal et procédure pénale — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`penal_procedure_penale`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Je veux porter plainte pour vol de mon téléphone | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence ELEVEE ; domaine reconnu [5] |
| courant | on ma volé mon telefone je veu porté plainte | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence ELEVEE ; domaine reconnu [5] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | la police me cherche | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [5] |
| hors | Quelle est la peine pour escroquerie ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [5] |
| urgent | mon frere est en garde a vue depuis 3 jours sans avocat | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [5] |
| abstention | Combien de temps la garde à vue peut-elle durer ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [5] |

**Lacunes** : Aucun texte pénal (Code pénal, Code de procédure pénale).

**Corrections techniques réalisées** : Domaine nommé quand non couvert.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Code pénal et Code de procédure pénale.

### 6. Droit commercial et droit des affaires — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`contrats_dettes_commerce`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Je veux créer une société et m'inscrire au registre du commerce | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [6] |
| courant | je veu cree ma societe et avoir le rccm | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [6] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | mon associé ne veut plus travailler | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [6] |
| hors | Comment vendre mon fonds de commerce ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [6] |
| urgent | — | sans objet | domaine sans risque typique pour la sécurité d'une personne |
| abstention | Quel capital minimum pour créer une société ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [6] |

**Lacunes** : Aucun Acte uniforme de droit commercial ou des sociétés.

**Corrections techniques réalisées** : Domaine nommé quand non couvert.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Actes uniformes OHADA (droit commercial général, sociétés commerciales).

### 7. Droit de la consommation — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`consommation`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | J'ai acheté un téléphone défectueux et le vendeur refuse de me rembourser | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [7] |
| courant | le vendeur veu pa remboursé mon produit defectueux | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [7] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | je ne suis pas content de mon achat | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [7] |
| hors | Mon abonnement internet est facturé deux fois | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [7] |
| urgent | — | sans objet | domaine sans risque typique pour la sécurité d'une personne |
| abstention | Combien de jours ai-je pour retourner un produit défectueux ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [7] |

**Lacunes** : Aucun texte de droit de la consommation.

**Corrections techniques réalisées** : Domaine nommé quand non couvert.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Texte de protection du consommateur.

### 8. Droit bancaire et crédit — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`contrats_dettes_commerce`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | La banque refuse de m'accorder un crédit | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [8] |
| courant | la banque a bloqué mon compte bancaire sans raison | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [8, 3] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | j'ai un souci d'argent | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Le taux d'interet de mon credit a changé | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [8] |
| urgent | une société de microfinance menace de saisir tous mes biens demain | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence ELEVEE ; domaine reconnu [6, 8, 23] |
| abstention | Quel est le taux d'interet maximum autorisé pour un crédit ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [8] |

**Lacunes** : Aucun texte bancaire (UEMOA, BCEAO, microfinance).

**Corrections techniques réalisées** : Urgence « menace de saisir mes biens demain » détectée (elle restait NORMALE).

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Textes bancaires et de microfinance (UEMOA / BCEAO).

### 9. Droit administratif — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`administratif_voies_de_recours`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | La mairie refuse de me délivrer un document administratif | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [9] |
| courant | la mairi veu pa me donner mon papier, c'est l'administration | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [9] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | on m'a refusé quelque chose | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Comment faire un recours administratif contre une décision ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [9] |
| urgent | l'administration va démolir ma maison demain | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence ELEVEE ; domaine reconnu [3, 9] |
| abstention | Quel est le délai pour faire un recours administratif ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [9] |

**Lacunes** : Aucun texte de procédure administrative.

**Corrections techniques réalisées** : Urgence « démolir ma maison demain » détectée (elle restait NORMALE).

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Textes de procédure administrative et de recours.

### 10. Droit constitutionnel et libertés fondamentales — NON COUVERT

**Code concerné** : routage `core/qualification.py` (aucune clé de routage dans le moteur) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | La police a interdit notre manifestation pacifique | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [5, 10] |
| courant | on m'a empeché de voter a l'election | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [10] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | je trouve que c'est injuste | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Que dit la constitution sur la liberté d'expression ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [10] |
| urgent | — | sans objet | domaine sans risque typique pour la sécurité d'une personne |
| abstention | Quel article de la constitution protège la liberté de culte ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [10] |

**Lacunes** : Constitution absente du corpus.

**Corrections techniques réalisées** : Domaine nommé quand non couvert.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Constitution en vigueur.

### 11. Droit fiscal — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`administratif_voies_de_recours`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Les impôts me réclament une taxe que je ne dois pas | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [11] |
| courant | les impots me demande de payé une patente | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [11] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | on me demande de l'argent | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | J'ai reçu un redressement fiscal | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [11] |
| urgent | — | sans objet | domaine sans risque typique pour la sécurité d'une personne |
| abstention | Quel est le taux de la TVA ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [11] |

**Lacunes** : Code général des impôts et lois de finances absents.

**Corrections techniques réalisées** : Domaine nommé quand non couvert.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Code général des impôts et loi de finances de l'année.

### 12. Droit des assurances — NON COUVERT

**Code concerné** : routage `core/qualification.py` (aucune clé de routage dans le moteur) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Mon assurance refuse d'indemniser mon sinistre | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [12] |
| courant | l'assureur veu pa payé apres mon sinistre | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [12] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | on ne veut pas me payer | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Mon assureur a résilié ma police d'assurance | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [12, 5] |
| urgent | — | sans objet | domaine sans risque typique pour la sécurité d'une personne |
| abstention | Dans quel délai l'assurance doit-elle payer après un sinistre ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [12] |

**Lacunes** : Code CIMA absent.

**Corrections techniques réalisées** : « ma police d'assurance résiliée » ne reçoit plus la fiche de résiliation du BAIL.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Code CIMA.

### 13. Droit des transports et circulation routière — PARTIEL

**Code concerné** : routage `core/qualification.py` (`transport_responsabilite_civile`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** :
- 2013-711 — DECRET N° 2013-711 DU 18 OCTOBRE 2013 PORTANT INTERDICTION DE L'USAGE DU TELEPHONE PORTABLE ET DE TOUT AUTRE MOYEN DE COMMUNICATION EN SITUATION DE CONDUITE AUTOMOBILE (2013-10-18) ; 6 articles indexés, 6 citables ; lecture CALQUE_TEXTE ; référence VERIFIE ; source https://www.sgg.gouv.ci/photo_doc/1399281886Decret_N_2013_791_du_20_novembre_2013%20.pdf.

**Situations traitées (fiches)** :
- `TRANSP_2` Téléphone au volant — article 2, texte 2013-711, référence VERIFIE ; questions : aucune

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Un policier m'a arrêté parce que je téléphonais en conduisant | reussi | étape clarification ; fiches TRANSP_2 ; 0 question(s) ; urgence NORMALE |
| courant | la police ma arreté car j'avais le telephone au volan | reussi | étape clarification ; fiches TRANSP_2 ; 0 question(s) ; urgence NORMALE |
| clarif | — | sans objet | la fiche TRANSP_2 n'a pas de question de clarification dans le guide |
| ambigu | j'ai un souci avec ma voiture | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | J'ai eu un accident de voiture, l'autre conducteur refuse de payer | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [13] |
| urgent | accident de moto, mon frère est blessé et saigne beaucoup | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [13] |
| abstention | Quelle est l'amende pour le téléphone au volant ? | reussi | étape clarification ; fiches TRANSP_2 ; 0 question(s) ; urgence NORMALE ; fin : ANALYSE_CONFORME |

**Lacunes** : Une seule situation couverte (téléphone au volant, décret 2013-711, 6 articles). Code de la route, accidents et indemnisation : absents. Aucune question de clarification pour la fiche.

**Corrections techniques réalisées** : Le domaine transport n'avait AUCUN mot-clé : il ne pouvait jamais être reconnu ; ajouté. Faute « volan » tolérée. Urgence « blessé, saigne » détectée.

**Questions pour un juriste** : Relire la fiche TRANSP_2 ; confirmer que le décret 2013-711 est en vigueur.

**Sources à obtenir ou vérifier** : Code de la route et textes sur l'indemnisation des accidents.

### 14. Droit du numérique et données personnelles — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`donnees_personnelles_numerique`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** :
- 2013-450 — LOI N° 2013-450 DU 19 JUIN 2013 RELATIVE A LA PROTECTION DES DONNEES A CARACTERE PERSONNEL (exemplaire du Journal officiel du 8 août 2013) (2013-06-19) ; 53 articles indexés, 0 citables ; lecture OCR_VISION_AUTO ; référence PARTIELLEMENT_VERIFIE ; source http://www.autoritedeprotection.ci/docs/loi_2013_450_journal.pdf.
- 2013-451 — LOI N° 2013-451 DU 19 JUIN 2013 RELATIVE A LA LUTTE CONTRE LA CYBERCRIMINALITE (exemplaire du Journal officiel du 12 août 2013) (2013-06-19) ; 78 articles indexés, 0 citables ; lecture OCR_VISION_AUTO ; référence PARTIELLEMENT_VERIFIE ; source http://www.autoritedeprotection.ci/docs/Loi-2013-451.pdf.
- 2013-546 — LOI N° 2013-546 DU 30 JUILLET 2013 RELATIVE AUX TRANSACTIONS ELECTRONIQUES (exemplaire du Journal officiel du 12 septembre 2013) (2013-07-30) ; 48 articles indexés, 0 citables ; lecture OCR_VISION_AUTO ; référence PARTIELLEMENT_VERIFIE ; source http://www.autoritedeprotection.ci/docs/Loi-2013_546.pdf.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Quelqu'un a publié mes photos sur les réseaux sociaux sans mon accord | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [14] |
| courant | on a piraté mon compte facebook | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [14] |
| clarif | — | sans objet | textes neutralisés (OCR non recoupé) : aucune fiche |
| ambigu | j'ai un souci sur internet | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Une entreprise utilise mes données personnelles sans mon accord | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [14] |
| urgent | quelqu'un menace de publier mes photos intimes si je ne paie pas | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [14] |
| abstention | Quelle est la peine pour piratage informatique ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [14] |

**Lacunes** : Lois 2013-450, 2013-451 et 2013-546 indexées par OCR non recoupé : 179 articles neutralisés (non citables), aucune fiche.

**Corrections techniques réalisées** : Urgence « menace de publier mes photos intimes » détectée (elle restait NORMALE).

**Questions pour un juriste** : Dire si un exemplaire en texte natif des lois 2013-450/451/546 doit être obtenu avant toute fiche (articles neutralisés).

**Sources à obtenir ou vérifier** : Exemplaires en texte natif des lois 2013-450, 2013-451 et 2013-546.

### 15. Droit de la santé — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`sante_droits_usagers`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | L'hôpital refuse de me donner mon dossier médical | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [15] |
| courant | le medecin a fait une erreur medicale sur mon operation | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [15] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | je ne suis pas bien soigné | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | La clinique me facture des soins que je n'ai pas reçus | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [15] |
| urgent | mon enfant est très malade et l'hôpital refuse de le soigner sans payer | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence ELEVEE ; domaine reconnu [15] |
| abstention | Combien de temps l'hôpital doit-il garder mon dossier médical ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [15, 5] |

**Lacunes** : Aucun texte de santé ou de droits des patients.

**Corrections techniques réalisées** : Le domaine santé n'avait AUCUN mot-clé : jamais reconnu ; ajouté.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Textes sur les droits des patients et l'organisation des soins.

### 16. Droit des associations et organisations — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`associations_organisations_religieuses`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Le président de notre association refuse de convoquer l'assemblée générale | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [16] |
| courant | le tresorier de l'association a pris l'argent des cotisations | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [16] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | il y a des problèmes dans notre groupe | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Comment déclarer une ONG ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [16] |
| urgent | — | sans objet | domaine sans risque typique pour la sécurité d'une personne |
| abstention | Combien de membres faut-il pour créer une association ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [16] |

**Lacunes** : Aucun texte sur les associations.

**Corrections techniques réalisées** : Domaine nommé quand non couvert.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Loi sur les associations.

### 17. Droit de l'éducation — NON COUVERT

**Code concerné** : routage `core/qualification.py` (aucune clé de routage dans le moteur) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | L'école a exclu mon enfant sans explication | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [17] |
| courant | l'ecole veut pas inscrire mon enfant, les frais de scolarite sont trop cher | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [17] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | mon fils a des problèmes | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Mon fils a été recalé au BEPC, peut-on contester ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [17] |
| urgent | — | sans objet | domaine sans risque typique pour la sécurité d'une personne |
| abstention | À quel âge l'école est-elle obligatoire ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [17] |

**Lacunes** : Aucun texte sur l'éducation.

**Corrections techniques réalisées** : Domaine nommé quand non couvert.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Loi sur l'enseignement.

### 18. Droit rural et agricole — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`logement_baux_foncier`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** :
- 98-750 — LOI N° 98-750 DU 23 DECEMBRE 1998 RELATIVE AU DOMAINE FONCIER RURAL (exemplaire numérisé SGG) (1998-12-23) ; 29 articles indexés, 29 citables ; lecture OCR_VISION_AUTO ; référence PARTIELLEMENT_VERIFIE ; source https://www.sgg.gouv.ci/photo_doc/1339597849.pdf.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Ma famille conteste mes droits sur une plantation de cacao au village | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [18] |
| courant | on veut prendre mon champ au village, j'ai pas de certificat foncier | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [18] |
| clarif | — | sans objet | loi 98-750 indexée (OCR non recoupé) mais aucune fiche |
| ambigu | on se dispute pour une terre | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Comment obtenir un certificat foncier ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [18] |
| urgent | des gens armés sont venus occuper notre plantation | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [18] |
| abstention | En combien de temps obtient-on un certificat foncier ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [18] |

**Lacunes** : Loi 98-750 (foncier rural) indexée par OCR non recoupé, 29 articles, aucune fiche ni relecture.

**Corrections techniques réalisées** : Urgence « gens armés » détectée (« armés » au pluriel échappait au motif).

**Questions pour un juriste** : Dire si la lecture OCR de la loi 98-750 peut servir de base, après recoupement, ou si un exemplaire officiel est requis.

**Sources à obtenir ou vérifier** : Exemplaire officiel lisible de la loi 98-750 et ses textes d'application.

### 19. Droit de l'environnement et de l'urbanisme — PARTIEL

**Code concerné** : routage `core/qualification.py` (`logement_baux_foncier`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** :
- 2020-624 — LOI N° 2020-624 DU 14 AOÛT 2020 INSTITUANT CODE DE L'URBANISME ET DU DOMAINE FONCIER URBAIN (2020-08-14) ; 302 articles indexés, 302 citables ; lecture CALQUE_TEXTE ; référence VERIFIE ; source https://www.construction.gouv.ci/uploads/publications/178542377022.pdf.
- 2020-624 — LOI N° 2020-624 DU 14 AOÛT 2020 INSTITUANT CODE DE L'URBANISME ET DU DOMAINE FONCIER URBAIN (exemplaire numérisé DGI) (2020-08-14) ; 287 articles indexés, 287 citables ; lecture OCR_VISION_AUTO ; référence PARTIELLEMENT_VERIFIE ; source https://www.dgi.gouv.ci/assets/documents/transfert_propriete/lois_reglements/LOI%20INSTITUANT%20CODE%20URBANISME%20ET%20DOMAINE%20FONCIER%20URBAIN-4-45.pdf.

**Situations traitées (fiches)** :
- `LOGEME_181` Domaine public urbain — article 181, texte 2020-624, référence VERIFIE ; questions : aucune
- `LOGEME_238` Expropriation — article 238, texte 2020-624, référence VERIFIE ; questions : aucune
- `LOGEME_69` Aménagement foncier — article 69, texte 2020-624, référence VERIFIE ; questions : aucune

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | L'État veut exproprier mon terrain pour une route | reussi | étape clarification ; fiches LOGEME_181, LOGEME_238 ; 0 question(s) ; urgence NORMALE |
| courant | l'etat veut m'expropier pour faire une route | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| clarif | — | sans objet | les fiches 181, 238 et 69 n'ont pas de question de clarification dans le guide |
| ambigu | on construit à côté de chez moi | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Une usine pollue la rivière de notre village | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [19, 18] |
| urgent | les bulldozers vont détruire nos maisons demain pour le déguerpissement | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence ELEVEE ; domaine reconnu [3, 19] |
| abstention | Combien l'État doit-il me payer pour l'expropriation ? | reussi | étape clarification ; fiches LOGEME_238 ; 0 question(s) ; urgence NORMALE ; fin : ANALYSE_CONFORME |

**Lacunes** : Trois fiches de définition (domaine public, expropriation, réserves foncières) sans question de clarification. Code de l'environnement absent ; procédure et indemnisation d'expropriation non détaillées dans les fiches.

**Corrections techniques réalisées** : Urgence « détruire nos maisons demain / déguerpissement » détectée ; « pollution » reconnue.

**Questions pour un juriste** : Relire les fiches 181, 238 et 69 ; dire quelles questions de clarification seraient utiles (expropriation, domaine public).

**Sources à obtenir ou vérifier** : Code de l'environnement ; textes d'application sur l'expropriation.

### 20. Propriété intellectuelle — NON COUVERT

**Code concerné** : routage `core/qualification.py` (aucune clé de routage dans le moteur) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Une entreprise a copié mon logo et ma marque | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [20] |
| courant | on a copier ma musique sans payer, c'est de la contrefacon | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [20] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | on m'a volé mon idée | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Comment déposer un brevet ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [20] |
| urgent | — | sans objet | domaine sans risque typique pour la sécurité d'une personne |
| abstention | Combien d'années dure le droit d'auteur ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [20] |

**Lacunes** : Accord de Bangui (OAPI) et textes de propriété intellectuelle absents.

**Corrections techniques réalisées** : Défaut corrigé : « reprise » était trouvé dans « entreprise » ; une question de marque recevait le congé du bailleur.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Accord de Bangui (OAPI) et loi sur le droit d'auteur.

### 21. Droit des étrangers et nationalité — NON COUVERT

**Code concerné** : routage `core/qualification.py` (aucune clé de routage dans le moteur) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Comment obtenir la nationalité ivoirienne ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [21] |
| courant | ma carte de sejour a expiré | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [21] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | j'ai un problème de papiers | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Je suis étranger, puis-je acheter un terrain ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [3, 21] |
| urgent | — | sans objet | aucun cas urgent formulable sans inventer de procédure ; l'expulsion du territoire est couverte par la détection générale |
| abstention | Après combien d'années de mariage peut-on obtenir la nationalité ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [2, 21] |

**Lacunes** : Code de la nationalité et textes sur le séjour absents.

**Corrections techniques réalisées** : Domaine nommé quand non couvert.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Code de la nationalité ; textes sur l'entrée et le séjour des étrangers.

### 22. Protection de l'enfant et des personnes vulnérables — NON COUVERT

**Code concerné** : routage `core/qualification.py` (`famille_mariage_filiation`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** :
- 2023-89 — DECRET No 2023-89 DU 15 FEVRIER 2023 FIXANT LES NORMES ET STANDARDS APPLICABLES AUX ETABLISSEMENTS DE PROTECTION DE REMPLACEMENT DE L'ENFANT (2023-02-15) ; 68 articles indexés, 68 citables ; lecture AUCUNE ; référence PARTIELLEMENT_VERIFIE ; source https://famille.gouv.ci/uploads/publications/176937624358.pdf.
- 2023-90 — DECRET No 2023-90 DU 15 FEVRIER 2023 PORTANT REGLEMENTATION DES FAMILLES D'ACCUEIL (2023-02-15) ; 21 articles indexés, 21 citables ; lecture AUCUNE ; référence PARTIELLEMENT_VERIFIE ; source https://famille.gouv.ci/uploads/publications/176937670169.pdf.
- 202-894 — LOI n° 202-894 du 21 décembre 2021 relative aux mesures de protection des victimes de violences domestiques. de viol et de violences sexuelles autres que domestiques. (2021-12-21) ; 16 articles indexés, 16 citables ; lecture AUCUNE ; référence PARTIELLEMENT_VERIFIE ; source https://famille.gouv.ci/uploads/publications/176960480223.pdf.
- 2019-779 — DÉCRET No 2019-779 portant création, attributions, organisation et fonctionnement du comité interministériel de protection de l’enfant. (date non renseignée) ; 9 articles indexés, 9 citables ; lecture AUCUNE ; référence PARTIELLEMENT_VERIFIE ; source https://famille.gouv.ci/uploads/publications/176937240619.pdf.
- 2020-907 — DECRET No 2020-907 DU 18 NOVEMBRE 2020 PORTANT ATTRIBUTIONS, ORGANISATION ET FONCTIONNEMENT DE L’AUTORITE CENTRALE POUR L’ADOPTION EN COTE D’IVOIRE : DECRET ACACI (2020-11-18) ; 29 articles indexés, 29 citables ; lecture AUCUNE ; référence PARTIELLEMENT_VERIFIE ; source https://famille.gouv.ci/uploads/publications/176936873529.pdf.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Un enfant de mon quartier est maltraité par sa tutrice | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [22] |
| courant | un enfan travaille dans les champs et va pas a l'ecole, c'est du travail des enfants | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [17, 18, 22] |
| clarif | — | sans objet | décrets 2023-89, 2023-90 et loi 2021-894 indexés mais aucune fiche |
| ambigu | je m'inquiète pour un petit | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Comment devenir famille d'accueil ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [22] |
| urgent | un enfant est enfermé et battu chez mes voisins | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [1] |
| abstention | Quel est l'âge minimum pour travailler ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |

**Lacunes** : Décrets 2023-89, 2023-90, 2019-779, 2020-907 et loi « 202-894 » indexés, mais aucune fiche. Loi 2019-572 (minorité) et loi 2015-539 (pupilles) : 0 article indexé.

**Corrections techniques réalisées** : Urgence « enfant enfermé et battu » détectée par un motif dans les deux ordres (enfant… frappé / frappe… les enfants).

**Questions pour un juriste** : Choisir, parmi les décrets et la loi présents, les situations à couvrir en premier (protection de l'enfant).

**Sources à obtenir ou vérifier** : Indexation des lois 2019-572 et 2015-539 déjà présentes.

### 23. Droit OHADA, sûretés et voies d'exécution — PARTIEL

**Code concerné** : routage `core/qualification.py` (`contrats_dettes_commerce`) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** :
- Acte uniforme OHADA (sûretés) — ACTE UNIFORME PORTANT ORGANISATION DES SURETES (OHADA) — Journal Officiel de l'OHADA, 15e annee, n° 22, 15 fevrier 2011 (2011-02-15) ; 228 articles indexés, 228 citables ; lecture CALQUE_TEXTE ; référence VERIFIE ; source https://www.ohada.org/wp-content/uploads/2016/05/JO_OHADA_Journal_officiel_n_22.pdf.

**Situations traitées (fiches)** :
- `CONTRA_1` Définition de la sûreté (OHADA) — article 1, texte Acte uniforme OHADA, référence VERIFIE ; questions : aucune
- `CONTRA_4` Sûretés personnelles et cautionnement (OHADA) — article 4, texte Acte uniforme OHADA, référence VERIFIE ; questions : aucune

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Mon ami m'a demandé de me porter caution pour son prêt bancaire | reussi | étape clarification ; fiches CONTRA_4 ; 0 question(s) ; urgence NORMALE |
| courant | la banque veut saisir ma maison hypotequée | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence ELEVEE ; domaine reconnu [3, 8, 23] |
| clarif | — | sans objet | les fiches CONTRA_1 et CONTRA_4 n'ont pas de question de clarification |
| ambigu | quelqu'un me doit de l'argent | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE |
| hors | Le créancier a fait saisir mon salaire, comment contester la saisie ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence ELEVEE ; domaine reconnu [4, 23] |
| urgent | le commissaire de justice est devant ma porte pour saisir mes meubles | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence CRITIQUE ; domaine reconnu [23] |
| abstention | Combien de temps a le créancier pour vendre les biens saisis ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [23] |

**Lacunes** : Seul l'Acte uniforme portant organisation des sûretés est présent (2 fiches de définition). Acte uniforme sur le recouvrement et les voies d'exécution absent : saisies non couvertes. Aucune question de clarification.

**Corrections techniques réalisées** : Urgence « commissaire de justice devant ma porte » détectée (CRITIQUE) ; « saisir » reconnu ; « sûreté », « OHADA » reconnus.

**Questions pour un juriste** : Relire les fiches CONTRA_1 et CONTRA_4 ; confirmer la version en vigueur de l'Acte uniforme sur les sûretés.

**Sources à obtenir ou vérifier** : Acte uniforme portant organisation des procédures simplifiées de recouvrement et des voies d'exécution.

### 24. Droit international privé et commerce international — NON COUVERT

**Code concerné** : routage `core/qualification.py` (aucune clé de routage dans le moteur) ; reconnaissance `KNOWLEDGE/domaines_24.json` ; fiches `KNOWLEDGE/catalogue.json` ; questions `KNOWLEDGE/questions_clarification.json` ; urgence `core/urgence.py`.

**Références disponibles** : aucune dans le corpus.

**Scénarios exécutés** :

| Type | Récit | Résultat | Observé |
|---|---|---|---|
| simple | Je suis marié avec une étrangère et nous voulons divorcer à l'étranger | reussi | étape clarification ; fiches FAMILL_19 ; 1 question(s) ; urgence NORMALE |
| courant | je veu faire reconnaitre un jugement etranger ici | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [21, 24] |
| clarif | — | sans objet | aucune fiche dans ce domaine : pas de cas de clarification possible |
| ambigu | ma famille est à l'étranger | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [21] |
| hors | Comment faire l'exequatur d'une décision étrangère ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [21, 24] |
| urgent | — | sans objet | domaine sans risque typique pour la sécurité d'une personne |
| abstention | Quel est le délai pour une adoption internationale ? | reussi | étape hors_catalogue ; fiches aucune ; 0 question(s) ; urgence NORMALE ; domaine reconnu [2, 24] |

**Lacunes** : Aucune règle de conflit de lois ; Convention de La Haye 1993 (adoption internationale) présente mais 0 article indexé.

**Corrections techniques réalisées** : « reconnaître un jugement étranger » ne reçoit plus la fiche de reconnaissance d'enfant.

**Questions pour un juriste** : Choisir les textes de référence et les premières situations à couvrir.

**Sources à obtenir ou vérifier** : Règles de conflit de lois applicables ; indexation de la Convention de La Haye de 1993.

## Moteur transversal

| Composant | Constat | Preuve |
|---|---|---|
| Détection du domaine | Corrigée : transport et santé n'avaient aucun mot-clé ; mots vides exclus des troncatures ; les 24 domaines sont nommés même non couverts. Limite : une faute de plus d'une lettre n'est pas reconnue (« expropier », « hypotequée »). | `core/qualification.py`, `core/domaines_vision.py` ; scénarios « courant » |
| Qualification des faits | Faits déclarés, manquants nommés ; jamais « prouvés » sans pièce. | `core/faits.py`, `tests/test_conversation.py` |
| Sélection des fiches | Corrigée : mots entiers, une faute tolérée, déclencheur d'un mot soumis au domaine reconnu, domaine le mieux classé en cas de concurrence. | `core/catalogue.py`, `tests/test_scenarios_reference.py` |
| Questions adaptatives, contradictions, manques | 18 questions sur 16 fiches ; les fiches des domaines 13, 19 et 23 n'en ont aucune ; tours conditionnels ; contradiction récit/réponse confirmée ; manques nommés. | `core/clarification.py`, `tests/test_clarification.py` |
| Urgences | Signalées même sans fiche : vérifié par les scénarios « urgent » hors catalogue des domaines 1, 2, 4, 5, 8, 9, 13, 14, 15, 18, 19, 22 et 23. Motifs manquants ajoutés (enfants frappés, armes, blessure, chantage aux images, exécution en cours, démolition, saisie, menaces). | `core/urgence.py` ; scénarios « urgent » |
| Citations et traçabilité | Citations revalidées au chargement ; contrôle d'abstention : aucun article cité hors des fiches servies, aucun nombre non sourcé dans les lectures, démarches et points à vérifier. | `core/catalogue.py`, `tests/evaluation_24_domaines.py` |
| Faits / règles / interprétations / incertitudes | Sections distinctes ; lectures marquées « pas des citations », statut A_RELIRE_PAR_UN_JURISTE. | `core/conversation.py` |
| Synthèses et courriers | Synthèse et brouillon téléchargeables ; le brouillon n'est pas inclus dans le contrôle d'abstention (gabarit daté, champs À COMPLÉTER). | `core/documents.py`, e2e |
| Orientation humaine sans réponse fiable | Hors catalogue : conclusion impossible, domaine nommé, verrous et urgence affichés. **Aucun annuaire de professionnels** (contacts vérifiés à fournir). | `core/conversation.py`, `web/src/components/Resultats.tsx` |
| Isolation et suppression | Identifiant serveur, cookie signé HttpOnly ; suppression ciblée testée. | `tests/test_clarification.py`, `web/tests/integration` |
| Données personnelles | Rien n'est envoyé à un tiers (modèle de langage désactivé) ; masquage prêt pour le jour où il serait activé. | `core/pseudonymisation.py` |
| Délais, articles, procédures inventés | Aucun observé sur les 136 scénarios exécutés ; garde-fou du guide (nombre absent de l'article refusé). | `tests/test_audit_24_domaines.py`, `tests/test_clarification.py` |

Point d'attention : hors catalogue, la réponse peut lister des **numéros d'articles du domaine** trouvés par la recherche, sous le titre « Articles du domaine, non appliqués à votre question ». Ils ne sont pas cités comme réponse ; un juriste devrait dire si cet affichage est souhaitable.

## Tests exécutés (19/10/2026, espace de travail ; la CI rejoue les mêmes)

| Suite | Réussis | Échoués | Ignorés | Non exécutés |
|---|---|---|---|---|
| Moteur `tests/run_all.py` (dont audit 24 domaines et scénarios de référence) | 425 | 0 | 5 (PDF officiels absents : 3 ; chaîne OCR macOS absente : 2) | — |
| Scénarios d'audit (7 types × 24 domaines) | 136 | 0 | — | 32 sans objet (raison donnée pour chacun) |
| Web unitaires et composants | 55 | 0 | 0 | — |
| Web intégration (moteur réel) | 11 | 0 | 0 | — |
| Web bout en bout (Chromium) | 10 | 0 | 0 | — |
| Sur le Mac du propriétaire | — | — | — | non exécuté (pas d'accès) |

Défaut trouvé **pendant** l'audit et corrigé : une modification de cet audit avait corrompu la table des questions par domaine (erreur interne sur tout récit transport ou santé). Les scénarios l'ont détecté ; un test verrouille désormais cette table.

## Plan priorisé

1. **Relecture juridique** des 24 fiches et 18 questions existantes (domaines 2, 3, 13, 19, 23) — condition pour passer de PARTIEL à un usage public.
2. **Famille (2)** : textes du mariage, du divorce, de la pension et des successions ; indexation de l'état civil, de la minorité et de l'adoption déjà présents.
3. **Logement (3)** : décision sur la source de la loi 2025-221, puis fiches d'expulsion relues.
4. **Travail (4)** : Code du travail officiel, puis fiches licenciement et salaire impayé.
5. **Pénal (5)** : orientation (plainte, garde à vue, droits de la victime), avec verrous humains.
6. **Protection de l'enfant (22)** : fiches sur les textes déjà indexés (décrets 2023, loi « 202-894 »).
7. **OHADA (23)** : Acte uniforme sur le recouvrement et les voies d'exécution.
8. **Numérique (14) et rural (18)** : exemplaires lisibles pour lever la neutralisation ou recouper l'OCR.
9. Questions de clarification pour les fiches qui n'en ont pas (13, 19, 23).
10. Les autres domaines, au rythme des textes obtenus.

## Inventaire

L'inventaire complet (textes avec titre, numéro, date, articles indexés et citables, mode de lecture, état de la référence, source ; fiches ; questions ; scénarios) est dans `reports/inventaire_24_domaines.json`, régénérable par `python3 bin/audit_domaines.py`.

