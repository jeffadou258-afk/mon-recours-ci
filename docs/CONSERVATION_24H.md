# Conservation temporaire des consultations — 24 heures

Décision produit du 22/10/2026 : **une consultation est conservée 24 heures au
plus après sa création, puis supprimée automatiquement côté serveur.** Les
ressources permanentes (corpus, fiches, configuration, comptes, journaux
d'audit) ne sont jamais concernées.

**État : audité, conçu et préparé sur la branche `feature/conservation-24h`.
Rien n'est installé, aucune purge n'a été lancée, aucune donnée existante n'a
été supprimée ni modifiée.** Les tests utilisent exclusivement des données
synthétiques.

---

## 1. Fonctionnement constaté avant ce chantier

| Étape | Où | Ce qui se passe |
|---|---|---|
| Identifiant | `web/src/lib/server/session.ts` | tiré côté serveur : `web-` + UUID v4 ; jamais fourni par le navigateur |
| Lien navigateur ↔ consultation | même fichier | cookie `mrci_dossier` signé HMAC, `HttpOnly`, `SameSite=Strict`, `Path=/api`, **durée 2 h** |
| Création | `agent.py` `ouvrir_dossier` (appelé par `POST /ouvrir`) | répertoire `DOSSIERS/<id>/` en 700 |
| Date de création | `DOSSIER_EN_COURS.json`, champ `ouvert_le` (UTC) | **seul endroit** ; aucune échéance n'était inscrite |
| Fichiers produits | `DOSSIERS/<id>/` | voir § 4 |
| Base SQLite | `KNOWLEDGE/corpus_juridique.sqlite3` | **aucune donnée de consultation** : la base n'est que lue pendant une consultation (vérifié : moteur exécuté avec la base en lecture seule, parcours complet réussi) |
| Suppression | `POST /api/supprimer` → `core/service.py` `supprimer` | à la demande de la personne, confinée au seul dossier |
| Purge | `web/scripts/purger-consultations.mjs` | 90 jours sur la date de modification, **jamais installée** |
| Effet des 2 h du cookie | — | après 2 h le navigateur ne peut plus rouvrir la consultation, **mais les fichiers restaient sur le disque** |

---

## 2. Données temporaires (soumises aux 24 heures)

Tout le contenu de `DOSSIERS/web-<uuid>/` :

| Fichier | Contenu | Données personnelles |
|---|---|---|
| `DOSSIER_EN_COURS.json` | récit (`demande`), qualification, urgence, garde-fous, faits, **informations du courrier** (expéditeur, destinataire, pièces), copie des références candidates du corpus | **oui** |
| `CONVERSATION.json` | récit, questions posées, **réponses**, contradictions, étape | **oui** |
| `DOSSIER_TRACABILITE.json` | faits, analyse, règles, articles utilisés | **oui** (faits) |
| `BROUILLONS/<horodatage>_reclamation.txt` et `.pdf` | courrier ; **une paire par génération**, les versions s'accumulent dans le dossier | **oui** |
| `CONSERVATION.json` *(nouveau)* | `cree_le`, `expire_le`, `duree_heures` | non |

Hors serveur : le cookie (identifiant seulement, 2 h) et l'état de la page dans
la mémoire du navigateur, effacés à la fermeture.

## 3. Données permanentes (jamais purgées)

| Donnée | Emplacement |
|---|---|
| Code, corpus, fiches, questions, textes extraits | dépôt Git : `KNOWLEDGE/`, `core/`, `web/`… |
| Configuration et secrets | `/etc/mon-recours-ci/env` |
| Comptes administrateurs | `/etc/mon-recours-ci/comptes.json` |
| Clé de sauvegarde | `/etc/mon-recours-ci/cle-sauvegarde` (+ copie hors serveur) |
| Journal d'audit de l'administration | `/var/lib/monrecours/audit.jsonl` |
| Journal de purge (compteurs) | `KNOWLEDGE/qualite/purge.jsonl` |
| Archives de sauvegarde | `/var/lib/monrecours-sauvegardes/` |
| Certificats HTTPS | `/etc/letsencrypt/` (réémissibles) |

La séparation est **physique** : la purge ne lit que la racine `DOSSIERS/`, et
n'y touche que les noms `web-<uuid v4>` (et les restes `.purge-web-<uuid>`) ;
rien de permanent n'est stocké sous `DOSSIERS/`.

---

## 4. Tous les endroits où une consultation peut être copiée

| # | Emplacement | Avant | Après ce chantier |
|---|---|---|---|
| 1 | `DOSSIERS/<id>/` (fichiers du § 2) | gardé indéfiniment | **refusé à la lecture dès l'échéance, effacé au plus 15 min après** |
| 2 | PDF et TXT des courriers (`BROUILLONS/`) | idem | idem ; téléchargement refusé dès l'échéance |
| 3 | Archives `bin/sauvegarde.py` | consultations incluses | **exclues** (`--sans-dossiers`) |
| 4 | Instantanés de disque de l'hébergeur (option « Backups ») | prévus, 7 jours, en clair | **recommandé : ne pas les activer** (sinon 7 jours de copie à annoncer) |
| 5 | Journal du moteur (journald) | horodatage, route, statut, durée, **empreinte de 12 caractères** de l'identifiant — jamais de contenu | inchangé ; conservation ramenée à **7 jours** |
| 6 | Journal de l'interface (journald) | événement, route, statut, code — ni contenu ni identifiant | inchangé ; 7 jours |
| 7 | Journal d'accès nginx | adresse IP, chemin, statut — le corps des requêtes n'y est pas | 14 jours (rotation Ubuntu) |
| 8 | Fichiers temporaires de nginx | un corps de plus de 16 Ko pouvait être écrit sur disque le temps de la requête | **gardé en mémoire** (`client_body_buffer_size 32k`) |
| 9 | Réponse `INTERNE` du moteur | peut contenir un message d'exception | jamais journalisée ni renvoyée telle quelle par l'interface (test existant) |
| 10 | Navigateur : cookie, mémoire de la page | 2 h / fermeture | inchangé |
| 11 | Fichiers enregistrés par la personne, impressions, captures | sur son appareil | **hors de portée du service** — annoncé à l'écran |
| 12 | Modèle de langage externe | désactivé | désactivé (s'il était activé un jour, le récit masqué partirait chez le fournisseur : à réévaluer) |
| 13 | Postes de développement (Mac) | `DOSSIERS/` locaux, contenu **non vérifié** | **à inventorier** avec `scripts/etat-poste.sh` ; rien n'est supprimé sans accord |
| 14 | Base SQLite | rien | rien |

---

## 5. Mécanisme d'expiration et de purge (préparé)

```
création (POST /ouvrir) ──► CONSERVATION.json { cree_le, expire_le = cree_le + 24 h }   (écrit une fois, O_EXCL)
                │
lecture ────────┼──► moteur : repondre / courrier / ouvrir refusés si échu  → DOSSIER_EXPIRE
                │    interface : téléchargement PDF refusé si échu          → 410 CONSULTATION_EXPIREE
                │
purge ──────────┴──► minuteur systemd toutes les 15 min (côté serveur, sans navigateur)
                     1. renommage en .purge-web-<uuid>-<hasard>  → introuvable aussitôt
                     2. effacement ; en cas d'échec, reste repris au passage suivant
```

* **Échéance fiable** : inscrite à la création, jamais réécrite (deux ouvertures
  concurrentes ne peuvent pas la repousser). Dossiers antérieurs : `ouvert_le` +
  24 h, puis date de modification + 24 h. Chaque repli ne peut que retarder.
* **24 h maximum vues de l'utilisateur** : le refus à la lecture s'applique à la
  seconde de l'échéance, même si la purge n'est pas encore passée.
* **Sûre** : racine unique, noms `web-<uuid v4>` seulement, liens symboliques
  ignorés, `realpath` contrôlé, dossier parent vérifié ; aucun chemin venant d'un
  utilisateur.
* **Idempotente** : relancée, elle ne fait rien de plus (testé 4 fois de suite).
* **Erreurs partielles** : un échec n'interrompt pas les autres dossiers ; code de
  sortie 1 ; le reste renommé est repris ensuite.
* **Journal** : compteurs et origine des échéances seulement — aucun identifiant.
* **Durée** : `MONRECOURS_CONSERVATION_HEURES=24` (moteur et interface) et
  `--heures 24` (purge) ; une valeur invalide est refusée.

## 6. PDF

Les PDF sont dans `DOSSIERS/<id>/BROUILLONS/` et disparaissent avec le dossier.
Le téléchargement est refusé dès l'échéance (contrôle dans
`web/src/lib/server/dossiers.ts`, même règle que le moteur). Les régénérations
successives s'accumulent pendant les 24 heures, puis partent ensemble. La copie
que la personne a téléchargée lui appartient : l'écran de résultats le dit.

## 7. Journaux

* Moteur et interface : aucun contenu de consultation, ce qui était déjà
  garanti par le code et des tests. L'empreinte de 12 caractères de
  l'identifiant permet de relier les requêtes d'une même consultation, sans en
  révéler le contenu : conservation de **7 jours** (`journald-mon-recours-ci.conf`).
* nginx : adresse IP et chemin, sans corps ; 14 jours.
* Purge et audit : compteurs, ou événements d'administration sans mot de passe
  ni identifiant de consultation.

## 8. Sauvegardes

**Recommandation : ne plus sauvegarder les consultations.** Elles vivent
24 heures ; les restaurer après un incident apporterait peu et contredirait la
promesse faite à l'utilisateur.

| Élément | Protégé par |
|---|---|
| Code, corpus, fiches | Git (GitHub) — reconstructible à l'identique |
| Base du corpus (état exact du serveur) | archive chiffrée nocturne |
| Configuration, comptes, journal d'audit | archive chiffrée nocturne (`--inclure`) |
| Consultations | **aucune copie** (`--sans-dossiers`) |

Après un incident : réinstaller depuis Git, restaurer la dernière archive
(`--base-destination`, `--permanent-destination`), redémarrer. Les
consultations des dernières 24 heures sont perdues : la personne recommence.
Les instantanés de disque de l'hébergeur ne sont pas nécessaires ; s'ils étaient
activés, ils conserveraient des consultations jusqu'à 7 jours et il faudrait
l'annoncer. Les archives déjà existantes ne sont pas modifiées par ce chantier.

## 9. Conséquences sur l'hébergement

* **Stockage persistant toujours nécessaire** : corpus, configuration, comptes,
  audit, archives. Le serveur unique reste la bonne architecture.
* **Pas de base de données à ajouter** : les consultations restent des fichiers,
  et la base n'en contient aucune.
* **Disque** : le volume des consultations est borné à une journée. Mesuré :
  ≈ 2,6 Mo par consultation, surtout la copie des références candidates du
  corpus dans `DOSSIER_EN_COURS.json` (aucune donnée personnelle). À 1 000
  consultations par jour : ≈ 2,6 Go au plus, largement dans les 40 Go. Une
  réduction de cette copie est possible plus tard (optimisation, non requise).
* **Pas de stockage en mémoire vive** (`tmpfs`) : 4 Go de RAM ne suffiraient pas
  à forte affluence et un redémarrage perdrait les consultations en cours.
* **Sauvegardes** : archives minuscules (base + configuration) ; option
  d'instantanés de l'hébergeur inutile.
* **Coût** : serveur CX23 + IPv4 **5,99 €/mois (≈ 72 €/an)** hors taxes, au lieu
  de 7,09 € avec l'option d'instantanés ; nom de domaine inchangé.

## 10. Fichiers modifiés (branche `feature/conservation-24h`)

| Fichier | Changement |
|---|---|
| `core/conservation.py` *(nouveau)* | échéance : écriture unique, lecture, replis, durée configurable |
| `agent.py` | `CONSERVATION.json` écrit à la création du dossier |
| `core/service.py` | `ouvrir`, `repondre`, `rediger_courrier` refusent un dossier échu (`DOSSIER_EXPIRE`) ; `supprimer` reste toujours possible |
| `web/scripts/purger-consultations.mjs` | `--heures`, échéance lue dans `CONSERVATION.json`, retrait par renommage, reprise des restes, journal enrichi |
| `web/src/lib/server/dossiers.ts` | même règle d'échéance ; PDF refusé si échu |
| `web/src/lib/server/handlers.ts`, `web/src/lib/types.ts` | code `CONSULTATION_EXPIREE` (HTTP 410) |
| `web/src/components/MessageErreur.tsx` | « Consultation expirée et supprimée », bouton Recommencer |
| `web/src/components/Parcours.tsx`, `ActionsConsultation.tsx`, `web/src/app/comprendre/page.tsx` | annonce de la consultation temporaire et des 24 heures |
| `bin/sauvegarde.py` | `--sans-dossiers` (choix explicite obligatoire), `--inclure`, `--permanent-destination` |
| `web/deploiement/monrecours-purge.service` / `.timer` | `--heures 24`, toutes les 15 minutes |
| `web/deploiement/monrecours-sauvegarde.service` | sans consultations ; configuration et audit inclus ; correction de l'échappement `$$` pour systemd |
| `web/deploiement/env.exemple`, `nginx.conf.exemple`, `journald-mon-recours-ci.conf` *(nouveau)*, `verifier-preproduction.sh` | durée, corps en mémoire, journaux 7 jours, contrôles |

## 11. Tests (données synthétiques)

| Exigence | Test |
|---|---|
| moins de 24 h → conservé | `test_retention.TestPurge24Heures.test_moins_de_24_heures_conserve` ; web `dossiers.test.ts` « avant l'échéance » |
| plus de 24 h → éligible et supprimé | `test_plus_de_24_heures_supprime_pdf_compris` |
| exécution répétée sans effet dangereux | `test_execution_repetee_sans_effet_supplementaire` |
| une consultation n'en supprime pas une autre | `test_une_consultation_expiree_ne_touche_pas_une_autre_non_expiree` ; web « n'empêche pas une autre » |
| corpus jamais touché ; comptes jamais touchés | `test_donnees_permanentes_jamais_touchees` |
| PDF pris en compte | `test_plus_de_24_heures_supprime_pdf_compris` ; web « le courrier n'est plus servi » ; intégration (PDF 410) |
| erreurs partielles | `test_reste_d_une_suppression_interrompue_est_repris` (un dossier retiré mais non effacé est repris) |
| plus rien d'accessible après échéance | `test_conservation.TestServiceRefuseLesDossiersExpires` ; intégration web + moteur réel : `repondre`, `courrier`, PDF → 410, aucun mot du récit, dossier non modifié ni recréé |
| échéance inscrite, jamais repoussée, à la seconde | `test_conservation.TestMarquage` |
| sauvegarde sans consultations | `test_sauvegarde.TestSauvegardeSansConsultations` |
| annonce à l'écran | `affichage.test.tsx` (24 heures, consultation temporaire, message d'expiration) |
| non-régression : 90 jours / date de modification | `test_retention.TestPurgeDossiersSansMetadonnee` |

