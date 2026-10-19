# Mon Recours CI — Agent juridique et d'assistance citoyenne

**Version 0.4.0** · Côte d'Ivoire · français simple · `agent-juriste-ci`

Un premier niveau d'assistance juridique numérique : comprendre une situation,
identifier les textes applicables **quand ils sont enregistrés et vérifiés**,
connaître les démarches envisageables, préparer des écrits, orienter vers un
professionnel compétent.

L'agent **n'est pas** avocat, magistrat, huissier ni autorité administrative. Il
ne représente personne et ne garantit aucun résultat.

---

## Ce qui est prouvé, et ce qui ne l'est pas

| Élément | Statut |
|---|---|
| Suite de tests | **371 tests, 371 OK, exit 0** (`python3 tests/run_all.py`) |
| Corpus toutes matières | **26 documents**, **1 777 articles**, intégrité `INTEGRE` |
| Domaines couverts | **3** `TERMINE_TECHNIQUEMENT` (logement · entreprises/OHADA · transport) · **2** `CORPUS_PARTIEL` (famille · numérique) · **6** `BLOQUE_SOURCE` |
| Provenance du texte | **1 111 `CALQUE_TEXTE`** · **666 `OCR_AUTO`** · **0 `VERIFIE_MANUELLEMENT`** |
| Références en état `VERIFIE` | **4** (Code Construction/Habitat · Code Urbanisme/Foncier · Acte uniforme OHADA sûretés · décret 2013-711) |
| Couverture par domaine | tableau **calculé** : `KNOWLEDGE/INVENTAIRE_COUVERTURE.md` |
| Validation juridique | **aucune** — `TERMINE_ET_VERIFIE` est refusé tant qu'aucun article n'a été relu par un humain |
| Envoi de courrier | **impossible** : aucune fonction d'envoi dans le code (vérifié par lecture de l'AST) |
| Interface conversationnelle | **opérationnelle et déterministe** — `core/conversation.py`, 13 fiches validées contre le corpus, CLI `bin/dialogue.py` |
| Serveur HTTP | **local et testé** — `bin/serveur_api.py` (127.0.0.1, clé obligatoire, débit, journal sans données personnelles) ; **non exposé, non déployé** |
| Mode LLM | **interface et adaptateur écrits, NON opérationnels** — `llm.statut()["operationnel"] == False`, aucun appel réel, aucune clé dans le code |
| Modèle de langage | **aucun en service** : le cœur et la conversation sont déterministes |
| Seuils de réussite chiffrés | **non définis** (prévu avant bêta) |

> **Le corpus n'est ni complet ni à jour au-delà de la date de consultation.**
> Il contient ce qui a pu être téléchargé sur un domaine public les 16 et
> 17 octobre 2026. Les textes postérieurs, les modifications non republiées et
> les textes non numérisés n'y sont pas.
>
> **Un texte lu par machine n'est pas un texte relu par un humain.** Aucun
> article ne porte `VERIFIE_MANUELLEMENT` : ce nombre est **zéro**, et deux tests
> verrouillent ce zéro. Le statut `TERMINE_ET_VERIFIE` est **inatteignable**
> aujourd'hui, et `core/couverture.py` refuse de le rendre.

---

## Installation

**Démarrage complet (moteur + interface web) sur un Mac ou un poste Linux :**

```bash
bash scripts/demarrer-local.sh            # puis ouvrir http://localhost:3000
bash scripts/demarrer-local.sh --tests    # contrôles complets avant démarrage
```

État du produit, matrice de conformité et limites : `RAPPORT_PRODUIT.md`.
Spécification reconstituée : `SPEC_RECONSTITUEE.md`.

Runtime : **Python 3.9+ et la bibliothèque standard** (`sqlite3`, `urllib`,
`ssl`, `json`, `unittest`). Aucune dépendance obligatoire pour faire tourner
l'agent.

Collecte uniquement : `pypdf`, installé dans un venv dédié (`.venv-corpus/`).
Le runtime n'en a pas besoin, puisque les textes extraits sont conservés en
clair à côté des PDF.

Optionnel : `fpdf2` pour l'export PDF des brouillons. Sans lui, l'échec PDF est
**déclaré** dans le résultat, jamais masqué.

