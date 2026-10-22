# PASSATION — Mon Recours CI (reprise par MS)

> **22/10/2026 — conservation 24 h** : préparée sur la branche `feature/conservation-24h`, non installée. Voir `docs/CONSERVATION_24H.md`.

Rédigé le 22/10/2026 à partir du dépôt GitHub `jeffadou258-afk/mon-recours-ci`,
branche `feature/admin-authentification`, commit `a1aa017`, et de l'état réel
des services consultés le même jour. Ce document ne contient **aucun secret**.

Légende utilisée partout :

| Mention | Sens |
|---|---|
| **OPÉRATIONNEL** | fonctionne et a été vérifié par un test exécuté |
| **PRÉPARÉ** | code ou procédure écrits et testés localement, mais pas en service |
| **SIMULÉ** | réponses figées (démonstration), aucun calcul réel |
| **ABSENT** | n'existe pas |
| **À VÉRIFIER** | non vérifiable depuis la session qui a rédigé ce document |

> **Mise à jour du 22/10/2026 (matin).** Avec `fpdf2` installé : moteur
> **580 tests, 0 échec** ; web **104/104**, intégration **14/14** ; CI
> `39746130681` (commit `d22cab4`) entièrement verte, ESLint compris (étape ajoutée). Compatibilité
> serveur Linux, sauvegarde/restauration, architecture, coûts, protection des
> données et plan de relecture : **`docs/PLAN_MISE_EN_PRODUCTION.md`** (fait foi
> sur ces points). État du Mac : `bash scripts/etat-poste.sh` (lecture seule).
> Kit de relecture du lot logement : `KNOWLEDGE/relecture/`.

---

## 1. Résumé du projet

Mon Recours CI est un assistant juridique citoyen pour la Côte d'Ivoire, en
français simple. Une personne décrit sa situation ; le service pose des
questions, cite **mot pour mot** les articles de loi du corpus, indique les
démarches possibles et prépare un brouillon de courrier (PDF), jamais envoyé.

Le cœur est un **moteur juridique Python déterministe** qui refuse de conclure
sans référence vérifiée. Une **interface web Next.js** l'appelle côté serveur.

Il n'est ni avocat ni autorité. **Aucune fiche n'a été relue par un juriste.**

Objectif suivant : passer de la démonstration figée à une **version réellement
fonctionnelle en ligne** (moteur réel, dossiers persistants, HTTPS,
administration), distincte de la démonstration publique.

---

## 2. Architecture technique actuelle

```
Navigateur ──HTTPS──► Next.js 15 (web/)  ──HTTP local + clé──►  moteur Python
                      pages + /api/*                            bin/serveur_api.py
                      cookie de consultation signé              127.0.0.1:8765 seulement
                      administration (/admin)                   │
                                                                ├─ KNOWLEDGE/corpus_juridique.sqlite3
                                                                └─ DOSSIERS/<id>/  (JSON + PDF, sur disque)
```

| Couche | Contenu | Technologie |
|---|---|---|
| Moteur | `agent.py`, `core/*` (qualification, urgence, garde-fous, analyse, conversation, clarification, documents, sources…), `config.py` | Python 3.9+, bibliothèque standard ; `fpdf2` pour le PDF (`requirements.txt`) |
| Serveur du moteur | `bin/serveur_api.py` : écoute **uniquement** sur 127.0.0.1, clé d'API obligatoire, débit global, corps ≤ 64 Ko, journal sans contenu personnel | Python `http.server` (pas ASGI/WSGI) |
| Corpus | `KNOWLEDGE/corpus_juridique.sqlite3` (versionné, 7,2 Mo), `KNOWLEDGE/catalogue.json` (fiches), `KNOWLEDGE/CORPUS/` (textes extraits) | SQLite |
| PDF officiels | **non versionnés** dans les branches de code ; archivés sur la branche orpheline `corpus/archives-pdf` | — |
| Dossiers | `DOSSIERS/<id>/` : `DOSSIER_EN_COURS.json`, traçabilité, brouillons PDF ; droits 700/600 | disque local |
| Interface | `web/src/app` (pages + routes API), `web/src/components`, `web/src/lib/server/*` | Next.js 15.5.28, React 19, TypeScript strict |
| Authentification | `web/src/lib/server/auth/*` | scrypt + cookie HMAC sans état |
| Collecte du corpus | `bin/collecter_*`, `bin/integrer_collecte.py`, `bin/ocr_local.py`, `bin/reconstruire_base.py` | GitHub Actions `collecte-corpus.yml` (manuel / opt-in) |
| CI | `.github/workflows/interface-web.yml` | GitHub Actions |
| Déploiement serveur | `web/deploiement/` : unités systemd moteur / web / purge, `nginx.conf.exemple`, `env.exemple`, `verifier-preproduction.sh` | **PRÉPARÉ**, jamais installé |

