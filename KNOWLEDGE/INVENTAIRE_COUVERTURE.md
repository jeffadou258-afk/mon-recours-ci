# Inventaire de couverture juridique — Mon Recours CI

Généré le 2026-10-17T02:23:13+00:00 par `bin/rapport_couverture.py`.

**La réussite des tests ne vaut pas validation juridique par un professionnel.** Un domaine `TERMINE_TECHNIQUEMENT` reste `INCOMPLET` au plan juridique : les deux colonnes sont séparées exprès.

| Code | Domaine | Statut technique | Complétude juridique | Documents | Réf. vérifiées | Articles |
|---|---|---|---|---|---|---|
| A | Logement, baux et foncier | `TERMINE_TECHNIQUEMENT` | INCOMPLET | 6 | 2 | 1173 |
| C | Travail, emploi et relations professionnelles | `BLOQUE_SOURCE` | INCONNU | 0 | 0 | 0 |
| B | Famille, couple et enfants | `CORPUS_PARTIEL` | INCOMPLET | 15 | 0 | 191 |
| D | Entreprises, commerce et activites economiques | `TERMINE_TECHNIQUEMENT` | INCOMPLET | 1 | 1 | 228 |
| G | Penal, plaintes et procedures judiciaires | `BLOQUE_SOURCE` | INCONNU | 0 | 0 | 0 |
| E | Dettes, argent et consommation | `BLOQUE_SOURCE` | INCONNU | 0 | 0 | 0 |
| H | Religion, communautes et associations | `BLOQUE_SOURCE` | INCONNU | 0 | 0 | 0 |
| I | Numerique, internet et donnees personnelles | `CORPUS_PARTIEL` | INCOMPLET | 3 | 0 | 179 |
| F | Administration et documents officiels | `BLOQUE_SOURCE` | INCONNU | 0 | 0 | 0 |
| J | Transport, accidents et responsabilite civile | `TERMINE_TECHNIQUEMENT` | INCOMPLET | 1 | 1 | 6 |
| K | Sante et droits des usagers | `BLOQUE_SOURCE` | INCONNU | 0 | 0 | 0 |

**Total** : 26 documents, 1777 articles. Provenance : CALQUE_TEXTE = 1111, OCR_AUTO = 666

## Méthode de comptage

> documents = lignes de la table documents pour le domaine ; articles = lignes de articles_corpus rattachees a ces documents (comptees une par une, pas estimees) ; references = lignes de references_juridiques pour le domaine.

## Ce que le corpus permet, et ce qu'il ne permet pas

La reussite des tests ne vaut PAS validation juridique. Un domaine TERMINE_TECHNIQUEMENT reste juridiquement incomplet.

---

## A — Logement, baux et foncier (`logement_baux_foncier`)

* **Statut technique** : `TERMINE_TECHNIQUEMENT` — 6 document(s), 1173 article(s), 2 reference(s) verifiee(s)
* **Validation juridique** : `RECOMMANDEE` · complétude : `INCOMPLET`
* **Risque** : ELEVE — expulsion, perte du logement, delais de procedure
* **Intervention humaine** : recommandée selon les faits

**Périmètre visé**

- bail d'habitation
- bail professionnel et commercial
- depot de garantie
- avances sur loyers
- revision et paiement des loyers
- reparations
- conge, resiliation et preavis
- impayes et procedures d'expulsion
- propriete immobiliere et titres fonciers
- litiges vendeur/acquereur
- conflits de limites et occupation de terrain
- lotissement et amenagement
- copropriete
- domaine public
- expropriation
- foncier rural et coutumier

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| sgg.gouv.ci | HTTP 200 | portail ; Journal officiel derriere identifiant |
| jorci.oneci.ci | HTTP 503 (maintenance) | aucun Journal officiel consultable |
| biblio.cndj.ci | mur de connexion, acces payant | respecte, non contourne |
| dgi.gouv.ci, construction.gouv.ci, sgg.gouv.ci/photo_doc | PDF telecharges | textes effectivement collectes |

**Lacunes identifiées**

- loi n° 2025-221 (contentieux des baux, execution des expulsions) absente : aucun exemplaire *.gouv.ci — voir KNOWLEDGE/05_LACUNE_LOI_2025_221.md
- textes d'application de la copropriete (decret 2013-225) non collectes
- modificatifs du foncier rural (loi 2019-868, ordonnance 2025-85) non collectes

**Documents indexés**

