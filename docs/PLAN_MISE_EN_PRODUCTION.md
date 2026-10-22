# Plan de mise en production — Mon Recours CI

État au 22/10/2026, branche `feature/admin-authentification`. **Rien n'est
souscrit, rien n'est déployé.** Ce document décrit l'architecture retenue, son
coût, les protections des données et le plan de relecture juridique, puis la
liste des seules décisions qui reviennent au propriétaire.

Légende : **VÉRIFIÉ** = exécuté et observé · **PRÊT** = fichier écrit et
contrôlé, pas installé · **À DÉCIDER** = décision du propriétaire.

---

## 1. Compatibilité avec un serveur Linux — vérifiée

| Élément | Résultat | Preuve |
|---|---|---|
| Moteur Python sous un utilisateur sans droits, tout le code en lecture seule, **seul `DOSSIERS/` inscriptible** | **VÉRIFIÉ** : `/sante`, `/ouvrir`, `/repondre`, `/courrier` (PDF de 1 896 octets), `/supprimer` réussis ; dossiers créés en 700/600 | essai du 22/10 (utilisateur `nobody`, copie du dépôt appartenant à root) |
| SQLite | **VÉRIFIÉ** : base en mode `delete` (pas de WAL), lue sans écriture ; `integrity_check = ok` | même essai |
| Corpus sans les PDF officiels | **VÉRIFIÉ** : `INTEGRE` en mode `pdf_non_distribues_toleres` (empreintes des 37 textes extraits) | `/sante` du même essai |
| Courriers PDF | **VÉRIFIÉ** avec `fpdf2` 2.8.4 | essai + tests `test_courriers` |
| Sauvegarde → vérification → restauration | **VÉRIFIÉ** : archive 600 opaque (0 occurrence du récit en clair), mauvaise clé refusée (code 3), restauration **identique** (`diff -r` vide), base restaurée `ok`, 5 593 articles | essai du 22/10 |
| Python 3.12 / Node 22 | **VÉRIFIÉ** en CI (Ubuntu) ; Python 3.13 localement | runs GitHub Actions |
| Unités systemd | **PRÊT** : syntaxe validée par `systemd-analyze verify` | `web/deploiement/*.service`, `*.timer` |

Corrections apportées le 22/10 pour un serveur réel :

* le moteur tourne dans un **environnement virtuel** (`/opt/mon-recours-ci/.venv`) :
  Ubuntu 24.04 refuse `pip install` dans le Python du système, et sans `fpdf2`
  aucun courrier PDF n'est produit ;
* **sauvegarde planifiée** ajoutée (`monrecours-sauvegarde.service` + `.timer`,
  chaque nuit, archive vérifiée aussitôt) — elle n'existait que comme outil ;
* `verifier-preproduction.sh` contrôle désormais `fpdf2`, les minuteurs de
  sauvegarde et de purge, les droits de la clé et l'âge de la dernière archive ;
* `bin/sauvegarde.py` ajoute le filtre `data` de la bibliothèque standard à ses
  propres contrôles d'extraction.

---

## 2. Architecture recommandée (une seule)

**Un serveur virtuel Linux unique (Hetzner Cloud CX23 : 2 vCPU, 4 Go de RAM,
40 Go de disque, 20 To de trafic), Ubuntu 24.04 LTS, avec un nom de domaine
en `.ci`.**

```
Internet ──HTTPS (Let's Encrypt)──► nginx :443 ──► Next.js 127.0.0.1:3000 ──► moteur 127.0.0.1:8765
                                    TLS, débit,      cookie signé,               clé d'API,
                                    taille bornée    admin, audit                débit global
                                                                                 │
                                    /opt/mon-recours-ci/DOSSIERS (700) ◄─────────┘
                                    /var/lib/monrecours-sauvegardes (700, chiffré)
```

Pourquoi ce choix :

* le moteur doit écrire sur un disque durable (`DOSSIERS/`) et n'écoute qu'en
  local : un serveur unique le garde fermé à Internet, sans réécriture ;
* tout est déjà écrit pour cette forme (systemd, nginx, purge, sauvegarde,
  contrôle automatique) ;