```bash
cd /Users/mac/mon_recours_ci

# --- vérification complète -------------------------------------------------
python3 tests/run_all.py                 # suite complète, verdict factuel
python3 bin/verifier_sources.py          # requêtes HTTP réelles sur les 8 sources
python3 bin/verifier_sources.py --rapport  # lecture de l'historique, sans réseau
python3 bin/demonstration.py             # les 5 étapes sur 3 situations réelles

# --- corpus juridique ------------------------------------------------------
./.venv-corpus/bin/python bin/collecter_corpus.py         # (re)collecte logement + indexation
./.venv-corpus/bin/python bin/collecter_corpus.py --etat  # état du corpus, sans réseau
./.venv-corpus/bin/python bin/collecter_domaine.py --domaine famille_mariage_filiation
python3 bin/collecter_domaine.py --domaine famille_mariage_filiation --etat
python3 bin/ocr_collecter.py --domaine famille_mariage_filiation   # OCR d'un domaine
python3 bin/ocr_collecter.py --etat       # provenance des textes, sans réseau
python3 bin/demonstration_corpus.py       # réponse documentée de bout en bout

# --- couverture et rapports ------------------------------------------------
python3 bin/rapport_couverture.py         # inventaire + rapport de mission (rejoue les tests)

# --- couche conversationnelle ---------------------------------------------
python3 bin/dialogue.py --catalogue       # ce que le catalogue sait traiter (fiches validées)
python3 bin/dialogue.py --dossier D1 --demande "Mon bailleur garde ma caution."
python3 bin/dialogue.py --dossier D1 --reponses logement=oui
python3 bin/dialogue.py --fichier D1      # relit l'état de la conversation
```

## Documents de référence

| Document | Contenu |
|---|---|
| `AGENT_SPEC.md` | identité, périmètre A→L, architecture, permissions, human gate, critères de réussite |
| `SAFETY_RULES.md` | les règles non négociables, avec le module et le test qui les tiennent |
| `SYSTEM_PROMPT.md` | comportement attendu d'une future couche conversationnelle (**non chargé aujourd'hui**) |
| `WORKFLOW.md` | les 5 étapes d'une demande, les 4 étapes du corpus, le cycle de vie d'un domaine |
| `KNOWLEDGE_SOURCES.md` | sources officielles, obstacles constatés, pièges de collecte |
| `EVALUATION_TESTS.md` | les 14 épreuves exigées, les défauts trouvés, ce qu'un test vert ne prouve pas |
| `CLAUDE_HANDOFF.md` | reprise technique : contrats d'entrée/sortie, modèle de données, interface, LLM |
| `KNOWLEDGE/INVENTAIRE_COUVERTURE.md` | **fiches par domaine** : statut, périmètre, sources, lacunes |

---

## Structure

```
mon_recours_ci/
├── config.py                 chemins, énumérations, registre des sources (AUCUNE règle de droit)
├── agent.py                  orchestrateur MonRecoursCI (5 étapes)
├── core/
│   ├── garde_fous.py         refus typés (PREUVE_FABRIQUEE, MENACE, FRAUDE, GARANTIE_RESULTAT…)
│   ├── urgence.py            CRITIQUE / ELEVEE / NORMALE — sécurité d'abord
│   ├── qualification.py      routage par domaine + questions ciblées
│   ├── faits.py              statuts préservés, pièces, informations manquantes
│   ├── sources.py            vérification HTTP réelle (seul module réseau du cœur)
│   ├── base.py               corpus SQLite, métadonnées obligatoires, états de vérification
│   ├── corpus.py             documents téléchargés, empreintes, articles indexés
│   ├── analyse.py            analyse structurée + validation anti-invention
│   ├── ocr.py                politique OCR : similarité, seuils, verdicts, provenance
│   ├── plan_action.py        plan, orientations, verrous humains
│   ├── documents.py          brouillons de courriers — jamais envoyés
│   └── evidence.py           dossier de traçabilité (§16)
├── KNOWLEDGE/
│   ├── 00_AGENT_CONFIG.md     identité, invariants, limites
│   ├── 01_SOURCES_OFFICIELLES.md  registre + résultats mesurés + obstacles constatés
│   ├── 02_CORPUS/README.md    procédure d'ajout d'une référence
│   ├── 03_MODELE_METADONNEES.md   champs obligatoires et pourquoi
│   ├── 04_CORPUS_LOGEMENT_BAUX_FONCIER.md  ce qui est prouvé, ce qui manque
│   ├── 05_LACUNE_LOI_2025_221.md  recherches menées, sources essayées, lacune conservée
│   ├── CORPUS/                PDF officiels + textes extraits + textes OCR + rapport
│   ├── corpus_juridique.sqlite3   base (références, documents, articles)
│   └── verifications_sources.json journal des vérifications de sources
├── WORKFLOWS/01…05/etape.md    les cinq étapes détaillées
├── DOSSIERS/<dossier_id>/     DOSSIER_EN_COURS.json, DOSSIER_TRACABILITE.json, BROUILLONS/
├── tools/ocr_pdf.swift        outil OCR (Vision + PDFKit), compilé par le collecteur
├── bin/                       verifier_sources.py, demonstration.py, collecter_corpus.py,
│                              ocr_collecter.py, demonstration_corpus.py
└── tests/                     13 fichiers, 232 tests
```

