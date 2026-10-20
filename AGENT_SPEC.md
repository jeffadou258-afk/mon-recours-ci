# AGENT_SPEC — Mon Recours CI (`agent-juriste-ci`)

Spécification de l'agent tel qu'il **existe réellement** dans
`/Users/mac/mon_recours_ci/`, pas tel qu'on aimerait qu'il soit. Chaque
affirmation de ce document est vérifiable par une commande citée.

---

## 1. Identité

| Champ | Valeur |
|---|---|
| Nom | Mon Recours CI |
| Nom technique | `agent-juriste-ci` |
| Pays de référence | Côte d'Ivoire |
| Langue | français simple et accessible |
| Public | toute personne vivant en Côte d'Ivoire, sans distinction de niveau d'instruction |
| Rôle | premier niveau d'information juridique et d'orientation citoyenne |
| Ce qu'il n'est pas | ni avocat, ni notaire, ni huissier, ni magistrat, ni autorité administrative |

## 2. Mission

Répondre à cinq questions, dans cet ordre :

1. Que dit la loi dans ma situation ?
2. Quel texte et quel article permettent de le vérifier ?
3. Quels sont mes droits et obligations, au vu des faits connus ?
4. Que puis-je faire concrètement, et dans quel ordre ?
5. Vers qui me tourner si une intervention humaine est nécessaire ?

La formulation « voici ce que la loi ivoirienne dit » n'est employée **que**
lorsque les sources disponibles permettent réellement de la justifier. Sinon
l'agent répond `CONCLUSION_IMPOSSIBLE` — il **dit** qu'il ne sait pas.

## 3. Périmètre de domaines (taxonomie A→L)

`config.COUVERTURE_DOMAINES` fait correspondre la nomenclature de la mission aux
12 clés de routage internes. L'état réel de chaque domaine est calculé, jamais
déclaré : voir `KNOWLEDGE/INVENTAIRE_COUVERTURE.md`.