| Document | Référence | Lecture | Articles |
|---|---|---|---|
| `DOC-BB9AF3E961AF` | — | `TEXTE_NON_JURIDIQUE` | 0 |
| `DOC-4C67C010CD72` | 2020-624 | `CALQUE_TEXTE` | 302 |
| `DOC-FC436680EEE7` | 2020-624 | `OCR_VISION_AUTO` | 287 |
| `DOC-CB3C9F2B2AAC` | 2020-623 | `OCR_VISION_AUTO` | 2 |
| `DOC-814370E4E6D2` | 2019-576 | `CALQUE_TEXTE` | 553 |
| `DOC-9B30C0B1263F` | 98-750 | `OCR_VISION_AUTO` | 29 |

---

## C — Travail, emploi et relations professionnelles (`travail`)

* **Statut technique** : `BLOQUE_SOURCE` — aucun texte collecte : 2 source(s) identifiee(s), aucune exploitable
* **Validation juridique** : `RECOMMANDEE` · complétude : `INCONNU`
* **Risque** : ELEVE — perte de revenus, licenciement
* **Intervention humaine** : recommandée selon les faits

**Périmètre visé**

- contrat de travail
- periode d'essai
- salaire et retenues
- heures supplementaires et conges
- licenciement et demission
- preavis et indemnites
- harcelement et discrimination
- accidents du travail
- conflits employeur/salarie
- stages et apprentissage
- secteur prive / fonction publique / regimes speciaux

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| travail.gouv.ci | injoignable (HTTP 000, DNS) | aucun texte collecte |
| recherche web restreinte aux domaines officiels | aucun exemplaire libre du Code du travail (loi 2015-532) | blocage constate, non contourne |

**Lacunes identifiées**

- Code du travail (loi n° 2015-532) : AUCUN exemplaire officiel libre localise
- convention collective interprofessionnelle : non localisee
- statut de la fonction publique : non localise (page ministerielle = HTML, pas de PDF de texte)

---

## B — Famille, couple et enfants (`famille_mariage_filiation`)

* **Statut technique** : `CORPUS_PARTIEL` — 15 document(s) collecte(s) mais aucun texte integral verifie
* **Validation juridique** : `REQUISE` · complétude : `INCOMPLET`
* **Risque** : CRITIQUE quand des enfants ou des personnes vulnerables sont concernes
* **Intervention humaine** : OBLIGATOIRE

**Périmètre visé**

- mariage civil
- droits et obligations des epoux
- regimes matrimoniaux
- separation et divorce
- pension alimentaire
- autorite parentale
- garde et residence des enfants
- filiation et reconnaissance
- succession et heritage
- donation et partage
- violences familiales
- protection de l'enfance
- adoption

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| famille.gouv.ci (publications) | HTTP 200 — 15 textes juridiques telecharges | corpus effectivement collecte |
| oneci.ci | HTTP 200 | texte de l'etat civil disponible |
| mffe.ci (site famille) | HTTP 200 | meme texte de loi que famille.gouv.ci |

**Lacunes identifiées**