### Routes

| Pages | Routes API (serveur Next.js) |
|---|---|
| `/` accueil · `/consultation` · `/comprendre` · `/hors-ligne` · `/connexion` · `/connexion/mot-de-passe-oublie` · `/admin` | `GET /api/sante` · `POST /api/ouvrir` · `POST /api/repondre` · `POST /api/courrier` · `GET /api/courrier/telecharger` · `POST /api/supprimer` · `POST /api/connexion` · `POST /api/deconnexion` |

### Variables d'environnement (noms seulement)

| Côté | Variables |
|---|---|
| Interface | `MONRECOURS_API_URL`, `MONRECOURS_API_KEY`, `MONRECOURS_SESSION_SECRET` (≥ 32 caractères), `MONRECOURS_API_TIMEOUT_MS`, `MONRECOURS_DEBIT_VISITEUR`, `MONRECOURS_MODE` (`demo` = réponses figées et administration fermée), `NODE_ENV`, `PORT`, `HOSTNAME` |
| Administration | `MONRECOURS_COMPTES_FICHIER` (recommandé) **ou** `MONRECOURS_COMPTES` — jamais les deux (administration fermée si ambigu) ; `MONRECOURS_AUDIT_FICHIER` |
| Moteur | `MONRECOURS_API_KEY`, `MONRECOURS_DOSSIERS`, `MONRECOURS_CHEMIN_DB`, `MONRECOURS_PDF_NON_DISTRIBUES` (`1` si les PDF officiels ne sont pas sur la machine) |
| Sauvegarde / purge | `MONRECOURS_CLE_SAUVEGARDE`, `MONRECOURS_JOURNAL_PURGE` |
| Modèle de langage (**désactivé**) | `MONRECOURS_LLM_FOURNISSEUR`, `MONRECOURS_LLM_URL`, `MONRECOURS_LLM_MODELE`, `MONRECOURS_LLM_API_KEY`, `MONRECOURS_LLM_ACCORD_DONNEES` — **ne pas les définir** sans accord écrit du propriétaire |

Gabarits : `web/.env.example`, `web/deploiement/env.exemple` (sans valeurs).

---

## 3. Fonctionnalités : état réel

### 3.1 Moteur juridique Python

| Fonction | État |
|---|---|
| Qualification, urgence (CRITIQUE / ÉLEVÉE / NORMALE), garde-fous typés | **OPÉRATIONNEL** (tests) |
| Conversation déterministe, 92 fiches, questions de clarification | **OPÉRATIONNEL** (tests) — contenu **non relu par un juriste** |
| Citations mot pour mot, contrôle anti-invention, provenance (`CALQUE_TEXTE` / `OCR_AUTO`) | **OPÉRATIONNEL** (tests) |
| Courrier : brouillon + PDF, informations demandées à la personne, jamais envoyé | **OPÉRATIONNEL** si `fpdf2` est installé |
| Recherche documentaire | **OPÉRATIONNEL**, classement imparfait (article attendu dans le top 5 : 22 % des cas) |
| Serveur HTTP local | **OPÉRATIONNEL en local**, **jamais exposé ni déployé** |
| Modèle de langage | **PRÉPARÉ et DÉSACTIVÉ** (`operationnel = False`, aucune clé) |

