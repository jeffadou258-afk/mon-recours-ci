# Mon Recours CI — interface web

Application Next.js (App Router, TypeScript strict, PWA mobile d'abord) qui permet
à une personne de décrire sa situation, de répondre aux questions de clarification
et de lire le résultat du **moteur juridique existant** (`bin/serveur_api.py`).

L'interface ne contient **aucune logique juridique** : elle relaie, assainit et
affiche ce que le moteur renvoie. Elle ne fabrique ni source, ni citation, ni
réponse.

---

## Architecture

```
Navigateur ──(même origine)──► Next.js /api/ouvrir, /api/repondre, /api/sante
                                  │  • valide l'entrée (limites du moteur)
                                  │  • génère l'identifiant de dossier (cookie signé)
                                  │  • ajoute la clé X-API-Key (serveur uniquement)
                                  │  • retire chemins de fichiers et identifiants internes
                                  ▼
                       bin/serveur_api.py (127.0.0.1:8765)  ── moteur déterministe
```

| Route de l'interface | Route du moteur | Rôle |
|---|---|---|
| `GET /api/sante` | `GET /sante` | couverture du catalogue, état du corpus |
| `POST /api/ouvrir` `{demande}` | `POST /ouvrir` | qualification, fiches, questions, urgence |
| `POST /api/repondre` `{reponses}` | `POST /repondre` | analyse, citations, démarches |

Aucune autre route n'est appelée : ce sont les trois seules que le moteur implémente.

### Pourquoi une couche serveur

1. **La clé du moteur ne doit jamais atteindre le navigateur.**
2. **Le moteur ne cloisonne pas les dossiers** : quiconque connaît un `dossier_id`
   peut répondre dedans. L'interface tire donc l'identifiant au hasard côté serveur
   (`web-<uuid>`) et le stocke dans un cookie `HttpOnly`, `SameSite=Strict`, signé
   par HMAC. Le navigateur ne le voit jamais ; un cookie forgé est rejeté.
3. **Le moteur renvoie des chemins de fichiers** (`traceabilite`,
   `brouillon.genere.fichier_txt`) : ils sont retirés avant l'envoi.

### Fichiers principaux

```
src/app/                    pages (accueil, /consultation, /comprendre, /hors-ligne), routes /api, manifeste PWA
src/components/             Parcours, Clarification, Resultats, CarteCitation, Alertes, Badges…
src/lib/validation.ts       limites partagées client/serveur (4000 / 1000 caractères, comme core/service.py)
src/lib/libelles.ts         traduction des codes du moteur en français courant (aucune règle de droit)
src/lib/server/handlers.ts  gestionnaires /api/* (API Web standard Request/Response)
src/lib/server/assainir.ts  liste blanche des champs transmis au navigateur
src/lib/server/session.ts   identifiant de dossier + cookie signé
src/lib/server/moteur.ts    client HTTP du moteur (délai, erreurs réseau)
public/sw.js                service worker : fichiers statiques seulement, JAMAIS /api/*
apercu/                     banc d'aperçu pour les tests navigateur (voir plus bas)
tests/                      unitaires, composants, intégration (moteur réel), bout en bout (Chromium)
scripts/verifier-secrets.mjs  contrôle qu'aucun secret n'est dans le code client
```

---

## Installation

Prérequis : **Node.js ≥ 20.9**, **Python 3.9+** (pour le moteur), sur la même machine.

```bash
cd mon-recours-ci/web
npm install
cp .env.example .env.local     # puis remplir les valeurs (voir ci-dessous)
```

### Variables d'environnement (serveur uniquement)

| Variable | Obligatoire | Rôle |
|---|---|---|
| `MONRECOURS_API_URL` | non (défaut `http://127.0.0.1:8765`) | URL du moteur. En `http`, seul un hôte local est accepté. |
| `MONRECOURS_API_KEY` | **oui** | même valeur que celle donnée au moteur (≥ 16 caractères) |
| `MONRECOURS_SESSION_SECRET` | **oui** | secret de signature du cookie (≥ 32 caractères, aléatoire) |
| `MONRECOURS_API_TIMEOUT_MS` | non (défaut 15000) | délai maximal d'attente du moteur |

Aucune variable `NEXT_PUBLIC_*` : rien n'est exposé au navigateur. Sans clé ou
sans secret, l'interface refuse d'appeler le moteur et affiche « service mal configuré ».

Générer des valeurs :

```bash
node -e "console.log(require('crypto').randomBytes(24).toString('base64url'))"   # clé du moteur
node -e "console.log(require('crypto').randomBytes(32).toString('base64url'))"   # secret de session
```

---

## Lancement en local

Terminal 1 — le moteur (depuis la racine du dépôt) :

```bash
export MONRECOURS_API_KEY="<la même clé que dans web/.env.local>"
python3 bin/serveur_api.py            # http://127.0.0.1:8765
```

Terminal 2 — l'interface :

```bash
cd web
npm run dev                           # http://localhost:3000
# ou, version optimisée :
npm run build && npm start
```

---

## Tests

| Commande | Ce qui est testé | Moteur |
|---|---|---|
| `npm test` | validation, cookie signé, assainissement, gestionnaires /api, rendu des composants | réponses **réelles enregistrées** (`tests/fixtures`) |
| `npm run test:integration` | parcours complet, hors catalogue, refus, urgence, cookie forgé, mauvaise clé, débit 429, moteur arrêté | **moteur réel** démarré par le test |
| `npm run test:e2e` | navigateur Chromium au format téléphone : saisie, clarification, résultat, erreurs réseau, débordement, cookie HttpOnly, secrets du bundle ; captures dans `tests/e2e/captures/` | **moteur réel** |
| `npm run typecheck` | TypeScript strict (après `npm install`) | — |
| `npm run build && npm run verifier:secrets` | absence de clé, de secret et de nom de variable serveur dans `.next/static` | — |

Les tests d'intégration et de bout en bout lancent le moteur via sa propre fabrique
`creer_serveur(port=0)` : aucun fichier du moteur n'est modifié. Pour le navigateur :
`npx playwright install chromium` la première fois.

### Banc d'aperçu (`apercu/`)

Outil de **test**, pas de production. Il sert les mêmes composants, la même feuille de
style et les mêmes gestionnaires `/api/*` que l'application Next.js, sans Next.js. Il a
permis de piloter un vrai navigateur dans un environnement où Next.js n'était pas
installable. `npm run apercu` le lance sur le port 3000.

---

## Règles d'affichage tenues

- `statut_reponse` est affiché tel quel ; `CONCLUSION_IMPOSSIBLE` n'est jamais tourné en réponse positive.
- Chaque citation montre son état de vérification et son mode de lecture. Un texte
  `OCR_AUTO` non recoupé n'est **jamais** affiché « vérifié ».
- Le texte cité est reproduit sans retouche. Les extraits du moteur sont limités
  (≈ 180 caractères, parfois coupés au milieu d'un mot) : la coupure est signalée
  par « […] » et un renvoi au document officiel.
- La « lecture » du moteur est présentée comme une reformulation, séparée du texte.
- Les verrous humains apparaissent dans un encadré non masquable.
- En urgence CRITIQUE seulement, les numéros d'urgence sont affichés (police
  170 / 110 / 111, pompiers 180, assistance médicale 185 — source : gouvernement du
  Canada, page Côte d'Ivoire, consultée le 2026-10-17 ; **à faire confirmer**).
- Aucune donnée n'est stockée par l'interface (pas de compte, pas d'historique,
  pas de `localStorage`). Le service worker ne met jamais `/api/*` en cache.
- La page de saisie annonce que la description n'est envoyée à aucun modèle
  d'IA : **ce texte devra être revu** le jour où un fournisseur LLM sera activé.

---

## Sécurité des dépendances

| Paquet | Version | Pourquoi |
|---|---|---|
| `next` | **15.5.28** | dernière version corrigée de la branche 15.5 (maintenance LTS). Corrige les avis d'octobre 2026 (GHSA-673q-mjm6-r5xr critique, CVE-2026-96889 / GHSA-2464-fhr4-w9xw critique, GHSA-p3m5-59mp-jv5r élevé), ceux de septembre 2026 (15.5.27) et les correctifs React2Shell de décembre 2025. Pas de passage à la 16 : changement majeur non nécessaire pour corriger. |
| `react`, `react-dom` | **19.1.10** | même ligne que les correctifs React d'octobre 2026 (les failles touchent `react-server-dom-*`, embarqué par Next.js ; React est aligné par cohérence). |
| `playwright` (dev) | **≥ 1.55.1** | GHSA-7mvr-c777-76hp (élevé) : téléchargement des navigateurs sans vérification TLS avant 1.55.1. |
| `postcss` (via `next`) | **≥ 8.5.23**, forcé par `overrides` | Next.js 15.5.28 fige `postcss@8.4.31`, visé par GHSA-qx2v-qp2m-jg93 (modéré, corrigé en 8.5.10), GHSA-6g55-p6wh-862q / CVE-2026-45623 (élevé, 8.5.12), GHSA-r28c-9q8g-f849 (élevé, 8.5.18) et GHSA-fxqj-rqcc-2cmp (modéré, 8.5.23). Mise à jour dans la même version majeure 8, compatible. |

**Pourquoi un `override` plutôt que Next.js 16.** `npm audit fix --force` proposerait un
changement de version majeure de Next.js. Ce n'est pas nécessaire : PostCSS 8.5.x reste
compatible avec l'API 8.x utilisée par Next.js, alors qu'un passage à Next.js 16 imposerait
des changements cassants et ne garantit pas, à lui seul, une version de PostCSS ≥ 8.5.23.
Exposition réelle de cette application : faible. PostCSS ne traite que notre propre
feuille de style, au moment du build ; aucun CSS fourni par un visiteur n'est analysé.
À retirer quand une version de Next.js 15.5 (ou la version adoptée) embarquera elle-même
PostCSS ≥ 8.5.23 : vérifier avec `npm ls postcss --all`.

Sources : [Next.js, 14 oct. 2026](https://nextjs.org/blog/nextjs-security-update-october-14-2026),
[Next.js, 30 sept. 2026](https://nextjs.org/blog/september-2026-security-release),
[React GHSA-xqc2-xf4c-x3h3](https://github.com/react/react/security/advisories/GHSA-xqc2-xf4c-x3h3),
[OSV GHSA-7mvr-c777-76hp](https://osv.dev/vulnerability/GHSA-7mvr-c777-76hp),
[avis de sécurité PostCSS](https://github.com/postcss/postcss/security/advisories),
[NVD CVE-2026-45623](https://nvd.nist.gov/vuln/detail/CVE-2026-45623).

### Scripts d'installation (npm 12)

`package.json` refuse explicitement les scripts d'installation de `esbuild`, `fsevents`
et `sharp` (`"allowScripts": { "esbuild": false, "fsevents": false, "sharp": false }`).
La CI installe avec `--ignore-scripts` et tous les tests passent ainsi :

- **fsevents** (macOS seulement) est une dépendance facultative de surveillance de
  fichiers, livrée précompilée ; inutile à l'application.

- **sharp** sert uniquement à l'optimisation d'images de Next.js, désactivée ici
  (`images.unoptimized`). Ses binaires précompilés arrivent par les paquets
  `@img/sharp-*` ; son script ne sert qu'à compiler depuis les sources quand aucun
  binaire n'existe pour la plateforme.
- **esbuild** n'est utilisé que par les outils de test (`tsx`, banc d'aperçu), pas par
  Next.js. Son binaire arrive par le paquet de plateforme `@esbuild/*` ; le script
  d'installation ne fait que le vérifier.

Si les tests échouaient sans ces scripts, approuver la version exacte installée
(`npm approve-scripts esbuild`), jamais `--all` ni `--dangerously-allow-all-scripts`.

## Avant tout déploiement (non fait, et nécessaire)

1. **Le moteur n'écoute que sur 127.0.0.1** et refuse de démarrer autrement. Un
   déploiement Vercel ne peut donc pas le joindre. Il faut soit héberger interface et
   moteur sur le même serveur, soit exposer le moteur derrière TLS avec une revue de
   sécurité (CLAUDE_HANDOFF.md §6 ter).
2. **Limite de débit partagée** : le moteur limite à 30 requêtes / minute **par clé**.
   Tous les visiteurs passant par la même clé, la limite est globale. Une limitation
   par visiteur côté interface (ou un débit moteur adapté) est nécessaire.
3. **Conservation des récits** : le moteur écrit chaque demande dans `DOSSIERS/`
   (traçabilité). Une politique de durée de conservation et de suppression est à définir.
4. **Brouillon de courrier** : le moteur en prépare un, mais l'API ne transmet pas son
   contenu. Il faudrait une évolution du contrat (non faite ici) pour l'afficher.
5. Faire confirmer les numéros d'urgence et les libellés par l'équipe et un juriste.
6. Audit de sécurité externe, revue données personnelles, TLS, journalisation centralisée.
