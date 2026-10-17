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
2. **Code** : cloner le dépôt dans `/opt/mon-recours-ci` avec les PDF du corpus
   (ils ne sont pas dans le dépôt), puis vérifier :
   `python3 tests/run_all.py` doit finir par `VERDICT=SUCCES`.
3. **Utilisateur système** dédié, sans droits d'administration : `monrecours`.
4. **Secrets** dans `/etc/mon-recours-ci/env` (droits `600`, propriétaire
   `monrecours`) — voir `env.exemple`. Jamais dans le dépôt.
5. **Interface** : `cd web && npm ci && npm run build && npm run verifier:secrets`.
6. **Services** : copier `monrecours-moteur.service` et `monrecours-web.service`
   dans `/etc/systemd/system/`, puis `systemctl enable --now` les deux.
7. **nginx + HTTPS** : adapter `nginx.conf.exemple` (nom de domaine), puis
   `certbot --nginx -d votre-domaine.ci`.
8. **Purge** : planifier `purger-consultations.mjs` (voir
   `monrecours-purge.timer`) avec la durée de conservation décidée.
9. **Contrôle** : depuis un téléphone, faire un parcours complet ; vérifier
   qu'aucune page n'est en cache côté navigateur pour `/api/*`.

## Avant d'ouvrir au public (indispensable, non fait)

- Durée de conservation des récits décidée et annoncée aux utilisateurs.
- Mentions légales et politique de confidentialité (loi n° 2013-450 relative à
  la protection des données à caractère personnel : déclaration auprès de
  l'autorité compétente à vérifier avec un juriste).
- Relecture des fiches par un juriste ; confirmation des numéros d'urgence.
- Revue de sécurité externe ; sauvegardes chiffrées de `DOSSIERS/` et de la base.
- Supervision : `GET /api/sante` doit renvoyer `ok: true`.