---

## Les quatre invariants tenus par le code

1. **Aucune conclusion sans référence vérifiée.**
   `core.analyse.peut_conclure` refuse de conclure sans règle appuyée sur une
   référence du corpus et sans application aux faits. Sur un corpus vide,
   l'agent répond `CONCLUSION_IMPOSSIBLE` : il **dit** qu'il ne sait pas.

2. **Aucune analyse non conforme ne sort.**
   `core.analyse.exiger_conformite` lève. Codes de refus :
   `REGLE_SANS_SOURCE`, `REF_INCONNUE`, `REF_VIDE`, `APPLICATION_SANS_REGLE`,
   `APPLICATION_SANS_FAIT`, `HYPOTHESE_SANS_CONDITION`,
   `CITATION_NON_VERIFIABLE`, `INCERTITUDE_NON_DECLAREE`, `NOMBRE_NON_SOUTENU`,
   `DOMAINE_INDETERMINE`.

3. **Aucun envoi, aucune représentation.**
   `core/documents.py` ne contient aucune fonction d'envoi ; un test lit le
   fichier source et le prouve. Les brouillons portent « BROUILLON — NON ENVOYÉ ».

4. **Ce qui manque est nommé.**
   Le dossier de traçabilité porte `champs_non_renseignes` : la liste explicite
   des zones aveugles, jamais omises. Un document non lisible porte
   `note_qualite = "scan sans calque texte — OCR requis"`.

5. **Un texte lu par machine porte sa provenance, partout.**
   Chaque article est marqué `CALQUE_TEXTE` ou `OCR_AUTO`. Une règle appuyée sur
   un article OCR **non recoupé** sans incertitude déclarée est refusée
   (`PROVENANCE_OCR_NON_DECLAREE`) : une reconnaissance automatique ne peut pas
   se lire comme une lecture de document. Un scan ne devient jamais un document
   à calque texte (`calque_texte` reste 0 après OCR), et un article OCR sous le
   seuil de qualité est **écarté**, jamais indexé en silence.

---

## La chaîne de preuve, jusqu'à l'article

```
document PDF  →  SHA-256 du fichier        (recalculé à chaque contrôle d'intégrité)
              →  référence juridique        (etat_verification + preuve_url + empreinte + date)
              →  article indexé             (numéro + texte + SHA-256 du texte)
              →  règle de l'analyse         (articles="Article 416")
              →  dossier de traçabilité     (articles_effectivement_verifies)
```

Le contrôle décisif est `core.corpus.verifier_regle_article(ref_id, numéro,
énoncé)` : il compare les nombres de l'énoncé **au seul texte de l'article
cité**. C'est lui qui refuse « le plafond est de 95000 FCFA par trimestre » sur
l'article 423.

`NOMBRE_NON_SOUTENU` reste en place, mais son pouvoir discriminant **baisse
quand la référence porte le texte intégral d'une loi** (290 000 caractères) : un
petit nombre finit par y apparaître quelque part. C'est mesuré, documenté, et
compensé par le contrôle au niveau de l'article.

---

## Défauts réels, trouvés par les tests et par les démonstrations

1. **Un filtre large frappait la victime.** Le motif `MENACE` refusait « mon
   mari menace de me tuer ». Les motifs `MENACE` et `VIOLENCE` exigent désormais
   un marqueur de **demande** (*aide*, *écris*, *rédige*, *je veux*…). Six
   témoins légitimes verrouillent ce comportement.
2. **Les apostrophes typographiques étaient supprimées** par la normalisation :
   « d'habitation » devenait « dhabitation ». Recherche et citation cassées sur
   les expressions les plus courantes du domaine.
3. **Espaces parasites dans les références numériques.** Le PDF officiel livre
   « la loi 99 -478 ». Une citation pourtant exacte était déclarée **absente**.
4. **Le verbe « expulser » n'était pas détecté** comme urgence élevée — seul le
   nom « expulsion » l'était. Or un locataire écrit « il va me faire expulser ».
5. **Les faits disparaissaient** de la section « distinction » du dossier de
   traçabilité — trouvé par `bin/demonstration.py`, pas par les tests.
6. **Les marqueurs de page de l'OCR entraient dans le texte des articles.**
   `--- PAGE 3 ---` se retrouvait au milieu de l'article 2 de la loi 98-750,
   donc dans une citation potentielle. Retirés à l'extraction.