- loi n° 2019-570 (mariage) presente dans les recueils mais pas encore indexee comme texte autonome
- divorce et regimes matrimoniaux : textes non encore identifies sur un domaine officiel
- successions : aucun exemplaire officiel localise (loi 2019-573 non trouvee)
- les deux RECUEILS sont conserves mais volontairement NON indexes : on ne peut pas rattacher une disposition d'un recueil a son texte d'origine avec certitude
- 5 des 11 scans ONT ETE REFUSES par l'OCR, et c'est ecrit sur chaque document : loi 2019-572 (minorite, 58% des articles 1..160), loi 2018-862 (etat civil, 49% des articles 1..113), loi 2015-539 (pupille de l'Etat, 50% des articles 1..54) — ces textes MODIFIENT le Code de la famille et renvoient a des articles d'autres textes : leur decoupage en articles n'est pas fiable. Convention de La Haye (adoption) et loi relative a l'adoption : aucun article n'atteint le seuil de similarite 0,80 face a l'autre copie officielle — divergence a trancher par un humain.
- sur ces 5 textes, aucun article n'est citable : ni la loi sur la minorite, ni celle sur l'etat civil, ni le statut de pupille de l'Etat, ni les textes sur l'adoption. C'est une part importante du perimetre B qui reste hors de portee.

**Documents indexés**

| Document | Référence | Lecture | Articles |
|---|---|---|---|
| `DOC-1EDDBBD930BF` | 2023-90 | `AUCUNE` | 21 |
| `DOC-DAFFEFDC4B7D` | 2023-89 | `AUCUNE` | 68 |
| `DOC-3C674637A31E` | 202-894 | `AUCUNE` | 16 |
| `DOC-F9B2C53EB909` | 2020-907 | `AUCUNE` | 29 |
| `DOC-B722D1F51881` | 2019-571 | `CALQUE_TEXTE` | 0 |
| `DOC-A443F2E78D1D` | 2019-572 | `AUCUNE` | 0 |
| `DOC-6A33514AB7DF` | 2018-862 | `AUCUNE` | 0 |
| `DOC-AC714CEB4E83` | 2018-863 | `AUCUNE` | 26 |
| `DOC-30FD07C1A483` | 2015-539 | `AUCUNE` | 0 |
| `DOC-2CD0D346F0EE` | — | `AUCUNE` | 0 |
| `DOC-CC2B6457296C` | — | `TEXTE_DE_COMPILATION` | 0 |
| `DOC-E8B83E447CA5` | — | `TEXTE_DE_COMPILATION` | 0 |
| `DOC-D098B13E00DA` | — | `CALQUE_TEXTE` | 22 |
| `DOC-D754ACEE8E29` | 2019-779 | `AUCUNE` | 9 |
| `DOC-BEA207BA48BF` | — | `AUCUNE` | 0 |

---

## D — Entreprises, commerce et activites economiques (`contrats_dettes_commerce`)

* **Statut technique** : `TERMINE_TECHNIQUEMENT` — 1 document(s), 228 article(s), 1 reference(s) verifiee(s)
* **Validation juridique** : `RECOMMANDEE` · complétude : `INCOMPLET`
* **Risque** : MOYEN
* **Intervention humaine** : recommandée selon les faits

**Périmètre visé**

- creation et fonctionnement d'entreprise
- societes et entreprise individuelle
- relations entre associes
- contrats commerciaux
- factures et impayes
- recouvrement de creances
- responsabilite contractuelle
- rupture de contrat
- difficultes d'entreprise
- procedures collectives
- droit OHADA et articulation avec le droit ivoirien

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| ohada.org — Journal officiel OHADA n° 22 (15/02/2011) | HTTP 200 — Acte uniforme portant organisation des sûretés, 131 911 caractères extraits, 228 articles indexés | corpus effectivement collecté et vérifié |
| commerce.gouv.ci (publications) | HTTP 200 — agenda des foires 2026 et rapport d'activités 2021 : aucun texte de loi | classés non juridiques, non indexés |
| justice.gouv.ci, gouv.ci | 302 puis 403 sur les pages de publications | aucun texte collecté |

**Lacunes identifiées**

- SEUL l'acte uniforme sur les sûretés est présent. Manquent : AUSCGIE (sociétés commerciales et GIE), AUDCG (droit commercial général), AUPSRVE (recouvrement des créances), AUPC (procédures collectives)
- le Journal officiel OHADA n° 22 publie plusieurs actes : les articles indexés doivent être rattachés à l'acte sur les sûretés, pas aux autres
- aucun texte ivoirien sur l'entreprise individuelle, le registre du commerce ou les difficultés d'entreprise n'est collecté
- la matière des sûretés touche aussi le cautionnement entre particuliers (domaine E) : le classement en droit des affaires est un choix documenté, pas une exclusion

**Documents indexés**

| Document | Référence | Lecture | Articles |
|---|---|---|---|
| `DOC-AB97B11FA7AE` | — | `CALQUE_TEXTE` | 228 |

---

## G — Penal, plaintes et procedures judiciaires (`penal_procedure_penale`)

* **Statut technique** : `BLOQUE_SOURCE` — aucun texte collecte : 2 source(s) identifiee(s), aucune exploitable
* **Validation juridique** : `REQUISE` · complétude : `INCONNU`
* **Risque** : CRITIQUE — liberte individuelle en jeu
* **Intervention humaine** : OBLIGATOIRE

**Périmètre visé**

- vol
- escroquerie
- abus de confiance
- menaces
- violences
- diffamation
- degradations
- cyberinfractions
- depot de plainte
- convocation et audition
- garde a vue
- droits des victimes
- presomption d'innocence
- procedure et juridictions

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| justice.gouv.ci/publications | HTTP 200 mais aucun lien de PDF de texte expose | aucun texte collecte |
| recherche web (loi 2019-574 code penal ; loi 2018-975 procedure penale) | exemplaires seulement sur des sites non officiels | blocage constate, non contourne |

**Lacunes identifiées**

- Code penal (loi n° 2019-574) : AUCUN exemplaire officiel
- Code de procedure penale (loi n° 2018-975) : AUCUN exemplaire officiel
- delais de prescription, de recours et d'appel : non documentes par un texte
- DOMAINE A RISQUE ELEVE : ne jamais conclure sans avocat

---

## E — Dettes, argent et consommation (`consommation`)

* **Statut technique** : `BLOQUE_SOURCE` — aucun texte collecte : 1 source(s) identifiee(s), aucune exploitable
* **Validation juridique** : `RECOMMANDEE` · complétude : `INCONNU`
* **Risque** : MOYEN
* **Intervention humaine** : recommandée selon les faits

**Périmètre visé**

- dettes entre particuliers
- prets et reconnaissances de dette
- creances impayees
- litiges client/commercant
- defaut de livraison
- produits defectueux
- pratiques commerciales contestees
- remboursements
- garanties et engagements

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| recherche web (loi 2016-412 relative a la consommation) | exemplaires trouves uniquement sur des sites non officiels et des depots internationaux (FAO) | blocage constate : une source non officielle ne devient pas un texte verifie |

**Lacunes identifiées**

- loi n° 2016-412 (consommation) : aucun exemplaire officiel ivoirien libre
- dettes civiles / commerciales / fiscales / sociales : distinction non encore adossee a des textes collectes

---

## H — Religion, communautes et associations (`associations_organisations_religieuses`)

* **Statut technique** : `BLOQUE_SOURCE` — aucun texte collecte : 2 source(s) identifiee(s), aucune exploitable
* **Validation juridique** : `RECOMMANDEE` · complétude : `INCONNU`
* **Risque** : MOYEN — neutralite indispensable dans les conflits confessionnels
* **Intervention humaine** : recommandée selon les faits

**Périmètre visé**

- creation et fonctionnement d'association
- gouvernance et responsabilite des dirigeants
- conflits internes
- biens et fonds associatifs
- locaux et contrats
- responsabilite civile
- liberte de religion et ses limites
- obligations de declaration

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| interieur.gouv.ci (publications) | HTTP 200 — decrets de nomination et rapports statistiques, aucun texte sur les associations | aucun texte collecte |
| recherche web (loi 60-315 relative aux associations) | exemplaires seulement sur des sites non officiels | blocage constate, non contourne |

**Lacunes identifiées**

- loi n° 60-315 (associations) : aucun exemplaire officiel collecte
- regime des organisations religieuses : non documente par un texte collecte

---

## I — Numerique, internet et donnees personnelles (`donnees_personnelles_numerique`)

* **Statut technique** : `CORPUS_PARTIEL` — 3 document(s) collecte(s) mais aucun texte integral verifie
* **Validation juridique** : `RECOMMANDEE` · complétude : `INCOMPLET`
* **Risque** : MOYEN a ELEVE
* **Intervention humaine** : recommandée selon les faits

**Périmètre visé**

- escroqueries en ligne
- usurpation d'identite
- menaces numeriques
- diffusion non autorisee de contenus
- protection des donnees personnelles
- comptes compromis
- cyberharcelement
- preuves numeriques

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| autoritedeprotection.ci/lois/ | HTTP 200 — 3 PDF directs : lois 2013-450, 2013-451, 2013-546 (exemplaires du Journal officiel sécurisés en HTTP, pas en HTTPS) | corpus effectivement collecté, lu par OCR (179 articles) |
| telecom.gouv.ci (publications) | HTTP 200 — 2 PDF identiques, tous deux copies du MÊME Journal officiel que celui de l'autorité de protection des données | doublon écarté : le corpus ne référence qu'un exemplaire |
| artci.ci | HTTP 200 | autorité de régulation identifiée, textes d'application à collecter |

**Lacunes identifiées**

- les 3 lois proviennent d'OCR et ne sont RECOUPÉES AVEC AUCUNE autre copie officielle : leur fidélité n'est pas mesurable, seulement contrôlée structurellement. Statut `PARTIELLEMENT_VERIFIE`
- aucun texte d'application (décrets, décisions de l'autorité de protection, règlements de l'ARTCI) n'est collecté : la loi seule ne dit pas comment elle est mise en œuvre
- la loi 2013-451 (cybercriminalité) est un texte PÉNAL : elle engage la liberté des personnes et impose une orientation vers un avocat
- cyberharcèlement, usurpation d'identité en ligne et diffusion non autorisée de contenus ne sont pas adossés à un article spécifique du corpus
- preuves numériques : aucune règle de conservation ou d'identification n'est documentée par un texte collecté

**Documents indexés**

| Document | Référence | Lecture | Articles |
|---|---|---|---|
| `DOC-423816165608` | 2013-546 | `OCR_VISION_AUTO` | 48 |
| `DOC-F9EA35E85B8C` | 2013-450 | `OCR_VISION_AUTO` | 53 |
| `DOC-744992A64543` | 2013-451 | `OCR_VISION_AUTO` | 78 |

---

## F — Administration et documents officiels (`administratif_voies_de_recours`)

* **Statut technique** : `BLOQUE_SOURCE` — aucun texte collecte : 2 source(s) identifiee(s), aucune exploitable
* **Validation juridique** : `REQUISE` · complétude : `INCONNU`
* **Risque** : MOYEN — delais de recours pouvant expirer
* **Intervention humaine** : OBLIGATOIRE

**Périmètre visé**

- actes d'etat civil
- erreurs sur les actes
- documents d'identite
- demandes et recours administratifs
- refus ou silence d'une administration
- autorisations et agrements
- fiscalite declarative
- recours gracieux / hierarchique / juridictionnel

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| onet.gouv.ci / interieur.gouv.ci (etat civil) | rapports statistiques publies, aucun texte de loi expose | aucun texte collecte ; les textes d'etat civil viennent du domaine famille (loi 2018-862, 2018-863) |
| fonctionpublique.gouv.ci | HTTP 200, pages HTML | aucun PDF de texte expose dans le HTML servi |

**Lacunes identifiées**

- code des procedures administratives : non identifie
- textes fiscaux : aucun exemplaire collecte (la DGI publie des loi_finances, non collectees)

---

## J — Transport, accidents et responsabilite civile (`transport_responsabilite_civile`)

* **Statut technique** : `TERMINE_TECHNIQUEMENT` — 1 document(s), 6 article(s), 1 reference(s) verifiee(s)
* **Validation juridique** : `REQUISE` · complétude : `INCOMPLET`
* **Risque** : ELEVE — prejudice corporel
* **Intervention humaine** : OBLIGATOIRE

**Périmètre visé**

- accidents de circulation
- dommages materiels et corporels
- responsabilite civile
- assurance
- litiges avec un transporteur
- contrats de transport
- indemnisation

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| sgg.gouv.ci/photo_doc/ | HTTP 200 — décret n° 2013-711 (téléphone au volant), 4 517 caractères extraits, 6 articles indexés | corpus effectivement collecté et vérifié |
| transports.gouv.ci | HTTP 200 — pages d'information sur la sécurité routière, aucun texte de loi exposé | aucun texte collecté |

**Lacunes identifiées**

- ATTENTION : le domaine n'a qu'UN texte, et il ne porte que sur l'usage du téléphone en conduisant. Il ne dit RIEN sur la responsabilité civile, l'indemnisation des dommages corporels, l'assurance ou les litiges avec un transporteur
- code de la route : non collecté
- régime des assurances (code CIMA) : non collecté
- accidents de circulation : aucune règle de responsabilité adossée à un texte du corpus — le statut technique du domaine ne doit PAS se lire comme une couverture du transport
- écart non tranché : le nom de fichier de la source annonce « décret n° 2013-791 du 20 novembre 2013 », le document porte « n° 2013-711 du 18 octobre 2013 ». C'est le document qui fait foi ; aucun autre exemplaire pour confirmer

**Documents indexés**

| Document | Référence | Lecture | Articles |
|---|---|---|---|
| `DOC-FC471C34DE21` | 2013-711 | `CALQUE_TEXTE` | 6 |

---

## K — Sante et droits des usagers (`sante_droits_usagers`)

* **Statut technique** : `BLOQUE_SOURCE` — aucun texte collecte : 1 source(s) identifiee(s), aucune exploitable
* **Validation juridique** : `REQUISE` · complétude : `INCONNU`
* **Risque** : CRITIQUE — urgence vitale possible
* **Intervention humaine** : OBLIGATOIRE

**Périmètre visé**

- droits des patients
- consentement et information
- reclamations contre un etablissement
- confidentialite des donnees de sante
- responsabilite professionnelle
- voies de recours

**Sources interrogées pendant la mission**

| Source | Résultat mesuré | Usage |
|---|---|---|
| sante.gouv.ci (publications) | HTTP 200 — 2 decrets d'organisation administrative, pas de texte sur les droits des patients | aucun texte utile collecte |

**Lacunes identifiées**

- aucun texte sur les droits des patients collecte
- aucun texte sur la responsabilite medicale collecte
- DOMAINE HORS PORTEE : ne jamais repondre a une question medicale

