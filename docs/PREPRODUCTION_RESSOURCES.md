# Préproduction : ressources, coûts et risques

Audit des moyens nécessaires pour installer Mon Recours CI **avec l'administration**
sur un serveur de test. Complète `web/deploiement/README.md` (procédure
d'installation) et `web/deploiement/PREPRODUCTION.md` (procédure de test de
l'administration). **Rien n'a été commandé ni déployé.**

Chiffres mesurés sur la machine de développement le 21/10/2026, sauf mention
contraire.

## 1. Architecture imposée par le code

```
Internet ──HTTPS──► nginx (443) ──► Next.js (127.0.0.1:3000) ──► moteur Python (127.0.0.1:8765)
                     TLS, HSTS         cookie signé,                      clé d'API,
                     limit_req         limite par visiteur               débit global
```

Le moteur **refuse d'écouter ailleurs que sur `127.0.0.1`** et ne sait pas faire
de TLS. L'interface doit donc tourner sur la même machine. Un hébergement
serverless est exclu pour le produit réel : il ne peut pas joindre le moteur sans
l'exposer, et n'offre ni disque persistant ni systemd.

## 2. Empreinte mesurée

| Élément | Mesure |
|---|---|
Base du corpus | **7,2 Mo** |
Base + textes + PDF du corpus (`KNOWLEDGE/`) | **389 Mo** |
`node_modules` | **377 Mo** |
Build `.next` | **81 Mo** |
Dépôt complet avec `.git` | **1,9 Go** |
Moteur Python au repos | **6 Mo** RSS |
Moteur Python après requêtes | **44 Mo** RSS |
Interface Next.js | **52 Mo** RSS |
Un dossier de consultation (après correction) | **26 Ko** |

Avant la correction du 21/10, un seul dossier pesait 2,6 Mo (texte des actes
recopié dans l'état) ; 175 dossiers occupaient 404 Mo. C'est ce qui faisait
exploser les sauvegardes autant que le disque.

**Dimensionnement recommandé** : 2 vCPU, **4 Go de RAM**, **40 Go de NVMe**.
Les 4 Go servent surtout au **build** Next.js (pic observé ~1,5–2 Go sur le
runner CI) ; au repos, l'ensemble tient sous 200 Mo.

## 3. Coûts estimés

Estimations **tierces** relevées le 21/10/2026, à confirmer auprès du fournisseur
choisi. Aucun de ces montants n'a été engagé.

| Poste | Ordre de grandeur | Source |
|---|---|---|
VPS 2 vCPU / 4 Go / 40 Go NVMe | **≈ 4 à 6 €/mois** (Hetzner CX22 ≈ 4,50 €, Contabo VPS S ≈ 5,50 €, OVH ≈ 4–8 €) | comparateurs publics, 10/2026 |
Nom de domaine | **≈ 10 à 15 €/an** sur un TLD courant | à confirmer chez le registraire |
Certificat TLS (Let's Encrypt) | **0 €** | gratuit |
Sauvegardes hors serveur | **≈ 1 à 5 €/mois** selon le volume | selon l'offre retenue |
Relecture juridique des fiches | honoraires à convenir | hors technique |

Ordre de grandeur total pour un test : **≈ 5 à 12 €/mois**, plus le domaine.
C'est une **décision du propriétaire**, pas une nécessité technique immédiate.

## 4. Exigences techniques

| Domaine | Exigence |
|---|---|
Système | Ubuntu LTS, systemd, utilisateur système `monrecours` sans privilèges |
Logiciels | Python 3.9+, Node.js ≥ 20.9, nginx, certbot, poppler-utils, tesseract-ocr-fra (OCR) |
Répertoires | `/opt/mon-recours-ci` (code + corpus), `/etc/mon-recours-ci` (env, comptes), `/var/lib/monrecours` (audit) |
Ports | **443** public ; 3000 et 8765 **en boucle locale uniquement** |
TLS | Certificat valide, redirection 80→443, HSTS — sans TLS le cookie `Secure` n'est jamais renvoyé |
Secrets | `/etc/mon-recours-ci/env` en `600 monrecours`, générés sur place |
Comptes | fichier `comptes.json` en `600 monrecours`, empreintes scrypt uniquement |
Accès | **restreindre la préproduction** (liste d'IP dans nginx) : une administration ne s'expose pas ouverte |

## 5. Limiteur de débit : ce qu'il protège, et ce qu'il ne protège pas

### Mesuré

| Test | Résultat |
|---|---|
16 requêtes du même visiteur sur `/api/ouvrir` | **12 × 200, puis 4 × 429** |
Requête d'un autre visiteur | 200 — non bloqué |
Connexions : 5 tentatives/minute par visiteur **et** par adresse | code |

### Ce que c'est

`web/src/lib/server/limiteur.ts` : une **`Map` en mémoire**, fenêtre glissante de
60 s, clé = dernière valeur de `X-Forwarded-For`. Rien de partagé.

### Ce que ce n'est pas

1. **Aucune protection distribuée.** Sur plusieurs instances (serverless, ou deux
   processus derrière nginx), la limite réelle est de `12 × nombre d'instances`.
   Redémarrer le service remet les compteurs à zéro.
2. **Pas d'anti-force brute par compte.** 5 tentatives/minute = 7 200 par jour et
   par adresse. Avec scrypt (N=16384) et un mot de passe de 12 caractères minimum,
   c'est hors de portée ; avec un mot de passe court toléré autrefois, non.
3. **`X-Forwarded-For` doit être réécrit par le proxy.** Le modèle nginx le fait
   (`proxy_set_header X-Forwarded-For $remote_addr`) ; sans cela, un client
   forgerait son identité et contournerait la limite par visiteur.
4. **Pas d'alerte.** Aucune supervision des 429 : une attaque en cours ne se voit
   que dans les journaux.

### Avant une mise en service réelle

| Priorité | Amélioration |
|---|---|
**P0** | `limit_req` nginx sur `/api/` (déjà dans le modèle : 20 r/m, `burst=10`) — première barrière, avant l'application |
**P1** | Verrouillage progressif par **compte** (pas seulement par adresse) après N échecs, avec délai croissant |
**P1** | Alerte sur pic de 429 et sur échecs de connexion répétés |
**P2** | Limiteur partagé (Redis ou table SQLite) si plusieurs instances |
**P2** | CAPTCHA ou preuve de travail en dernier recours, jamais en premier |

## 6. Risques identifiés

| # | Risque | Gravité | Mitigation |
|---|---|---|---|
1 | **Serveur unique** : panne = service arrêté | moyenne | sauvegardes hors serveur + procédure de reconstruction documentée |
2 | **Sauvegardes des récits jamais testées en restauration** | **élevée** | `bin/sauvegarde.py` existe et est prouvé sur données synthétiques ; **rester à faire sur un volume réel** |
3 | **Disque non chiffré** : les récits sont en clair sur le VPS | **élevée** | chiffrement au repos du volume, ou disque chiffré à l'installation |
4 | **Limiteur en mémoire** (cf. §5) | moyenne | `limit_req` nginx en P0 |
5 | **Aucune supervision** (`/api/sante` existe, personne ne le regarde) | moyenne | sonde externe + alerte |
6 | **80 % du corpus vient d'OCR**, sans relecture humaine | **élevée** | relecture juridique ; les citations affichent déjà `origine_texte` et `confiance_ocr` |
7 | **Aucun suivi d'abrogation** | **élevée** | table de vigueur + veille ; champ `modifications` vide sur 34/34 références |
8 | **17 domaines sur 24 sans texte** | élevée | abstention explicite ; ne pas annoncer une couverture inexistante |
9 | **Mises à jour non planifiées** (Node, Next, dépendances) | moyenne | `npm audit` en CI ; fenêtre de maintenance |
10 | **Préproduction accessible publiquement** si l'on oublie la liste d'IP | **élevée** | restriction nginx dès l'installation |

## 7. Décisions qui ne sont pas techniques

1. **Louer ou non** un VPS de test (≈ 5–12 €/mois) — conditionne toute validation réelle de l'administration.
2. **Nom de domaine** et sous-domaine de test.
3. **Durée de conservation** des consultations (90 jours proposés, non validés juridiquement).
4. **Qui reçoit** le compte d'administration de test.
5. **Relecture juridique** : sans elle, le produit reste une démonstration techniquement sérieuse, pas un service juridique.

Tant que les points 1 et 5 ne sont pas tranchés, tout développement
supplémentaire de l'administration restera **non exercé** : les tests unitaires
couvrent la logique, pas une connexion réelle derrière TLS.
