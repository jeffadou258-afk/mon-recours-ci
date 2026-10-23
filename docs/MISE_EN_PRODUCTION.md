# Mise en production réelle — plan d'exécution

Rédigé le 22/10/2026. **Rien n'a été commandé, installé à distance ni déployé.**
Ce document décrit ce qui est prêt, ce qui bloque, l'infrastructure nécessaire,
son coût, et les commandes exactes à exécuter le jour où la décision sera prise.

Documents liés : `web/deploiement/README.md` (installation), `web/deploiement/PREPRODUCTION.md`
(administration), `docs/ADMINISTRATION.md` (parcours de connexion),
`docs/PREPRODUCTION_RESSOURCES.md` (ressources et risques),
`docs/VEILLE_VIGUEUR.md` (corpus : technique vs juridique).

## 1. Architecture retenue : un seul serveur, et pourquoi

```
Internet ──HTTPS 443──► nginx ──► Next.js 127.0.0.1:3000 ──► moteur Python 127.0.0.1:8765
                         TLS, HSTS,          cookie signé,            clé d'API,
                         limit_req           limite par visiteur     corpus SQLite
                                                                      DOSSIERS/ (disque)
```

Le moteur **écrit** des dossiers sur disque, **lit** une base SQLite de 7,2 Mo et
n'expose ni TLS ni comptes. Ces trois faits imposent une machine à disque
persistant, avec les deux processus côte à côte. Aucun hébergement serverless ne
remplit ces conditions sans réécrire le socle de persistance.

## 2. Options réellement possibles

| Option | Coût | Faisable | Verdict |
|---|---|---|---|
**A. VPS unique** 2 vCPU / 4 Go / 40 Go NVMe (Hetzner, OVH, Scaleway, Contabo) | **≈ 4–6 €/mois** | oui, tout le code existe déjà | **recommandée** |
A + sauvegardes hors serveur (stockage objet) | **≈ +1–5 €/mois** | oui | **recommandée** |
B. Vercel + moteur ailleurs | 0 € pour l'interface, mais le moteur reste à héberger | non sans un second hébergement | sans intérêt : on paie quand même le moteur |
C. Portage serverless complet (fonctions Python + Postgres) | 0 € d'hébergement | non : semaines de réécriture | **à écarter maintenant** |
D. Oracle Cloud « Always Free » (4 vCPU ARM, 24 Go) | 0 €, mais compte + carte, capacité non garantie | oui | acceptable si l'on accepte l'aléa |
E. Railway / Render / Fly.io | offre gratuite à disque éphémère | non : perte des dossiers au redéploiement | à écarter |

**Total pour un service réel : ≈ 5 à 11 €/mois**, plus 10–15 €/an de domaine.
Ce n'est pas la gratuité, mais c'est le prix de la persistance et du TLS.

## 3. Ce qui est prêt, ce qui bloque

| Élément | État |
|---|---|
Interface Next.js | **prête** — build vert, 107 tests, typecheck 0 |
Moteur Python | **prêt** — 586 tests, corpus 5 593 articles |
Authentification admin | **prête** — 16/16 contrôles de bout en bout (`npm run verifier:admin`) |
Unités systemd (moteur, web, purge) | **écrites** — non exercées sur un vrai serveur |
nginx + TLS | **modèle écrit** — non exercé |
Contrôle de préproduction local | **écrit** (20 points) |
Contrôle d'instance déployée | **écrit et testé** : `npm run verifier:instance` → 14 PASS, 0 FAIL |
Sauvegarde chiffrée | **écrite et prouvée sur données synthétiques** — jamais sur volume réel |
**Hébergement** | **à commander** — décision du propriétaire |
**Nom de domaine** | **à acheter** — décision du propriétaire |
**Code sur le serveur** | **6 commits locaux non poussés** — voir §4, étape 5 |
**Relecture juridique** | **0 texte validé par un juriste** |

## 4. Procédure exacte

### Étape 0 — décisions préalables (propriétaire)

1. Fournisseur et région (Europe de préférence, données personnelles).
2. Nom de domaine et sous-domaine.
3. Budget accepté (≈ 5–11 €/mois + domaine).
4. **Qui** reçoit le compte administrateur.

### Étape 1 — serveur

Ubuntu 24.04 LTS, 2 vCPU, 4 Go, 40 Go. Clé SSH uniquement, pas de mot de passe root.

```bash
# sur le serveur, en root
adduser --system --group --home /opt/mon-recours-ci monrecours
apt update && apt upgrade -y
apt install -y nginx certbot python3-certbot-nginx ufw fail2ban \
               python3 python3-venv python3-pip poppler-utils tesseract-ocr-fra git
ufw allow 22/tcp && ufw allow 80/tcp && ufw allow 443/tcp && ufw --force enable
```

### Étape 2 — DNS

Enregistrement `A` du domaine vers l'IP du serveur. **Attendre la propagation**
avant certbot, sinon l'émission du certificat échoue.

### Étape 3 — code

Le dépôt est privé et **6 commits ne sont pas poussés**. Deux voies :

