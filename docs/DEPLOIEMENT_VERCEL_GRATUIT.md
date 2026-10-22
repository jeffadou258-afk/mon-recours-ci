# Déploiement gratuit sur Vercel — ce qui passe, ce qui ne passe pas

Audit du 22/10/2026. Aucun projet créé, aucun déploiement, aucun commit poussé.
Limites du plan Hobby relevées le même jour sur `vercel.com/docs` (fonctions,
cron, fair use) et dans les conditions d'utilisation.

## Verdict

**L'interface se déploie gratuitement. Le produit, non.**

Mon Recours CI n'est pas une application Next.js : c'est un **moteur Python** qui
détient l'état (corpus SQLite de 5 593 articles, dossiers sur disque), derrière une
interface qui ne fait que relayer des requêtes authentifiées. Sur Vercel, il n'y a
ni processus permanent, ni disque partagé : le moteur n'a nulle part où tourner.

Une URL qui répond n'est donc pas une application juridique opérationnelle. C'est
exactement la confusion que ce document existe pour éviter.

## 1. Limites du plan gratuit (relevées le 22/10/2026)

| Ressource | Hobby |
|---|---|
Mémoire d'une fonction | **2 Go / 1 vCPU** |
Durée maximale d'une fonction | **300 s** |
Taille du paquet d'une fonction | **250 Mo** décompressé |
Corps de requête/réponse | **4,5 Mo** — au-delà : 413 |
Transfert | 100 Go |
Invocations | 1 000 000 |
CPU | 4 h ; mémoire provisionnée 360 Go-h |
Déploiements | 100 / jour |
Journaux | **1 jour** de rétention |
Cron | 100 tâches/projet, mais **une exécution par jour maximum**, précision ±59 min |
Usage | **non commercial, personnel uniquement** |