Corpus mesuré le 22/10/2026 (lecture seule de la base) : **37 documents,
5 593 articles** (1 111 `CALQUE_TEXTE`, 4 482 `OCR_AUTO`, 0 vérifié à la main),
**34 références** (4 `VERIFIE`, 30 `PARTIELLEMENT_VERIFIE`), **92 fiches**,
`integrity_check = ok`, SHA-256 de la base `ad0242e7…a6bd202bb`.

Couverture : 3 domaines techniquement terminés (logement, entreprises/OHADA,
transport), 2 partiels (famille, numérique), la plupart des 24 domaines de la
vision **sans texte**. La loi n° 2025-221 (baux, expulsions) **n'est pas** dans
le corpus. Détail : `KNOWLEDGE/INVENTAIRE_COUVERTURE.md`.

### 3.2 Interface web

| Fonction | État |
|---|---|
| Parcours complet (décrire → questions → résultats → courrier → téléchargement → suppression) contre le **moteur réel** | **OPÉRATIONNEL en local et en CI** (tests d'intégration et bout en bout Chromium) |
| Isolation des consultations (cookie signé HttpOnly, identifiant serveur) | **OPÉRATIONNEL** (tests) |
| Mode démonstration (`MONRECOURS_MODE=demo`) | **SIMULÉ** — c'est ce qui tourne sur la démo publique |
| Page hors ligne (service worker), en-têtes de sécurité (CSP, `nosniff`, `DENY`) | **PRÉSENT** dans le code ; en-têtes contrôlés par les tests |

### 3.3 Authentification et administration (branche `feature/admin-authentification`)

| Élément | État |
|---|---|
| `/connexion`, `/api/connexion`, `/api/deconnexion`, `/admin` | **PRÉPARÉ et TESTÉ**, **activé nulle part** |
| Mots de passe | empreintes scrypt (N=16384, r=8, p=1, sel 16 octets) ; script `web/scripts/creer-compte.mjs` (saisie masquée, ≥ 12 caractères, n'affiche que l'empreinte) |
| Session | cookie `mrci_admin` HMAC, HttpOnly, SameSite=Strict, Secure en production, **2 h** ; rôle relu à chaque requête ; session liée à l'empreinte du mot de passe |
| Contrôles | limite 5/min par visiteur et par adresse ; contrôle d'origine (CSRF) ; réponse identique compte connu/inconnu (empreinte factice préchauffée) |
| Audit | JSONL dans `MONRECOURS_AUDIT_FICHIER` + journal serveur ; jamais de mot de passe, cookie ni IP |
| Fermeture automatique | en mode démo, sans compte, secret < 32 caractères, configuration ambiguë, fichier de comptes aux droits trop larges / lien symbolique / mauvais propriétaire |
| Mot de passe oublié | **par conception**, page d'explication sans réinitialisation par e-mail (aucun service d'envoi) : l'administrateur du serveur régénère l'empreinte |
| Tableau de bord | lecture seule ; « Non disponible » / « Non connecté » quand la donnée n'existe pas ; aucune consultation visible |
| Limites connues | limitation des tentatives **en mémoire** (remise à zéro au redémarrage, non partagée entre instances) ; pas de 2FA ; pas de gestion des comptes depuis l'interface (volontaire) |

