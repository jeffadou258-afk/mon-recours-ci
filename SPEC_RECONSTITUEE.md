# SPÉCIFICATION RECONSTITUÉE — Mon Recours CI

Statut : **reconstitution**, pas un document d'origine. Établie le 19 octobre 2026
à partir des seuls documents réellement consultés (liste au § 1). Chaque exigence
indique sa source. Ce qui n'a pas de source est marqué **HYPOTHÈSE À VALIDER**.

---

## 1. Ce qui a été retrouvé, et ce qui manque

| Document | Où | Nature |
|---|---|---|
| `AGENT_SPEC.md` | racine du dépôt | spécification de l'agent **tel qu'il existait** (identité, mission, domaines A→L, permissions, verrous humains, critères) |
| `SYSTEM_PROMPT.md` | racine | spécification de **comportement** d'une future couche conversationnelle (structure de réponse en 6 parties, questions) |
| `SAFETY_RULES.md` | racine | 10 règles non négociables, chacune liée au module et au test qui la font respecter |
| `WORKFLOW.md`, `WORKFLOWS/01…05` | racine | 5 étapes de traitement d'une demande, 4 étapes de constitution du corpus |
| `EVALUATION_TESTS.md` | racine | familles de tests, 14 épreuves par domaine, limites des tests |
| `CLAUDE_HANDOFF.md` | racine | contrats d'API, stratégie LLM (§ 6), recommandations d'interface |
| `KNOWLEDGE/00_AGENT_CONFIG.md`, `03_MODELE_METADONNEES.md` | `KNOWLEDGE/` | invariants, seuils, modèle de provenance |
| Document de vision (domaines A→X, 24 domaines) | transmis dans la conversation du 17/10/2026 | vision produit cible |
| Décisions du 17/10/2026 (priorités 1 à 4) | transmises dans la conversation | ordre de travail |
| Mission globale du 19/10/2026 | transmise dans la conversation | parcours en 13 étapes, critères de fin |

**Introuvables :**

* la **spécification d'origine numérotée** (§ 1 à § 16 au moins) que le code cite
  (`core/evidence.py` « spec §16 », `core/base.py` « §7.C, §7.D, §10.1-3 »,
  `core/garde_fous.py` « §10 et §14 », `core/urgence.py` « §5 et §12 »…). Elle
  n'est ni dans le dépôt, ni dans son historique Git (un seul commit d'origine) ;
* `references/couche-conversationnelle.md` : aucun dossier `references/` n'existe,
  sur aucune branche.

Les exigences ci-dessous sont donc **reconstituées** à partir de ce que ces
fichiers en reprennent.

## 2. Mission et identité (AGENT_SPEC § 1-2, vision § 2)

* Premier niveau d'information juridique et d'orientation pour toute personne
  vivant en Côte d'Ivoire, en français simple. Ni avocat, ni notaire, ni huissier.
* Répondre à : que dit la loi ; quel texte et quel article le prouvent ; quels droits
  et obligations au vu des faits ; que faire et dans quel ordre ; vers qui se tourner.
* Si les sources ne permettent pas de conclure : `CONCLUSION_IMPOSSIBLE`, dit
  clairement.

## 3. Parcours utilisateur (mission du 19/10, SYSTEM_PROMPT)

1. Comprendre l'utilité du service. 2. Décrire librement le problème.
3. Répondre à des questions adaptées (peu, seulement celles qui changent la
réponse — SYSTEM_PROMPT « Poser des questions »). 4. Analyse fondée sur les faits.
5. Explication des règles. 6. Sources consultables. 7. Options et recours.
8. Plan d'action. 9. Pièces à réunir. 10. Courriers préparés. 11. Consultation et
téléchargement des documents. 12. Orientation vers un professionnel.
13. Retrouver son dossier de manière sécurisée **si le suivi est prévu**.

Structure de réponse (SYSTEM_PROMPT) : ce que je comprends · ce que dit le droit ·
comment cela s'applique · ce que vous pouvez faire · points à vérifier · sources.

## 4. Règles de fiabilité (SAFETY_RULES § 1-3, mission § 5)

* Aucune invention : article, jurisprudence, délai, procédure, adresse, téléphone.
* Une interprétation n'est jamais présentée comme une citation.
* Distinguer : faits déclarés · faits à vérifier · règles sourcées · interprétations ·
  hypothèses · informations manquantes.