* c'est l'option la moins chère qui laisse de la marge : la construction Next.js
  demande 1 à 2 Go de RAM, le dépôt et les dépendances moins de 1 Go de disque,
  une archive de sauvegarde environ 2,7 Mo par nuit aujourd'hui.

Pourquoi pas Vercel pour le produit réel : système de fichiers des fonctions en
lecture seule, moteur non joignable sans l'exposer, forfait Hobby réservé à
l'usage non commercial. Vercel reste limité à la démonstration figée.

### Coût estimé (hors taxes, à revérifier le jour de la commande)

| Poste | Mensuel | Annuel | Source |
|---|---|---|---|
| Serveur CX23 + adresse IPv4 | 5,99 € | 71,88 € | [CostGoat, données du 20/10/2026](https://costgoat.com/pricing/hetzner) ; hausse du 15/06/2026 : [PrivateDevOps](https://privatedevops.com/news/hetzner-june-2026-cloud-price-increase-what-to-do) |
| Sauvegardes automatiques du serveur (20 % du prix du serveur) | 1,10 € | 13,18 € | même source |
| Nom de domaine `.ci` | ≈ 3 750 FCFA | **45 000 FCFA** au registre (50 000 à 75 000 FCFA chez un revendeur) | [Kolonell](https://kolonell.com/fr/blog/domaine-ci-extension-cote-ivoire-enregistrement-2026) — chiffres d'un revendeur, à confirmer auprès du NIC CI |
| Certificat HTTPS (Let's Encrypt) | 0 | 0 | — |
| **Total** | **≈ 7,09 € + domaine** ≈ **8 400 FCFA** | **≈ 85 € + 45 000 FCFA ≈ 101 000 FCFA** | 1 € = 655,957 FCFA |

Non compris : relecture juridique (honoraires à convenir), éventuelle copie
des sauvegardes chez un second fournisseur (quelques centimes par mois au volume
actuel), modèle de langage (désactivé). Les prix Hetzner s'entendent hors TVA ;
la TVA éventuelle dépend du pays de facturation.

### Besoins techniques

* un compte chez l'hébergeur (moyen de paiement du propriétaire) ;
* le domaine, et l'accès à sa zone DNS (un enregistrement `A` vers le serveur) ;
* une clé SSH du responsable technique (aucun mot de passe SSH) ;
* environ une demi-journée d'installation en suivant `web/deploiement/README.md`,
  puis `verifier-preproduction.sh` jusqu'à `CONFORME`.

### Limites assumées

* **Un seul serveur** : pas de haute disponibilité ; une panne coupe le service
  jusqu'au redémarrage ou à la restauration (objectif : moins d'une heure à partir
  d'une sauvegarde).
* **Serveur hors de Côte d'Ivoire** (centres de données européens) : latence
  d'environ 100 à 150 ms depuis Abidjan, sans effet notable sur le parcours. Le
  transfert de données personnelles hors du pays relève de la loi n° 2013-450 :
  **conditions et formalités à vérifier par un juriste** (autorité de protection :
  ARTCI) avant l'ouverture au public.
* Disque du serveur non chiffré par l'hébergeur ; les **archives** de sauvegarde
  le sont.
* Limitation des tentatives de connexion en mémoire (suffisant pour une instance).

---

## 3. Protection des données — mesures prévues (à approuver)

### 3.1 Sauvegardes

| Mesure | État |
|---|---|
| Archive chiffrée chaque nuit à 02 h 30 de `DOSSIERS/` et de la base (AES-256-CBC + HMAC-SHA256, copie cohérente de SQLite) | **PRÊT** (`monrecours-sauvegarde.*`) |
| Vérification automatique de chaque archive (MAC, déchiffrement, manifeste) | **PRÊT** (`ExecStartPost`) |
| Clé de 32 octets hors dépôt, `600 monrecours`, **copie hors du serveur** (coffre ou gestionnaire de secrets) | **À FAIRE à l'installation** — sans copie, perte du serveur = archives illisibles |
| Sauvegardes automatiques du serveur entier chez l'hébergeur (7 instantanés glissants) | inclus dans le coût ci-dessus |
| Copie des archives chiffrées chez un second fournisseur | **À DÉCIDER** (recommandé à terme, non indispensable au pilote) |
| Durée de vie des archives | **À DÉCIDER** — aucune suppression automatique n'est configurée |

### 3.2 Restauration

* Cycle complet **vérifié** le 22/10 sur données synthétiques (§ 1).
* Avant ouverture : une restauration d'essai **sur le serveur réel**, dans un
  répertoire neuf (`bin/sauvegarde.py restaurer … --sortie /srv/restauration/…`).
* Ensuite : une restauration d'essai **par trimestre**, consignée.

### 3.3 Accès administratifs

| Accès | Mesure |
|---|---|
| Serveur | SSH par clé uniquement, connexion `root` interdite, pare-feu limité aux ports 22, 80 et 443, mises à jour de sécurité automatiques |
| Services | utilisateur `monrecours` sans droits, `ProtectSystem=strict`, seuls `DOSSIERS/`, `.next/`, l'audit et les sauvegardes inscriptibles |
| Espace `/admin` | fermé tant que le propriétaire n'a pas autorisé un compte ; ensuite un seul compte administrateur, empreinte scrypt dans `/etc/mon-recours-ci/comptes.json` (`600`), session de 2 h, 5 tentatives par minute, journal d'audit. Option : restreindre `/connexion` et `/admin` à quelques adresses IP dans nginx |
| Secrets | `/etc/mon-recours-ci/env` (`600`), jamais dans le dépôt ; contrôle `verifier:secrets` sur le code envoyé au navigateur |

### 3.4 Journaux

| Journal | Contenu | Conservation proposée |
|---|---|---|
| Moteur | horodatage, route, statut, durée, **empreinte** du dossier — aucun récit | journald : **30 jours** (`MaxRetentionSec`) |
| Interface | `{horodatage, événement, route, statut, code}` — aucun contenu | idem |
| Audit de l'administration | connexions réussies/refusées (empreinte courte de l'adresse saisie), déconnexions, accès — jamais de mot de passe, cookie ou IP | **1 an** (traçabilité des accès) |
| nginx (accès) | adresse IP, URL, statut — les récits passent dans le corps des requêtes, jamais dans l'URL | **14 jours** (rotation) |
| Purge | compteurs uniquement | 1 an |

### 3.5 Durée de conservation des consultations

**90 jours est une proposition, pas une décision.** Mécanisme prêt : purge
quotidienne des dossiers `web-*` non modifiés depuis N jours (simulation par
défaut, suppression seulement avec `--confirmer`). Points à trancher ensemble :

1. la durée N (proposition : 90 jours ; une durée plus courte réduit le risque,
   une plus longue permet de revenir plus tard sur un courrier) ;
2. la durée de vie des archives de sauvegarde (une archive conserve un récit
   au-delà de sa purge : à annoncer, ou à limiter) ;
3. le texte affiché aux utilisateurs (page « Comprendre ») et les mentions
   légales — à faire relire par un juriste au regard de la loi n° 2013-450.

---

## 4. Plan de relecture juridique — premier lot

**Aucune fiche n'est validée juridiquement aujourd'hui.** Le statut des fiches
reste `A_RELIRE_PAR_UN_JURISTE` tant qu'une relecture signée n'a pas eu lieu.

| Élément | Proposition |
|---|---|
| Lot 1 | **Logement** : 10 fiches (Code de la construction et de l'habitat, loi n° 2019-576 ; code de l'urbanisme et du foncier, loi n° 2020-624), leurs questions et leurs démarches. C'est le domaine le mieux sourcé (références `VERIFIE`, textes lus par calque, pas par OCR) |
| Document remis | **PRÊT** : `KNOWLEDGE/relecture/logement_baux_foncier.md` (article intégral indexé, extrait cité, lecture simple, questions, démarche, provenance) + grille `logement_baux_foncier.csv` à remplir — générés par `bin/kit_relecture.py`, qui ne modifie aucun statut |
| Profil | avocat inscrit au Barreau de Côte d'Ivoire, ou enseignant-chercheur en droit privé, ou juriste d'une clinique juridique / association d'accès au droit — avec expérience du contentieux locatif |
| Points demandés | conformité de chaque extrait au texte officiel ; vigueur à la date de relecture ; effet de la **loi n° 2025-221** (baux, expulsions), absente du corpus ; exactitude de chaque lecture simple ; questions sans condition ajoutée ; démarches correctes |
| Charge estimée | une demi-journée à une journée de lecture (10 fiches courtes) — **estimation** à confirmer avec la personne |
| Livrable attendu | la grille remplie, datée et signée (nom, qualité) |
| Après la relecture | corrections appliquées par l'outil existant (`bin/ajouter_fiches.py`, qui revalide chaque citation contre la base), grille conservée dans le dépôt, registre `KNOWLEDGE/registre_validation_humaine.md` régénéré. Un outil d'enregistrement de la relecture signée reste à écrire avant de faire évoluer le moindre statut |
| Coût | honoraires à convenir — **À DÉCIDER** |

Lots suivants, par ordre d'exposition au public : famille (31 fiches, textes
OCR), contrats/OHADA (26), pénal (24).

---

## 5. Tests réellement exécutés le 22/10/2026

| Suite | Où | Résultat |
|---|---|---|
| Moteur `tests/run_all.py` (avec `fpdf2` 2.8.4, kit de relecture compris) | session de travail | **580 tests, 575 OK, 0 échec, 5 ignorés**, `VERDICT=SUCCES` |
| Web unitaires + composants | session de travail | **104 / 104** |
| Web intégration (moteur Python réel, PDF compris) | session de travail | **14 / 14** |
| CI GitHub Actions run `39741900730` (commit `11e1dc2`) | GitHub, déclenché le 22/10 | audit npm 0 vulnérabilité · TypeScript OK · unitaires 103 OK + 1 ignoré (contrôle réservé à root) · construction Next.js OK · secrets 0 · intégration 14/14 · bout en bout Chromium 11/11 · moteur 575 · **ESLint : 6 erreurs, 690 avertissements** (premier passage) |
| CI run `39743219578` (commit `18dc77c`, ESLint réglé) | GitHub, 22/10 | **toutes les étapes réussies** : mêmes résultats + **ESLint 0 erreur, 3 avertissements** (corrigés ensuite ; l'étape refuse désormais tout avertissement) |
| CI run `39746130681` (commit `d22cab4`, état final de la journée) | GitHub, 22/10 | **toutes les étapes réussies** : audit npm 0 · TypeScript OK · unitaires 103 OK + 1 ignoré · construction OK · secrets 0 · intégration 14/14 · bout en bout 11/11 · moteur 580 · **ESLint 0 problème** |

Un passage intermédiaire (run `39744788375`, commit `23ad0fe`) a échoué à la
construction Next.js puis réussi au passage suivant sans changement du code de
l'application. Le journal n'était pas lisible depuis la session ; cause
probable mais **non prouvée** : le téléchargement des polices Google pendant la
construction. La construction demande donc un accès à Internet, aussi sur le serveur.

ESLint n'avait jamais été exécuté sur le projet. Les 690 avertissements venaient
d'un fichier généré (`apercu/dist/app.js`), désormais ignoré ; les 6 erreurs
étaient 3 `any` dans des fichiers de test et 3 liens HTML ordinaires vers `/`,
choix délibéré (rechargement complet, compatible avec la page hors ligne et
l'aperçu sans Next.js), consigné dans `web/eslint.config.mjs`.

---

## 6. Décisions qui reviennent au propriétaire

1. **Hébergement** : accord pour le serveur Hetzner CX23 avec sauvegardes
   automatiques (≈ 7,09 €/mois, ≈ 85 €/an hors taxes).
2. **Nom de domaine** : choix du nom et achat du `.ci` (≈ 45 000 FCFA/an au
   registre ; pièce d'identité ou RCCM demandés).
3. **Durée de conservation** des consultations (90 jours proposés) et durée de
   vie des archives de sauvegarde.
4. **Relecteur juridique** du lot logement, et son budget.
5. **Premier compte administrateur** : qui, et quand (il ne sera créé qu'avec
   votre accord, sur le serveur, par `creer-compte.mjs`).
6. Copie des sauvegardes chez un second fournisseur : maintenant ou plus tard.