| Code | Domaine | Statut technique mesuré |
|---|---|---|
| A | Logement, baux et foncier | `TERMINE_TECHNIQUEMENT` — 1 173 art., 2 réf. `VERIFIE` |
| B | Famille, couple et enfants | `CORPUS_PARTIEL` — 15 docs, 191 art., 0 réf. `VERIFIE` (5 scans refusés par l'OCR) |
| C | Travail, emploi | `BLOQUE_SOURCE` |
| D | Entreprises, commerce (OHADA) | `TERMINE_TECHNIQUEMENT` — acte uniforme sûretés, 228 art. |
| E | Dettes, argent, consommation | `BLOQUE_SOURCE` |
| F | Administration et documents officiels | `BLOQUE_SOURCE` |
| G | Pénal, plaintes, procédures | `BLOQUE_SOURCE` |
| H | Religion, communautés, associations | `BLOQUE_SOURCE` |
| I | Numérique et données personnelles | `CORPUS_PARTIEL` — 3 lois (2013-450, 451, 546), 179 art. OCR, 0 recoupé |
| J | Transport et responsabilité civile | `TERMINE_TECHNIQUEMENT` — décret 2013-711, 6 art. **mais couverture réelle très étroite** |
| K | Santé et droits des usagers | `BLOQUE_SOURCE` |
| L | Domaines transversaux | aiguillage, pas de corpus |

## 4. Architecture réelle

```
agent.py                  orchestrateur MonRecoursCI (5 étapes, API unique)
config.py                 chemins, énumérations, registre des sources — AUCUNE règle de droit
core/
  garde_fous.py           refus typés (PREUVE_FABRIQUEE, MENACE, FRAUDE, GARANTIE_RESULTAT…)
  urgence.py              CRITIQUE / ELEVEE / NORMALE
  qualification.py        routage par domaine (tolérant aux fautes) + questions ciblées
  faits.py                statuts de faits préservés, pièces, informations manquantes
  sources.py              seul module réseau du cœur : vérification HTTP réelle
  base.py                 références juridiques, métadonnées obligatoires, états de vérification
  corpus.py               documents, empreintes, articles, recherche, provenance
  ocr.py                  politique OCR : similarité, seuils, verdicts
  couverture.py           statut honnête par domaine (technique vs juridique)
  analyse.py              analyse structurée + validation anti-invention
  plan_action.py          plan, orientations, verrous humains
  documents.py            brouillons de courriers — jamais envoyés
  evidence.py             dossier de traçabilité
bin/                      verifier_sources, collecter_corpus, collecter_domaine,
                          ocr_collecter, demonstration, demonstration_corpus,
                          rapport_couverture
tools/ocr_pdf.swift       OCR macOS Vision + PDFKit
tests/                    29 fichiers, 515 tests
```

**Aucun modèle de langage n'est intégré.** Il n'y a ni fournisseur, ni `mock` :
le cœur est déterministe. Le raisonnement juridique est fourni par l'appelant
(humain ou, plus tard, couche conversationnelle) ; le cœur **vérifie** que chaque
affirmation est traçable, et refuse le reste. C'est ce qui rend l'exactitude
vérifiable au lieu d'être affirmée.

## 5. Workflow

Voir `WORKFLOW.md` (5 étapes côté demande, 4 étapes côté corpus).

## 6. Permissions

| Permission | État |
|---|---|
| READ (sources autorisées, documents fournis) | **oui** |
| WRITE (brouillons, analyses, dossiers, corpus) | **oui**, dans l'espace du projet |
| DELETE | **non** — aucune suppression autonome ; les fichiers temporaires des tests sont nettoyés par les tests eux-mêmes |
| SEND (courrier, message, dépôt) | **non** — aucune fonction d'envoi n'existe |
| DEPLOY (mise en service publique) | **non** — aucune fonction de déploiement |

## 7. Human gate

Escalade obligatoire (verrou posé par le code) : danger immédiat, violence,
menace contre une personne, procédure pénale ou détention, expulsion imminente,
enfant ou personne vulnérable, délai de recours proche ou expiré, perte
importante de droits, sources contradictoires, texte essentiel absent, besoin de
représentation professionnelle, action irréversible.

Un verrou humain **ne se ferme jamais seul** : sans marqueur explicite, le code
lève. Détail complet : `SAFETY_RULES.md` § 6.

## 8. Conditions d'arrêt

* source essentielle non vérifiable et réponse qui en dépend ;
* faits manquants empêchant de déterminer la règle applicable ;
* danger immédiat (orientation urgente prioritaire) ;
* demande visant à fabriquer une preuve, frauder, menacer ou contourner la loi ;
* action exigeant une autorisation non donnée ;
* permissions insuffisantes ;
* problème de sécurité ou de confidentialité détecté.

L'agent explique la raison, précise ce qui manque, propose une voie sûre — et
**continue** le reste du travail quand c'est possible.

## 9. Preuves produites

`DOSSIERS/<dossier_id>/DOSSIER_TRACABILITE.json` : demande, résumé neutre,
faits déclarés **et** documentés, questions posées, textes consultés avec URL,
articles effectivement vérifiés (numéro + empreinte SHA-256), distinction
faits/règles/analyse, incertitudes et limites, plan d'action et sa raison,
orientations humaines, contrôles qualité, `champs_non_renseignes`.

`KNOWLEDGE/INVENTAIRE_COUVERTURE.md`, `RAPPORT_FINAL_MISSION.json`,
`KNOWLEDGE/CORPUS/rapport_collecte.json`, `rapport_ocr.json`.

## 10. Critères de réussite

Un domaine n'est `TERMINE_ET_VERIFIE` que si : périmètre documenté, sources et
lacunes recensées, textes correctement référencés, règles de provenance
appliquées, tests présents et verts, refus de conclure fonctionnels, cas à risque
gérés, résultats traçables, documentation à jour **et** relecture humaine tracée.

**Aujourd'hui, cette dernière condition n'est remplie pour aucun domaine.**
`core/couverture.py` refuse de rendre ce statut tant que
`VERIFIE_MANUELLEMENT = 0`.

## 11. Limites assumées

* 9 domaines sur 11 sont `BLOQUE_SOURCE` : les textes ne sont pas accessibles
  librement sur une source officielle.
* Aucun texte n'a été relu par un juriste.
* L'état de vigueur est vérifié à la date de consultation, jamais au-delà.
* Le classement de la recherche reste perfectible (l'article 3, long, remonte
  trop souvent).
* Le périmètre officiel est celui d'un accès **libre** : il exclut
  volontairement les textes derrière authentification ou paywall.

## 12. Correspondance avec la spécification d'origine

| Exigence | État réel |
|---|---|
| Qualification, faits, urgence, routage multi-domaines | **opérationnel** |
| Recherche et citation d'articles réels | **opérationnel** (logement : 1 173 articles) |
| Contrôle de provenance et de vigueur | **opérationnel** |
| Plan d'action, orientations, verrous humains | **opérationnel** |
| Génération de brouillons de courriers | **opérationnel**, jamais envoyés |
| Traçabilité complète | **opérationnel** |
| Couverture de tous les domaines A→L | **NON atteinte** : 1 domaine complet, 1 partiel, 9 bloqués |
| Validation juridique humaine | **non réalisée** |
| Interface web / application | **n'existe pas** — voir `CLAUDE_HANDOFF.md` |
