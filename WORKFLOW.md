# WORKFLOW — Mon Recours CI

Deux chaînes distinctes, à ne pas confondre :

* la **chaîne de traitement d'une demande** (ce que vit un citoyen), en 5 étapes ;
* la **chaîne de constitution du corpus** (ce que vit un texte), en 4 étapes.

---

## A. Traiter une demande citoyenne

### Étape 1 — Qualification (`core/qualification.py`, `core/urgence.py`)

Entrée : le récit de l'utilisateur, en langage courant. Sortie : domaines
probables, nature de la demande, urgence, ambiguïté.

* Le routage tolère les fautes : troncature (« bai » → « bail ») et une faute de
  frappe (« baeilleur » → « bailleur »), comptées un demi-point.
* L'urgence est détectée **avant** toute analyse : un danger immédiat passe en
  premier.
* `statut == "REFUS"` → **aucune analyse n'est produite**. Chaque refus porte un
  code stable, le motif cité tel quel, et une voie sûre.

### Étape 2 — Faits (`core/faits.py`)

Chaque fait porte un état : `DECLARE_PAR_L_UTILISATEUR`, `DOCUMENTE`,
`MANQUANT`, `A_CONFIRMER`, `ECARTE`.

* Un fait déclaré **n'est jamais** promu documenté sans une pièce réelle
  (nom de fichier + SHA-256 recalculé).
* Ce qui manque est **nommé** (`nommer_manquant`), jamais comblé par défaut.

### Étape 3 — Recherche et vérification (`core/corpus.py`, `bin/verifier_sources.py`)

* `chercher_articles(question, domaine)` : fragments de tête (4–6 lettres) +
  pondération IDF, dédoublonnage des exemplaires multiples.
* `obtenir_article_par_reference(ref_id, numero)` : le texte exact indexé.
* `verifier_integrite()` : recalcule les empreintes sur disque. C'est la preuve
  que rien n'a dérivé.

### Étape 4 — Analyse (`core/analyse.py`)

Une analyse sépare toujours : **règles** (texte), **applications** (faits),
**hypothèses**, **incertitudes**.

`valider()` refuse l'analyse si : règle sans source, référence inconnue ou vide,
application sans règle ou sans fait, hypothèse sans condition, citation non
vérifiable, incertitude non déclarée, nombre non soutenu, provenance OCR non
déclarée.

### Étape 5 — Clôture (`agent.clore_dossier`, `core/plan_action.py`, `core/evidence.py`)

Sortie : `statut_reponse` ∈ {`ANALYSE_CONFORME`, `CONCLUSION_IMPOSSIBLE`,
`ANALYSE_REFUSEE`, `REFUS`}, un plan d'action, un verrou humain si nécessaire, et
`DOSSIER_TRACABILITE.json` avec `champs_non_renseignes` explicitement listés.

Répondre `CONCLUSION_IMPOSSIBLE` est un **résultat correct**, pas un échec.

---

## B. Constituer le corpus d'un domaine

### Étape 1 — Identifier des sources réelles

Recherche restreinte aux domaines officiels, puis **vérification par requête
HTTP** de chaque URL candidate. Aucune URL n'entre dans un manifeste sans avoir
été appelée.

### Étape 2 — Collecter (`bin/collecter_domaine.py --domaine <domaine>`)

Lit `KNOWLEDGE/CORPUS/<DOSSIER>/_sources.json`. Pour chaque source :

1. réutilise le fichier local s'il existe, sinon télécharge ;
2. recalcule l'empreinte SHA-256 (jamais reprise de la source) ;
3. compte polices/images : **zéro police ⇒ aucun texte extractible** ;
4. extrait le texte si calque texte, sinon signale « OCR requis » ;
5. découpe en articles, **contrôle la couverture** (seuil 85 %) ;
6. crée la référence (état `VERIFIE` seulement si texte intégral **et** source
   non-tierce), importe le document, indexe les articles.

Règles appliquées :

* une **compilation** (`recueil`) ne produit **aucune** référence et **aucun**
  article : on ne peut pas rattacher une disposition d'un recueil à son texte
  d'origine avec certitude ;
* un **découpage non fiable** (loi modificative renvoyant aux articles d'autres
  codes) ⇒ **rien n'est indexé**, la référence reste `PARTIELLEMENT_VERIFIE` avec
  le motif ;
* une **reproduction tierce** ⇒ jamais `VERIFIE`, attribution conservée.

### Étape 3 — Lire les scans (`bin/ocr_collecter.py --domaine <domaine>`)

macOS Vision + PDFKit (`tools/ocr_pdf.swift`). Avant toute indexation :

1. **contrôle structurel** si aucune copie de référence n'existe ;
2. **comparaison** à une autre copie officielle si elle existe (similarité avec
   `autojunk=False`, seuil 0,80) ;
3. un article sous le seuil est **écarté**, jamais indexé en silence ;
4. chaque article porte `OCR_AUTO`, sa confiance et son état de recoupement.

### Étape 4 — Mesurer et déclarer (`bin/rapport_couverture.py`)

`core/couverture.py` calcule, par domaine, un statut **technique** et une
**complétude juridique** séparés, à partir des mesures réelles de la base. Les
lacunes et les sources interrogées sont déclarées dans `core/couverture.py`
(`DECLARATIONS`) : elles ne se devinent pas, elles s'écrivent.

Statuts : `TERMINE_ET_VERIFIE` (exige une relecture humaine — **inatteignable
aujourd'hui**), `TERMINE_TECHNIQUEMENT`, `CORPUS_PARTIEL`,
`EN_ATTENTE_VALIDATION_HUMAINE`, `BLOQUE_SOURCE`, `NON_DEMARRE`.

---

## C. Cycle de vie d'un domaine

```
NON_DEMARRE
   │  sources identifiées et appelées
   ▼
BLOQUE_SOURCE  ──(texte obtenu)──►  CORPUS_PARTIEL
                                        │  texte intégral vérifié
                                        ▼
                              TERMINE_TECHNIQUEMENT
                                        │  relecture humaine tracée
                                        ▼
                               TERMINE_ET_VERIFIE   ← jamais atteint à ce jour
```

Un domaine peut stagner en `BLOQUE_SOURCE` durablement : c'est une information
sur l'accès aux sources, pas un aveu d'échec du projet.