**Voie 1 (sans toucher à GitHub)** — transfert par bundle :

```bash
# machine locale
git bundle create /tmp/mon-recours-ci.bundle feature/admin-authentification
scp /tmp/mon-recours-ci.bundle root@SERVEUR:/tmp/
# serveur
git clone /tmp/mon-recours-ci.bundle /opt/mon-recours-ci
cd /opt/mon-recours-ci && git checkout feature/admin-authentification
```

**Voie 2** — pousser la branche sur GitHub (nécessite votre accord), puis
`git clone` avec une clé de déploiement en lecture seule.

Puis :

```bash
chown -R monrecours:monrecours /opt/mon-recours-ci
chmod 700 /opt/mon-recours-ci/DOSSIERS
install -d -o monrecours -g monrecours -m 700 /opt/mon-recours-ci/RUNTIME
```

### Étape 4 — dépendances

```bash
# Node 22
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs

# Python du moteur (fpdf2), dans un environnement dédié
cd /opt/mon-recours-ci
sudo -u monrecours python3 -m venv .venv
sudo -u monrecours .venv/bin/pip install -r requirements.txt

cd /opt/mon-recours-ci/web
sudo -u monrecours npm ci
sudo -u monrecours npm run build
```

> **Note** : l'unité du moteur appelle désormais
> `/opt/mon-recours-ci/.venv/bin/python` (corrigé le 22/10). Sans ce venv, l'export
> PDF échoue avec `No module named fpdf` — c'est exactement l'échec qu'avait connu
> la CI avant l'ajout de `requirements.txt`.

### Étape 5 — secrets

```bash
install -d -o monrecours -g monrecours -m 700 /etc/mon-recours-ci
install -o monrecours -g monrecours -m 600 /dev/null /etc/mon-recours-ci/env
cat > /etc/mon-recours-ci/env <<EOF
MONRECOURS_API_KEY=$(openssl rand -hex 32)
MONRECOURS_SESSION_SECRET=$(openssl rand -hex 32)
MONRECOURS_API_URL=http://127.0.0.1:8765
MONRECOURS_AUDIT_FICHIER=/var/lib/monrecours/audit.jsonl
MONRECOURS_DOSSIERS=/opt/mon-recours-ci/DOSSIERS
MONRECOURS_COMPTES_FICHIER=/etc/mon-recours-ci/comptes.json
NODE_ENV=production
PORT=3000
HOSTNAME=127.0.0.1
EOF
chown monrecours:monrecours /etc/mon-recours-ci/env && chmod 600 /etc/mon-recours-ci/env
```

**Ne jamais** définir `MONRECOURS_MODE=demo` ici.
**Ne jamais** définir `MONRECOURS_COMPTES` et `MONRECOURS_COMPTES_FICHIER` ensemble.

### Étape 6 — votre compte administrateur

```bash
install -o monrecours -g monrecours -m 600 /dev/null /etc/mon-recours-ci/comptes.json
echo '[]' | sudo -u monrecours tee /etc/mon-recours-ci/comptes.json > /dev/null
cd /opt/mon-recours-ci/web
sudo -u monrecours npm run compte:creer -- vous@votre-domaine.ci administrateur \
     --fichier /etc/mon-recours-ci/comptes.json
```

Mot de passe demandé deux fois, sans écho. Seule l'empreinte scrypt est écrite.

### Étape 7 — services

```bash
cp /opt/mon-recours-ci/web/deploiement/monrecours-*.service /etc/systemd/system/
cp /opt/mon-recours-ci/web/deploiement/monrecours-purge.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now monrecours-moteur monrecours-web
systemctl status monrecours-moteur monrecours-web --no-pager
```

**Le minuteur de purge n'est PAS activé à cette étape.** Il supprime
définitivement des dossiers : il ne doit tourner qu'après la décision sur la
durée de conservation, et après un essai en simulation (voir étape 10 bis).

### Étape 8 — TLS

```bash
cp /opt/mon-recours-ci/web/deploiement/nginx.conf.exemple /etc/nginx/sites-available/monrecours
sed -i 's/votre-domaine.ci/VOTRE-DOMAINE.ci/' /etc/nginx/sites-available/monrecours
ln -s /etc/nginx/sites-available/monrecours /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d VOTRE-DOMAINE.ci --redirect --agree-tos -m vous@votre-domaine.ci
```

### Étape 9 — vérifications (les trois, dans cet ordre)

```bash
cd /opt/mon-recours-ci/web
bash deploiement/verifier-preproduction.sh          # 20 points locaux
npm run verifier:admin                              # 16 contrôles d'administration
npm run verifier:instance -- https://VOTRE-DOMAINE.ci   # contrôle de l'instance déployée
```

Attendu : `16/16` et `0 FAIL`. **Si un contrôle échoue, le service ne s'ouvre pas.**

### Étape 10 — sauvegardes