Le dernier point est un **cadre contractuel**, pas une limite technique : les
conditions d'utilisation réservent le plan Hobby à un usage « personnel ou non
commercial », et la page Fair Use définit le commerce de façon large (paiement,
publicité, liens d'affiliation, et — selon la version de la page — les dons).
Un service d'aide juridique ouvert au public doit être examiné au regard de cette
clause avant toute mise en ligne durable. En cas de doute : demander à Vercel.

## 2. Ce qui fonctionne, ce qui ne fonctionne pas

| Fonction | Vercel gratuit | Raison vérifiée dans le code |
|---|---|---|
Pages, parcours de démonstration | **oui** (déjà en ligne) | fixtures + PDF statique, aucun disque |
Connexion admin (scrypt, cookie HMAC) | **techniquement oui** | `comptes.ts` lit `MONRECOURS_COMPTES` (JSON en variable) ; cookie signé sans état serveur |
Journal d'audit des connexions | **non** | `audit.ts` écrit dans `MONRECOURS_AUDIT_FICHIER` ; sans fichier, `console.warn` seulement → **1 jour de rétention** |
Limiteur de débit | **inefficace** | `Map` en mémoire, par instance, remise à zéro à chaque démarrage à froid |
`/api/ouvrir`, `/api/repondre` (moteur réel) | **non** | moteur Python absent ; `config.ts` refuse `http://` vers un hôte distant |
`/api/courrier/telecharger` | **non** | `handlers.ts:421` lit `courrier.chemin` **sur le disque local** → 404 |
Purge à 90 jours | **non** | repose sur un timer systemd ; un cron Vercel ne pourrait rien purger (pas de `DOSSIERS/`) |
Corpus (5 593 articles) | **non** | SQLite local, non écrivable en serverless, non partagé |
Sauvegarde chiffrée | **non** | exige un disque persistant et une clé hors ligne |

## 3. Pourquoi le moteur ne peut pas « suivre » l'interface

Trois verrous, chacun suffisant à lui seul :

1. **Le moteur écoute sur `127.0.0.1:8765`** et ne sait pas faire de TLS. Il n'est
   joignable que depuis la machine où il tourne.
2. **`lireConfig` refuse `http://` vers un hôte distant** (garde-fou de
   `config.ts`) : un moteur distant devrait être en HTTPS, ce qu'il ne sait pas
   être sans reverse proxy devant lui.
3. **Les dossiers sont des fichiers** sur le disque du moteur, et la route PDF les
   lit localement. Même avec un moteur joignable, le PDF resterait introuvable.

## 4. Modifications de code nécessaires, par niveau

| Niveau | Travail | Durée | Verdict |
|---|---|---|---|
0 | Rien : la démonstration est déjà conforme | 0 | **état actuel** |
1 | Message explicite « moteur non connecté » au lieu d'une erreur brute | 2–4 h | utile, non bloquant (le garde-fou `nonConfigure` existe déjà) |
2 | Porter le moteur en fonctions Python + base distante (Neon/Supabase gratuit) + stockage objet | **semaines** | à ne pas engager maintenant |
3 | Garder le moteur sur une machine à disque persistant | 1 journée d'installation | seule voie vers le produit réel |

Le niveau 2 touche `core/base.py` (SQLite), l'état de dossier (fichier) et la
route PDF : ce n'est pas une adaptation, c'est une réécriture du socle de
persistance.

## 5. Variables d'environnement (noms seulement, aucune valeur créée)

**Déjà configurées sur la démonstration :** `MONRECOURS_MODE`, `MONRECOURS_SESSION_SECRET`.

**Nécessaires au produit réel (non configurées, et inutiles sans moteur) :**
`MONRECOURS_API_URL`, `MONRECOURS_API_KEY`, `MONRECOURS_COMPTES` (ou
`MONRECOURS_COMPTES_FICHIER`), `MONRECOURS_AUDIT_FICHIER`, `MONRECOURS_DOSSIERS`,
`MONRECOURS_DEBIT_VISITEUR`, `MONRECOURS_API_TIMEOUT_MS`.

Sur Vercel, `MONRECOURS_AUDIT_FICHIER` et `MONRECOURS_DOSSIERS` **n'ont pas de
valeur possible** : il n'existe pas de disque persistant. Les définir pointerait
vers un répertoire éphémère, donc vers une perte silencieuse.

## 6. Tester gratuitement sans dégrader la sécurité

| Option | Coût | Ce qu'elle permet | Risque |
|---|---|---|---|
**A. Local + tunnel HTTPS éphémère** (Cloudflare Quick Tunnel) | 0 € | atteindre l'application depuis un téléphone, moteur et données restant sur la machine | l'URL est publique tant que le tunnel tourne → à fermer après usage |
**B. Démonstration Vercel existante** | 0 € | montrer l'interface, sans aucune donnée | aucune — déjà en ligne, **ne pas y toucher** |
**C. Oracle Cloud « Always Free »** | 0 € mais compte + carte | un vrai serveur avec disque | c'est un VPS : hors autorisation actuelle |
**D. Neon/Supabase gratuit + portage** | 0 € | une base distante | semaines de développement, et le moteur resterait à héberger |

**Recommandation : A pour tester, B pour montrer.** Aucune des deux ne demande de
créer un compte administrateur ni de configurer un secret de compte.

Procédure A, quand elle sera autorisée :

```bash
# 1. moteur local
python3 bin/serveur_api.py --port 8765
# 2. interface, avec les variables de production locales
cd web && MONRECOURS_SESSION_SECRET=<32+ car.> MONRECOURS_API_KEY=<16+ car.> \
  MONRECOURS_API_URL=http://127.0.0.1:8765 npm run build && npm start
# 3. tunnel (aucun compte requis)
cloudflared tunnel --url http://localhost:3000
```

Le cookie de session est `Secure` : il n'est renvoyé qu'en HTTPS, ce que le
tunnel fournit.

## 7. Coût prévisible

**0 €** tant qu'on reste dans l'option A ou B.

Le produit réel n'est **pas** gratuit sur Vercel : soit un hébergement moteur
(≈ 4–6 €/mois, cf. `docs/PREPRODUCTION_RESSOURCES.md`), soit des semaines de
réécriture. Il n'existe pas de combinaison « gratuit + opérationnel » aujourd'hui.

## 8. Étapes exactes d'un déploiement (pour plus tard, avec autorisation)

> **Avertissement opérationnel vérifié** : `web/.vercel/project.json` est lié au
> projet **`mon-recours-ci-demo`**. Lancer `vercel deploy` depuis `web/`
> **écraserait la démonstration publique**. Toute publication future doit d'abord
> changer de projet lié, ou se faire depuis un répertoire non lié.

1. Vérifier `git status` et le commit à publier.
2. Créer (si autorisé) un projet **distinct** — jamais réutiliser `mon-recours-ci-demo`.
3. Root Directory `web`, framework Next.js, `npm ci` / `npm run build`.
4. Variables : `MONRECOURS_MODE`, `MONRECOURS_SESSION_SECRET` uniquement.
5. Déployer **sans `--prod`**, puis vérifier l'URL réelle.
6. Refuser la publication si `/api/sante` n'annonce pas clairement l'absence de corpus.

## 9. Risques

| # | Risque | Gravité |
|---|---|---|
1 | Confondre une interface en ligne avec une application juridique opérationnelle | **élevée** — c'est le risque principal |
2 | Écraser la démonstration (lien Vercel local vers `mon-recours-ci-demo`) | **élevée** |
3 | Usage commercial interdit sur Hobby (service public, dons, publicité) | moyenne |
4 | Journaux conservés 1 jour : audit admin perdu | moyenne |
5 | Corps limité à 4,5 Mo : un courrier volumineux échouerait | faible |
6 | Suspension d'un projet Hobby sans préavis (conditions) | faible mais réelle |

## 10. Ce qui n'a pas été fait

Aucun projet créé · aucune variable ajoutée · aucun secret généré · aucun compte
créé · aucun déploiement · aucun commit poussé · démonstration publique non
modifiée (vérifiée en lecture seule : HTTP 200, en-tête `X-Mode: demonstration`).