Aucun compte (de test ou d'administration) n'a été créé.

### 3.4 Persistance, sauvegarde, purge

| Élément | État |
|---|---|
| Dossiers sur disque `DOSSIERS/` (700/600) | **OPÉRATIONNEL en local** |
| Sauvegarde chiffrée `bin/sauvegarde.py` (AES-256-CBC + HMAC, `sqlite3.backup()`), restauration contrôlée | **PRÉPARÉ et TESTÉ** sur données synthétiques ; jamais planifiée — `docs/SAUVEGARDE_RESTAURATION.md` |
| Purge `web/scripts/purger-consultations.mjs` + `monrecours-purge.timer` | **PRÉPARÉ** ; durée **90 jours = hypothèse à valider** par le propriétaire |
| Base de données multi-utilisateurs, comptes citoyens | **ABSENT** (décision : pas de comptes citoyens) |

---

## 4. État réel du déploiement et des services

| Service | État vérifié le 22/10/2026 |
|---|---|
| **Démonstration publique** https://mon-recours-ci-demo.vercel.app | projet Vercel `mon-recours-ci-demo`, déploiement de production `dpl_2nc7fWUTJ8JB8PrV3hQFJkGn5K3r` (READY), branche `corpus/collecte-autonome`, commit `3afb590`, `MONRECOURS_MODE=demo`. **SIMULÉ** : réponses figées, aucun moteur, administration fermée. **Ne pas modifier.** |
| Compte Vercel | forfait **Hobby** (gratuit, réservé à l'usage non commercial). Pas de connexion Git entre GitHub et Vercel : les déploiements de la démo ont été faits par envoi de fichiers. |
| Projet Vercel `mon-recours-ci-admin-test` | créé le 21/10 (ID `prj_8Z1gPenBJHBCFUKuur1kdtLURIpw`), protection Vercel Authentication sur **tous** les déploiements, **0 variable, 0 domaine, 0 déploiement** (la tentative a été interrompue avant l'envoi complet des fichiers). Il n'expose rien. **Décision du propriétaire** : le conserver vide ou le supprimer depuis le tableau de bord Vercel. Ce n'est pas un objectif de la suite. |
| Serveur de production | **ABSENT** (aucun VPS loué, aucun nom de domaine) |
| GitHub Actions | `interface-web.yml` (CI) ; `collecte-corpus.yml` (collecte, déclenchement manuel, écriture distante opt-in) |
| Modèle de langage | **aucun** fournisseur configuré |
| Base de données externe, e-mail, stockage cloud | **aucun** |

Le moteur ne peut pas tourner sur Vercel : il écrit sur disque (`DOSSIERS/`),
écoute en local seulement et n'est pas une application ASGI/WSGI ; le système
de fichiers des fonctions Vercel est en lecture seule (hors `/tmp` éphémère).

---

## 5. Branches et commits

`main` (`2dca704`, commit initial) n'a jamais reçu les travaux. Les branches
s'empilent sans conflit ; `feature/admin-authentification` contient toutes les
autres sauf l'archive PDF.

| Branche | Tête | Rôle |
|---|---|---|
| `main` | `2dca704` | commit initial — **ne pas modifier** |
| `feature/interface-web` → `feature/domaine-famille` → `feature/produit-fonctionnel` → `audit/24-domaines` → `corpus/collecte-24-domaines` | — | étapes historiques, toutes incluses dans les suivantes |
| `corpus/collecte-autonome` | `3afb590` | état publié en démonstration |
| **`feature/admin-authentification`** | **`a1aa017`** (+ ce document) | **branche de référence pour reprendre** : `3afb590` + authentification/admin (`625022c`), corrections de sécurité F1/F2/F3/F6 (`3522250`), procédure et contrôle de préproduction (`a1aa017`) |
| `corpus/archives-pdf` | `de52f96` | branche orpheline : PDF collectés (pas du code) |

Aucune fusion dans `main` n'a eu lieu. Elle reste une décision du propriétaire.

---

## 6. Commandes

```bash
git clone https://github.com/jeffadou258-afk/mon-recours-ci.git   # ou le dossier local existant
cd mon-recours-ci
git fetch origin && git checkout feature/admin-authentification

# Moteur (Python 3.9+)
python3 -m pip install -r requirements.txt          # fpdf2 : sans lui, aucun PDF et 3 tests échouent
MONRECOURS_PDF_NON_DISTRIBUES=1 python3 tests/run_all.py   # doit finir par VERDICT=SUCCES

# Interface (Node 20.9+)
cd web
npm ci --ignore-scripts
npm run typecheck
npm test                    # unitaires + composants
npm run test:integration    # avec le moteur Python réel (démarré par les tests)
npm run test:e2e            # Chromium (Playwright requis)
npm run build && npm run verifier:secrets
cd ..

# Tout démarrer en local (clés aléatoires dans web/.env.local, droits 600)
bash scripts/demarrer-local.sh            # http://localhost:3000
bash scripts/demarrer-local.sh --tests    # contrôles complets d'abord

# Contrôle d'un serveur installé (lecture seule, n'affiche aucune valeur)
sudo bash web/deploiement/verifier-preproduction.sh https://<adresse>
```

---

## 7. Derniers tests réellement exécutés

| Suite | Où / quand | Résultat |
|---|---|---|
| CI complète sur `a1aa017` (audit npm, TypeScript, unitaires, build Next.js, secrets, intégration moteur réel, bout en bout Chromium, tests du moteur) | GitHub Actions, run `39689164661`, 21/10 22:48 UTC | **toutes les étapes réussies** (les compteurs détaillés ne sont pas lisibles depuis cette session) |
| Moteur `tests/run_all.py` | session de rédaction, 22/10 | **575 tests : 566 OK, 3 échecs, 6 ignorés** — les 3 échecs (`test_courriers`) viennent uniquement de l'absence de `fpdf2` dans cet environnement (installation bloquée) ; ils passent en CI |
| Web unitaires + composants | session de rédaction, 22/10 | **104 / 104** |
| Web intégration (moteur réel) | session de rédaction, 22/10 | **13 / 14** — l'échec est le téléchargement du PDF, même cause (`fpdf2` absent) |
| Scénarios d'authentification de bout en bout (15) contre le moteur réel | 21/10, avant `a1aa017` | **15 / 15** |
| TypeScript, build, e2e | non exécutables dans cette session (registre npm inaccessible) | couverts par la CI ci-dessus |
| Sur le Mac du propriétaire | **non exécuté** | **À VÉRIFIER** |

Un test est ignoré en CI : le contrôle du propriétaire du fichier de comptes
exige `root`.

`README.md` annonce encore 515 tests : chiffre **périmé**, l'état mesuré est
575. `HANDOFF_HERMES.md` et `CLAUDE_HANDOFF.md` sont des instantanés datés.

---

## 8. Problèmes connus et décisions déjà prises

### Problèmes et risques

1. **Aucune validation juridique** : 0 article vérifié à la main, toutes les
   fiches `A_RELIRE_PAR_UN_JURISTE`. Bloquant pour un usage public.
2. **Couverture étroite** : la majorité des domaines sans texte ; loi 2025-221
   absente ; Code du travail non intégré (source non officielle).
3. **80 % des articles sont issus d'OCR** (`OCR_AUTO`) : provenance affichée,
   mais qualité non relue.
4. **PDF officiels hors du dépôt** : sur un serveur, soit les récupérer depuis
   `corpus/archives-pdf`, soit démarrer avec `MONRECOURS_PDF_NON_DISTRIBUES=1`.
5. **Limitation des tentatives en mémoire** (une seule instance prévue : acceptable
   sur un serveur unique, à revoir si plusieurs instances).
6. **Données personnelles** : `DOSSIERS/` contient des récits. Conformité à la
   loi n° 2013-450 non établie par un juriste ; durée de conservation non validée.
7. **Pas de revue de sécurité externe** ni de test d'intrusion.
8. Documents d'état partiellement périmés (voir § 7).

### Décisions techniques déjà prises

* Moteur déterministe ; aucun LLM sans accord, budget et accord sur les données.
* Le moteur n'écoute que sur `127.0.0.1` ; il n'est jamais exposé directement.
* **Production = un seul serveur Linux** (nginx + Next.js + moteur, systemd) ;
  Vercel ne convient pas pour l'application complète. Vercel reste réservé à la
  démonstration figée.
* Pas de comptes citoyens ; isolation par cookie signé ; suppression par la personne.
* Pas de réinitialisation de mot de passe par e-mail ; comptes administrateurs
  définis côté serveur (fichier `0600`), empreintes uniquement.
* Aucun envoi de courrier par le système.
* Ne jamais contourner un accès payant ou protégé (JO, CNDJ, CIVLII).

---

## 9. Prochaines tâches, par priorité

**P0 — reprise sans perte (avant toute modification)**
1. Sur le Mac (`/Users/mac/mon_recours_ci`) : `git status`, `git branch -vv`,
   `git log -5` ; vérifier qu'aucun travail local non poussé n'existe (l'agent
   Hermes y a travaillé). Ne rien écraser ; pousser ou sauvegarder d'abord.
2. Installer `fpdf2`, relancer `tests/run_all.py` et les tests web ; obtenir
   `VERDICT=SUCCES` et noter les compteurs réels.

**P1 — application complète réellement fonctionnelle**
3. Faire valider par le propriétaire : hébergeur (VPS), nom de domaine, durée de
   conservation (90 jours proposés), coût mensuel. Présenter 2–3 options chiffrées
   **au moment du choix** (les prix changent) avant tout achat.
4. Installer sur ce serveur, en suivant `web/deploiement/README.md` puis
   `web/deploiement/PREPRODUCTION.md` : utilisateur `monrecours`, `/etc/mon-recours-ci/env`
   (600), unités systemd moteur + web + purge, nginx + Let's Encrypt, PDF du corpus.
5. Planifier `bin/sauvegarde.py` (clé hors serveur), **tester une restauration
   réelle**, puis activer la purge.
6. Lancer `verifier-preproduction.sh` jusqu'à `CONFORME`, puis un parcours complet
   depuis un téléphone (moteur réel, PDF, suppression).
7. Seulement avec l'accord explicite du propriétaire : créer le premier compte
   administrateur avec `creer-compte.mjs` sur le serveur, puis tester connexion,
   rôle lecteur refusé, déconnexion, limite de tentatives, journal d'audit.

**P2 — qualité du produit**
8. Relecture juridique d'un premier lot de fiches (logement d'abord) et traçage
   dans `KNOWLEDGE/registre_validation_humaine.md`.
9. Intégrer la loi 2025-221 si une source acceptable est retenue par le propriétaire.
10. Améliorer le classement de la recherche ; compléter les domaines prioritaires.
11. Mettre à jour `README.md` (compteurs) une fois les tests relancés.

**P3 — plus tard, sur décision**
12. Couche de langage (fournisseur, budget, accord sur les données).
13. Fusion vers `main` après revue des différences et des tests.
14. Sort du projet Vercel vide `mon-recours-ci-admin-test`.

---

## 10. Précautions pour ne pas casser l'existant

* Ne pas redéployer, reconfigurer ni changer les variables du projet Vercel
  `mon-recours-ci-demo`.
* Ne pas modifier `main` ni fusionner sans accord.
* Ne rien supprimer : branches, `DOSSIERS/`, `KNOWLEDGE/`, sauvegardes
  `KNOWLEDGE/.sauvegardes/`, `KNOWLEDGE/qualite/historique_tests.jsonl`.
* Ne remplacer la base que via `bin/reconstruire_base.py` (il refuse si un
  contrôle échoue) ; jamais d'`UPDATE` direct (il ne survivrait pas à une reconstruction).
* `git pull --rebase` avant de pousser sur une branche où le robot de collecte écrit.
* Ne jamais commiter `.env*`, clés, fichier de comptes, archives de sauvegarde.
* Ne pas définir `MONRECOURS_LLM_*`. Ne pas créer de compte sans autorisation.
* Aucun achat, abonnement ou domaine sans accord écrit du propriétaire.
* Ne pas présenter la démonstration (réponses figées) comme le produit réel.

---

## 11. Informations que MS doit vérifier avant d'agir

1. L'état du Mac : modifications locales, branches non poussées, présence des
   PDF et des outils OCR (poppler, tesseract), contenu de `DOSSIERS/` (données
   réelles ou de test ?).
2. Les compteurs réels de la CI (non lisibles depuis la session de rédaction).
3. Le choix de l'hébergeur, du domaine et du budget mensuel par le propriétaire.
4. La durée de conservation des consultations.
5. Qui recevra le premier compte administrateur, et son accord explicite.
6. Le juriste chargé de la relecture, et le périmètre du premier lot.
7. Le sort du projet Vercel `mon-recours-ci-admin-test` (garder vide ou supprimer).
8. La source acceptable pour la loi 2025-221 et pour le Code du travail.

Documents utiles : `RAPPORT_PRODUIT.md`, `CLAUDE_HANDOFF.md` (contrats d'API),
`HANDOFF_HERMES.md` (collecte, OCR), `docs/PREPRODUCTION.md`,
`docs/SAUVEGARDE_RESTAURATION.md`, `web/README.md`, `web/deploiement/`.