```bash
install -d -o monrecours -g monrecours -m 700 /var/backups/monrecours
openssl rand -hex 32 > /etc/mon-recours-ci/cle-sauvegarde
chown monrecours:monrecours /etc/mon-recours-ci/cle-sauvegarde
chmod 600 /etc/mon-recours-ci/cle-sauvegarde

# quotidien, 03:10
echo '10 3 * * * cd /opt/mon-recours-ci && .venv/bin/python bin/sauvegarde.py sauvegarder \
  --dossiers DOSSIERS --base KNOWLEDGE/corpus_juridique.sqlite3 \
  --cle /etc/mon-recours-ci/cle-sauvegarde --sortie /var/backups/monrecours' \
  | sudo -u monrecours crontab -
```

**La clé vit hors du serveur de production** : une copie chiffrée hors du VPS
(inventaire ou coffre), sinon une perte du serveur perd aussi les sauvegardes.

**Test de restauration obligatoire avant ouverture** :

```bash
.venv/bin/python bin/sauvegarde.py verifier --archive /var/backups/monrecours/<archive>.enc \
  --cle /etc/mon-recours-ci/cle-sauvegarde
.venv/bin/python bin/sauvegarde.py restaurer --archive <archive>.enc \
  --sortie /tmp/restauration --base-destination /tmp/restauration.db \
  --cle /etc/mon-recours-ci/cle-sauvegarde
```

### Étape 10 bis — purge des consultations (après décision seulement)

```bash
# 1. simulation : on regarde ce qui SERAIT supprimé, rien n'est effacé
sudo -u monrecours MONRECOURS_DOSSIERS=/opt/mon-recours-ci/DOSSIERS \
  node web/scripts/purger-consultations.mjs --jours 90

# 2. si la liste est correcte ET la durée validée juridiquement :
systemctl enable --now monrecours-purge.timer
```

La sauvegarde de 03:10 précède la purge de 03:30 : un dossier supprimé reste
dans l'archive de la nuit. **Ne pas inverser** ces deux horaires.

### Étape 11 — supervision

- Sonde externe (gratuite) sur `https://VOTRE-DOMAINE.ci/api/sante`, alerte si
  le statut change ou si `articles` tombe à 0.
- `journalctl -u monrecours-web -u monrecours-moteur -f` pour les incidents.
- Alerte sur pic de 429 et sur échecs de connexion répétés.

## 5. Portes go/no-go avant ouverture au public

| # | Condition | Vérifiable par |
|---|---|---|
1 | `verifier:instance` → 0 FAIL | script |
2 | `verifier:admin` → 16/16 | script |
3 | `verifier-preproduction.sh` → 0 erreur | script |
4 | Restauration d'une archive réelle réussie | manuel |
5 | Journal d'audit écrit et sauvegardé | manuel |
6 | `/admin` restreint par IP (nginx) | manuel |
7 | Sauvegarde quotidienne + clé hors serveur | manuel |
8 | Corpus : intégrité connue et expliquée | `docs/VEILLE_VIGUEUR.md` |
9 | Politique de conservation (90 jours) tranchée | **décision** |
10 | Relecture juridique des fiches citées | **décision** |

Les portes 1 à 3 sont automatiques. Les portes 4 à 7 sont techniques et
réalisables le jour du déploiement. Les portes 9 et 10 ne dépendent pas de moi.

## 6. Risques principaux

| Risque | Gravité | Mitigation |
|---|---|---|
Serveur unique : panne = service arrêté | moyenne | sauvegardes hors site + procédure de reconstruction |
Disque non chiffré : récits en clair | **élevée** | chiffrement du volume à l'installation |
Sauvegarde jamais restaurée | **élevée** | porte n° 4, obligatoire |
80 % du corpus issu d'OCR, 0 % relu | **élevée** | affichage de la provenance ; relecture |
Aucun suivi d'abrogation | **élevée** | `bin/veille_vigueur.py` + relecture |
Limiteur en mémoire, par instance | moyenne | `limit_req` nginx en première barrière |
Pas de second facteur sur `/admin` | moyenne | restriction par IP + mot de passe long |
Perte de la clé de sauvegarde | **élevée** | copie hors serveur, dans un coffre |

## 7. Ce qui ne peut pas être automatisé

1. **La relecture juridique** : 92 fiches, 0 validée. Aucun script ne remplace un juriste ivoirien.
2. **Le choix de la durée de conservation** (90 jours proposés) : décision juridique.
3. **La vérification de vigueur** des 34 textes : `docs/VEILLE_VIGUEUR.md`.
4. **Le test de restauration sur volume réel** : à faire une fois, à la main.

## 8. Décisions demandées

| # | Décision | Effet si accordée |
|---|---|---|
1 | **Fournisseur + budget** (≈ 5–11 €/mois) | je prépare le serveur, sans le commander |
2 | **Domaine** (10–15 €/an) | TLS et URLs définitives |
3 | **Pousser les 6 commits** ou transfert par bundle | le serveur doit obtenir le code |
4 | **Créer votre compte** : je ne le ferai pas ; la commande est à l'étape 6 | administration utilisable |
5 | **Restreindre `/admin` par IP** | réduit le risque avant un second facteur |

Aucune de ces décisions ne peut être prise à votre place, et aucune n'a été
prise : ce document est un plan, pas une exécution.
