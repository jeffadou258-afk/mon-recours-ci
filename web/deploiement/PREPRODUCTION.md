# Préproduction de l'administration — procédure (NON exécutée)

Cette procédure installe l'interface **avec l'espace d'administration** sur un
serveur de test isolé, avec des **données synthétiques uniquement**. Elle n'a
pas encore été exécutée : aucun serveur de préproduction n'existe à ce jour.

La démonstration publique (Vercel, `MONRECOURS_MODE=demo`) n'est **pas** une
cible : l'administration y est volontairement fermée, le moteur Python ne
peut pas y tourner et il n'y a ni disque persistant ni systemd.

## Décisions à prendre par le propriétaire avant de commencer

| Décision | Pourquoi |
|---|---|
| Louer un serveur de test (VPS Linux) | aucun serveur n'existe |
| Choisir un sous-domaine de test (ex. `preprod.votre-domaine.ci`) | HTTPS obligatoire : le cookie de session est `Secure` |
| Restreindre l'accès (liste d'adresses IP dans nginx, ou authentification nginx en plus) | une préproduction ne doit pas être une administration ouverte sur Internet |
| Désigner qui reçoit le compte de test | aucun compte n'existe par défaut |

## Règles de la préproduction

- `MONRECOURS_MODE` **absent** (sinon l'administration est fermée).
- **Aucun** `MONRECOURS_LLM_*`.
- Corpus et consultations : uniquement les données synthétiques du dépôt.
  Aucun dossier réel dans `DOSSIERS/`.
- Secrets **propres à la préproduction** (jamais ceux de la future production).
- Comptes de test : `scripts/creer-compte.mjs`, empreintes uniquement.

## Installation

Suivre `README.md` (étapes 1 à 7) sur le serveur de test, avec ces précisions :

```bash
# 1. Secret de session propre à la préproduction (affiché nulle part)
sudo sh -c 'umask 077; printf "MONRECOURS_SESSION_SECRET=%s\n" "$(node -e "process.stdout.write(require(\"crypto\").randomBytes(32).toString(\"base64url\"))")" >> /etc/mon-recours-ci/env'

# 2. Fichier de comptes protégé
sudo install -o monrecours -g monrecours -m 0600 /dev/null /etc/mon-recours-ci/comptes.json
cd /opt/mon-recours-ci/web
node scripts/creer-compte.mjs essai-admin@votre-domaine.ci administrateur   # mot de passe demandé 2 fois, masqué
node scripts/creer-compte.mjs essai-lecteur@votre-domaine.ci lecteur
#   → copier les deux lignes JSON produites dans un tableau :
#     [ {…administrateur…}, {…lecteur…} ]
sudo -u monrecours sh -c 'cat > /etc/mon-recours-ci/comptes.json'   # coller, puis Ctrl-D

# 3. Variables d'administration (une seule source de comptes)
sudo sh -c 'cat >> /etc/mon-recours-ci/env' <<'EOF'
MONRECOURS_COMPTES_FICHIER=/etc/mon-recours-ci/comptes.json
MONRECOURS_AUDIT_FICHIER=/var/lib/monrecours/audit.jsonl
EOF

# 4. Unité systemd à jour (StateDirectory, UMask) puis redémarrage
sudo cp deploiement/monrecours-web.service /etc/systemd/system/
sudo systemctl daemon-reload && sudo systemctl restart monrecours-web
```

## Vérification automatique (lecture seule)

```bash
sudo bash deploiement/verifier-preproduction.sh https://preprod.votre-domaine.ci
```

Le script vérifie, sans afficher aucune valeur : droits du fichier
d'environnement, absence du mode démo et de LLM, présence du secret, une
seule source de comptes, fichier de comptes `600 monrecours` contenant des
empreintes scrypt, répertoire d'audit `700 monrecours`, unité systemd
(`ProtectSystem=strict`, `NoNewPrivileges`, `StateDirectory`, `UMask`,
`User`), HTTPS, HSTS, redirection HTTP → HTTPS, `/admin` redirigé sans
session, refus d'identifiants synthétiques sans cookie, refus d'une origine
étrangère. Il doit finir par `CONFORME`.

## Vérification manuelle (navigateur)

1. `/admin` sans être connecté → page de connexion.
2. Compte lecteur → « Espace réservé aux administrateurs », aucune donnée.
3. Compte administrateur → tableau de bord ; vérifier que les sections sans
   service affichent « Non disponible » / « Non connecté » et qu'aucune
   consultation n'est accessible.
4. Déconnexion → retour à `/connexion`, `/admin` redemande la connexion.
5. Six mots de passe faux de suite → message « Trop de tentatives ».
6. `sudo tail /var/lib/monrecours/audit.jsonl` → événements présents, aucun
   mot de passe.

## Retour arrière

| Besoin | Action | Effet |
|---|---|---|
| Fermer l'administration tout de suite | retirer `MONRECOURS_COMPTES_FICHIER` de `/etc/mon-recours-ci/env`, `systemctl restart monrecours-web` | `/connexion` répond « non configuré », `/admin` fermé |
| Retirer un seul compte | supprimer son entrée de `comptes.json` | effet immédiat, sans redémarrage |
| Fermer toutes les sessions | changer `MONRECOURS_SESSION_SECRET`, redémarrer | tous les cookies d'administration invalides |
| Revenir au code précédent | `git checkout <étiquette>`, `npm ci && npm run build`, redémarrer | le moteur Python n'est pas concerné |