Un test de mutation a été fait sur la purge : avancer l'échéance de 48 h fait
échouer 6 tests.

## 12. Risques identifiés

1. **Premier passage de la purge** : il supprimera d'un coup tous les dossiers
   web de plus de 24 h présents sur la machine où il est installé. À ne lancer
   qu'avec votre accord explicite, après inventaire (sur le Mac : contenu de
   `DOSSIERS/` non vérifié).
2. **Durée du cookie (2 h) plus courte que la conservation (24 h)** : la personne
   qui revient après 2 h ne retrouve pas sa consultation, alors qu'elle existe
   encore sur le serveur. C'est le choix le plus protecteur (téléphones
   partagés) ; l'allonger à 24 h est possible. **À décider.**
3. **Requête en cours à la seconde de l'échéance** : une écriture déjà commencée
   pourrait recréer un fichier après le retrait ; il serait effacé au plus tard
   24 h plus tard (repli sur la date de modification). Fenêtre de quelques
   millisecondes ; à surveiller, pas bloquant.
4. **Horloge du serveur** : l'échéance dépend de l'heure système ; NTP doit être
   actif (par défaut sur Ubuntu).
5. **Dossiers antérieurs à `CONSERVATION.json`** : échéance tirée de `ouvert_le`,
   ou de la date de modification si le fichier est illisible — jamais plus tôt,
   parfois plus tard.
6. **Instantanés de l'hébergeur** : s'ils sont activés, ils contredisent la
   promesse des 24 h pendant 7 jours.
7. **Copies chez la personne** (téléchargements, impressions, captures) : hors
   de portée ; annoncé à l'écran.
8. **Démonstration publique** : non concernée et non modifiée. Si cette version
   y était publiée un jour, l'annonce « supprimée du serveur après 24 heures »
   devrait y être adaptée (rien n'y est conservé).
9. **Conformité** : la durée de 24 h est une décision produit ; sa mention dans
   les conditions d'utilisation et la conformité à la loi n° 2013-450 restent à
   faire relire par un juriste.