* Articles OCR non recoupés : jamais présentés comme vérifiés ; documents
  neutralisés (`articles_fiables = 0`) : jamais cités.
* Aucun contournement de paywall ou d'authentification (SAFETY_RULES § 8).

## 5. Couche conversationnelle (CLAUDE_HANDOFF § 6, mission § 4)

* Le moteur déterministe reste **l'autorité** : un modèle de langage propose, le
  moteur vérifie (citation présente dans l'article, énoncé non dépassant).
* Le modèle est branché **en amont** : comprendre le récit, choisir parmi les
  fiches existantes, formuler des questions, repérer contradictions et manques.
  Il ne crée jamais de `ref_id` ni de citation.
* Clé uniquement côté serveur, en variable d'environnement. Repli déterministe
  explicite tant qu'aucun fournisseur n'est configuré. Aucune dépense sans accord.

## 6. Domaines

La taxonomie a changé entre les documents (voir § 9, contradiction 1). Cible :
les 24 domaines de la vision. Un domaine n'est **activé** pour les utilisateurs
qu'avec des sources fiables, des tests et un statut de validation explicite.
`TERMINE_ET_VERIFIE` exige une relecture humaine tracée (AGENT_SPEC § 10).

## 7. Permissions et verrous (AGENT_SPEC § 6-8, SAFETY_RULES § 4, 6)

* Lire, écrire des brouillons : oui. Envoyer, supprimer de façon autonome, déployer : non.
* Verrou humain obligatoire : danger, violence, menace, pénal ou détention,
  expulsion imminente, enfant ou personne vulnérable, délai proche ou dépassé,
  perte importante de droits, sources contradictoires, texte essentiel absent,
  besoin de représentation, action irréversible. Un verrou ne se ferme jamais seul.

## 8. Sécurité et confidentialité (SAFETY_RULES § 5, CLAUDE_HANDOFF § 6 quinquies)

* Moteur sur 127.0.0.1, clé d'API, limitation de débit, corps borné.
* Aucun chemin de fichier ni identifiant interne transmis au navigateur.
* Données personnelles minimisées. **Durée de conservation : NON DÉCIDÉE**
  (décision du propriétaire, question H7 de l'audit).

## 9. Contradictions relevées entre documents, et résolution proposée

| # | Contradiction | Résolution proposée |
|---|---|---|
| 1 | AGENT_SPEC : 12 domaines A→L. Vision : 24 domaines A→X, lettres différentes (ex. « G » = pénal d'un côté, consommation de l'autre). | Garder les clés de routage du moteur ; ajouter une **table de correspondance** vision → moteur ; la vision est la cible, AGENT_SPEC l'état. Ne jamais citer une lettre sans préciser la nomenclature. |
| 2 | AGENT_SPEC § 12 : « Interface web : n'existe pas ». | Périmé : l'interface existe (`web/`). AGENT_SPEC décrit l'état au 17/10 au matin ; il n'est pas réécrit, la présente reconstitution fait foi pour l'état courant. |
| 3 | AGENT_SPEC / SYSTEM_PROMPT : « aucun modèle de langage ». Vision : assistant conversationnel intelligent. | Compatibles par le contrat de `core/llm.py` : le modèle propose, le moteur valide. Activation = décision du propriétaire (coût, données envoyées à un tiers). |
| 4 | Nombres périmés (279 / 371 tests, 1 777 articles, 13 fiches) dans AGENT_SPEC, README, rapports générés. | Les rapports se régénèrent par leurs scripts ; les nombres à jour sont donnés par `GET /sante` et la CI. |
| 5 | Mission : « retrouver son dossier si le suivi est prévu » ; aucune décision sur les comptes. | **HYPOTHÈSE À VALIDER** : pas de compte pour le pilote ; le dossier reste lié à la session du navigateur ; l'usager peut le supprimer. |

## 10. Hypothèses à valider par le propriétaire

1. Pas de compte utilisateur pour le pilote (§ 9, ligne 5).
2. Durée de conservation des récits (aucune valeur retenue tant que non décidée).
3. Choix et budget d'un fournisseur de modèle de langage.
4. Liste de contacts d'orientation vérifiés (aucun numéro ni adresse inventés).
5. Juriste chargé de la relecture des fiches et des questions de clarification.
