# Préparer la mise en ligne (NON effectuée)

Ce dossier décrit une installation sur **un seul serveur Linux** (VPS). Rien
n'a été déployé. Chaque étape demande une décision et un accès du responsable
du projet : achat d'un serveur et d'un nom de domaine, accord sur l'hébergement
des données.

## Pourquoi un seul serveur, et pas Vercel

Le moteur (`bin/serveur_api.py`) refuse d'écouter ailleurs que sur `127.0.0.1`,
et c'est voulu : il n'a ni TLS, ni comptes. L'interface Next.js doit donc
tourner **sur la même machine** que lui. Un hébergement serverless (Vercel)
ne peut pas le joindre sans exposer le moteur, ce qui exigerait une revue de
sécurité qui n'a pas eu lieu.

```
Internet ──HTTPS──► nginx (443) ──► Next.js (127.0.0.1:3000) ──► moteur (127.0.0.1:8765)
                                    limite par visiteur            clé d'API, débit global
```

## Étapes

1. **Serveur** : Ubuntu LTS, Python 3.9+, Node.js 20.9+, nginx, certbot.
2. **Code** : cloner le dépôt dans `/opt/mon-recours-ci`. Les PDF officiels ne
   sont pas dans le dépôt : soit les copier depuis la branche
   `corpus/archives-pdf`, soit garder `MONRECOURS_PDF_NON_DISTRIBUES=1` (le
   moteur vérifie alors les empreintes des textes extraits).
   Python du moteur dans un environnement virtuel (Ubuntu 24.04 refuse
   `pip install` dans le Python du système) :
   `python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
   (fpdf2 : sans lui, aucun courrier PDF). Lancer les tests avec
   `MONRECOURS_PDF_NON_DISTRIBUES=1 .venv/bin/python tests/run_all.py` doit finir
   par `VERDICT=SUCCES`.
3. **Utilisateur système** dédié, sans droits d'administration : `monrecours`.
4. **Secrets** dans `/etc/mon-recours-ci/env` (droits `600`, propriétaire
   `monrecours`) — voir `env.exemple`. Jamais dans le dépôt.
5. **Interface** : `cd web && npm ci && npm run build && npm run verifier:secrets`.
6. **Services** : copier `monrecours-moteur.service` et `monrecours-web.service`
   dans `/etc/systemd/system/`, puis `systemctl enable --now` les deux. Créer
   `DOSSIERS/` et `RUNTIME/` (propriétaire `monrecours`, droits 700). `RUNTIME/` porte
   l'état de l'incident du fournisseur de langage et le registre du plafond ; l'unité du
   moteur le déclare en écriture et ne démarre pas s'il manque.
7. **nginx + HTTPS** : adapter `nginx.conf.exemple` (nom de domaine), puis
   `certbot --nginx -d votre-domaine.ci`.
8. **Purge** : planifier `purger-consultations.mjs` (voir
   `monrecours-purge.timer`) avec la durée de conservation décidée.
9. **Sauvegarde** : créer la clé (`docs/SAUVEGARDE_RESTAURATION.md`, §3), en
   garder une copie hors du serveur, puis installer
   `monrecours-sauvegarde.service` + `monrecours-sauvegarde.timer` (chaque nuit,
   archive vérifiée aussitôt). **Faire une restauration d'essai** dans un
   répertoire neuf avant d'ouvrir le service. La copie des archives hors du
   serveur reste à choisir.
10. **Contrôle** : depuis un téléphone, faire un parcours complet ; vérifier
   qu'aucune page n'est en cache côté navigateur pour `/api/*`.

## Avant d'ouvrir au public (indispensable, non fait)

- Durée de conservation des récits décidée et annoncée aux utilisateurs.
- Mentions légales et politique de confidentialité (loi n° 2013-450 relative à
  la protection des données à caractère personnel : déclaration auprès de
  l'autorité compétente à vérifier avec un juriste).
- Relecture des fiches par un juriste ; confirmation des numéros d'urgence.
- Revue de sécurité externe ; sauvegardes chiffrées de `DOSSIERS/` et de la base.
- Supervision : `GET /api/sante` doit renvoyer `ok: true`.

## Coûts récurrents (19/10/2026) — montants connus et estimations

| Poste | Montant | Nature |
|---|---|---|
| Serveur unique (VPS, 2 vCPU, 4 Go) | à chiffrer sur devis de l'hébergeur choisi | décision du propriétaire |
| Nom de domaine | à chiffrer auprès du registraire | décision du propriétaire |
| Certificat HTTPS (Let's Encrypt) | 0 | connu |
| Vercel | non nécessaire : l'interface tourne sur le serveur du moteur (le plan gratuit Hobby est réservé à l'usage non commercial ; Pro : 20 $/mois — [source](https://vercel.com/pricing)) | connu |
| Modèle de langage (facultatif) | ≈ 0,40 à 8 $ pour 1 000 consultations selon le modèle | **estimation**, voir `docs/COUCHE_LANGAGE.md` |
| Sauvegardes hors serveur | selon le stockage choisi | décision du propriétaire |
| Relecture juridique des fiches | honoraires à convenir | décision du propriétaire |

## Essai local

`bash scripts/demarrer-local.sh` (depuis la racine du dépôt) démarre le moteur et
l'interface sur la machine, avec des clés tirées au hasard ; `--tests` lance
d'abord tous les contrôles.


## Déploiement d'une version validée (sauvegarde + retour arrière automatique)

```bash
sudo -u monrecours git -C /opt/mon-recours-ci fetch origin feature/admin-authentification
sudo -u monrecours git -C /opt/mon-recours-ci show origin/feature/admin-authentification:web/deploiement/deployer.sh > /tmp/deployer.sh
sudo bash /tmp/deployer.sh <commit validé par la CI>
```

`deployer.sh` sauvegarde (`/var/backups/mon-recours-ci/`, 600) avant tout changement,
n'avance qu'en avance rapide, lance `maj.sh`, fait les tests de fumée (interface,
moteur, intégrité du corpus, RUNTIME inscriptible, route d'administration protégée,
dossiers préservés) et revient seul au commit précédent si un contrôle échoue.
Aucun secret n'est affiché ; DeepSeek n'est jamais appelé.