7. **Mon propre contrôle de qualité refusait un texte valide.** Le seuil
   `minimum_articles=5` rejetait la **loi 2020-623, qui compte légitimement deux
   articles** (c'est une loi de ratification). Le seuil est devenu un plancher
   explicite, et un test verrouille ce cas.
8. **La recherche ne comprenait pas les mots du citoyen.** Score = comptage de
   sous-chaînes, sans stopwords ni racines : « il va me faire **expulser** » ne
   trouvait pas l'article 445 (« **expulsion** »), et le mot « faire » ramenait
   des dizaines d'articles hors sujet. Corrigé par fragments de tête (4–6
   lettres) + pondération IDF. Une variante de classement a été **essayée puis
   rejetée sur mesure** (11 → 9 articles attendus bien placés).
9. **Le même article s'affichait deux ou trois fois** : il existe dans deux
   exemplaires officiels du texte, plus sa version OCR. Les doublons sont
   désormais résolus (clé = texte + numéro), le nombre d'exemplaires est
   signalé, et la **lecture de document** l'emporte sur l'OCR.
10. **« caution » ne désigne pas le dépôt de garantie dans le Code.** Le mot y
    renvoie au cautionnement — un autre contrat. Une table de vocabulaire
    explicite (`SYNONYMES_RECHERCHE`) fait le pont, et un test prouve que ce pont
    fonctionne *et* que les deux notions restent distinctes.
11. **Un témoin de test mentait.** Le premier test de la régression `autojunk`
    utilisait deux textes presque identiques : l'écart mesuré était nul, le test
    passait sans rien prouver. Remplacé par un témoin à graine fixe où l'écart
    est réel (0,00 contre 0,26), plus une égalité exacte avec la méthode
    `autojunk=False`.
12. **Trois de mes tests de phase 3 étaient faux**, pas le code : citation sans
    guillemets, incertitude déjà déclarée avant l'assertion, et un article
    inexistant créé sans son document (clé étrangère). Corrigés après diagnostic.

---

## Limites assumées

- **Couverture partielle.** Les cinq textes du domaine sont désormais
  exploitables, mais **par deux méthodes de lecture différentes** :
  `CALQUE_TEXTE` pour 855 articles, `OCR_AUTO` pour 318. **Aucun article n'a été
  relu par un humain** (`VERIFIE_MANUELLEMENT` = 0). Deux documents OCR sur trois
  (loi 98-750, loi 2020-623) n'ont **aucune copie de référence** : leur qualité
  n'est pas mesurable, seulement contrôlée structurellement.
- **La loi n° 2025-221 du 28 mars 2025** (contentieux des baux et exécution des
  expulsions) n'est **pas** dans le corpus : aucun exemplaire sur un domaine
  `*.gouv.ci` n'a été localisé. C'est la lacune la plus significative du domaine.
  Les recherches menées, source par source, sont conservées dans
  `KNOWLEDGE/05_LACUNE_LOI_2025_221.md`. Ce qui **est** établi : le communiqué du
  Conseil des ministres du 12 juin 2024 annonce un projet de loi sur ce sujet —
  sans numéro de texte, donc sans valeur de droit applicable.
- **Le classement de la recherche reste imparfait** : l'article 3 (définitions)
  est un article long qui remonte sur beaucoup de requêtes ; le score IDF ne le
  pénalise pas assez. Les articles attendus sont présents, pas toujours en tête.
- **La loi 2020-623 est une mesure temporaire** (suspension des expulsions du
  1er avril au 30 juin 2020, contexte covid-19). Elle est intégrée avec sa limite
  d'interprétation écrite, et un test vérifie que cette limite est présente.
- **L'état de vigueur** est vérifié à la date de consultation, jamais au-delà.
- **Le Journal officiel** (`sgg.gouv.ci/jo.php`) est derrière un identifiant, et
  le CNDJ facture l'accès à ses codes (10 000 FCFA/an ou /mois). Aucun
  contournement n'a été tenté.
- **Aucune suppression** ; pas d'interface web ; pas de comptes ; pas de
  persistance multi-utilisateurs au-delà du cloisonnement par dossier sur disque.
- La numérotation de la loi 2020-624 **saute l'article 151 dans le document
  publié** : constat vérifié, documenté et verrouillé par un test.

---

## Contraintes éthiques encodées

Ne jamais inventer une loi, un article, un jugement, un délai ou une procédure ·
ne jamais présenter une interprétation comme une citation · ne pas affirmer
qu'un texte est en vigueur sans vérification · ne pas garantir de résultat · ne
pas se présenter comme un professionnel habilité · ne pas aider à menacer,
frapper, frauder, détruire des preuves ou en fabriquer · respecter la
confidentialité (dossiers cloisonnés) · signaler les limites · ne pas
transformer coutume ou conviction en obligation légale.

Chaque refus porte un code, le motif détecté cité tel quel, et une **voie sûre**
proposée.
