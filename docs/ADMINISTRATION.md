# Administration : pourquoi vous n'y aviez pas accès, et comment l'utiliser

État au 22/10/2026 après correction. Dépôt `feature/admin-authentification`.

## 1. Pourquoi la connexion ne vous a pas été présentée

Cinq causes, dans l'ordre de poids. **Aucune n'est un défaut du code
d'authentification** : le code était là, il n'était pas branché.

| # | Cause | Nature |
|---|---|---|
1 | **La seule URL publique est en mode démonstration.** Dans ce mode, `lireEtatAuth` renvoie `desactive_demo` : l'administration est fermée **par conception** | configuration |
2 | **Aucun compte n'a jamais été configuré** — ni `MONRECOURS_COMPTES`, ni `MONRECOURS_COMPTES_FICHIER` | configuration |
3 | **Le script de création de compte existait mais n'était exposé nulle part** : aucun `npm run`, aucune documentation | code (ergonomie) |
4 | **Aucune instance réelle n'a été déployée** : le produit tourne en local, jamais derrière une URL avec administration | déploiement |
5 | **Aucun test de bout en bout** du parcours connexion → tableau de bord → déconnexion : les tests couvraient les briques, pas le chemin | code (tests) |

Autrement dit : vous n'aviez pas un produit sans authentification, vous aviez
**une démonstration volontairement fermée**, et aucun moyen simple d'ouvrir
l'administration pour vous.

## 2. Ce qui existait déjà

| Élément | Fichier | Rôle |
|---|---|---|
Page de connexion | `app/connexion/page.tsx` + `components/FormulaireConnexion.tsx` | formulaire, messages d'état |
Mot de passe oublié | `app/connexion/mot-de-passe-oublie/page.tsx` | procédure humaine, aucun e-mail |
Tableau de bord | `app/admin/page.tsx` + `components/admin/TableauDeBord.tsx` | 6 sections |
Route de connexion | `app/api/connexion/route.ts` | POST, 5 tentatives/min |
Route de déconnexion | `app/api/deconnexion/route.ts` | POST, efface le cookie |
Hachage | `lib/server/auth/motdepasse.ts` | scrypt N=16384, comparaison en temps constant |
Jetons | `lib/server/auth/jeton.ts` | HMAC-SHA256, 2 h, `f` = empreinte du compte |
Comptes | `lib/server/auth/comptes.ts` | variable JSON ou fichier, entrées douteuses écartées |
Accès | `lib/server/auth/acces.ts` | décision serveur à chaque requête |
Journal | `lib/server/auth/audit.ts` | JSON Lines, optionnel |
Tableau | `lib/server/auth/tableau.ts` | agrégation, aucune valeur secrète |
Création de compte | `scripts/creer-compte.mjs` | scrypt, saisie masquée |

**29 tests** couvrent déjà ces briques : 18 sur l'authentification, 7 sur le
fichier de comptes, 4 sur le composant d'administration.

Propriétés déjà prouvées par ces tests : mot de passe jamais stocké en clair ·
réponse identique que le compte existe ou non · rôle jamais lu depuis le client ·
cookie `HttpOnly` + `SameSite=Strict` · jeton altéré/expiré/étranger refusé ·
session de 2 h vérifiée côté serveur · journal sans donnée sensible.

## 3. Ce qui manquait réellement

| Manque | Type | Corrigé le 22/10 |
|---|---|---|
Aucune entrée `npm` pour créer un compte | code | **oui** — `npm run compte:creer` |
`creer-compte.mjs` ne savait qu'imprimer du JSON, pas écrire le fichier de comptes | code | **oui** — option `--fichier` |
Aucun test du parcours complet | code | **oui** — `npm run verifier:admin`, 16 contrôles |
**Le journal d'audit écrivait l'adresse e-mail en clair** sur les connexions réussies, alors qu'une fonction d'empreinte existait pour l'éviter | **code (fuite)** | **oui** — empreinte imposée dans l'écrivain |
Documentation d'exploitation | doc | **oui** — ce fichier |
Instance réellement déployée | déploiement | non — hors autorisation |
Relecture juridique | métier | non — hors technique |

## 4. La faille corrigée aujourd'hui

`creerEcrivain` écrivait `compte: "prenom.nom@domaine.ci"` en clair dans
`audit.jsonl` sur `connexion_reussie`, `deconnexion`, `acces_administration` et
`acces_administration_refuse`. Les échecs, eux, passaient déjà par
`empreinteSaisie`.

La règle est désormais appliquée **dans l'écrivain**, pas chez les appelants :
aucune adresse ne peut sortir, même si un futur appel l'oublie. Sans secret
exploitable, le journal écrit `[adresse non journalisée]` plutôt que l'adresse.

Détecté par le contrôle automatique « aucune adresse e-mail en clair dans le
journal », qui échouait avant correction.

## 5. Créer votre compte administrateur

Sur la machine qui hébergera le service :

```bash
cd web
npm run compte:creer -- vous@exemple.ci administrateur --fichier /etc/mon-recours-ci/comptes.json
```

- mot de passe demandé **deux fois, sans écho** ;
- 12 caractères minimum, refus des mots de passe trop répétitifs ;
- seule l'empreinte scrypt est écrite ; le mot de passe n'est jamais conservé ;
- fichier créé en **600**, écriture atomique, **doublon d'adresse refusé**,
  fichier déjà accessible à d'autres **refusé**.

Puis, dans l'environnement du service :

```
MONRECOURS_SESSION_SECRET=<64 caractères aléatoires>
MONRECOURS_COMPTES_FICHIER=/etc/mon-recours-ci/comptes.json
MONRECOURS_AUDIT_FICHIER=/var/lib/monrecours/audit.jsonl
MONRECOURS_API_URL=http://127.0.0.1:8765
MONRECOURS_API_KEY=<clé du moteur, 16 caractères minimum>
```

Sans `MONRECOURS_MODE=demo` : c'est cette variable qui ferme l'administration.

Ne définissez **jamais** `MONRECOURS_COMPTES` **et** `MONRECOURS_COMPTES_FICHIER`
en même temps — la configuration est alors refusée comme ambiguë.

## 6. Tester sans créer de compte réel

```bash
cd web
npm run verifier:admin
```

Le script démarre sa propre instance sur un port libre, avec un **compte jetable
tiré au hasard**, un répertoire temporaire, et un moteur volontairement
injoignable. Il supprime tout en sortant. **Rien n'est écrit dans le dépôt.**

Résultat du 22/10/2026 : **16/16 contrôles réussis**.

```
OK  /admin sans cookie renvoie vers la connexion — 307 -> /connexion
OK  mauvais mot de passe refusé — 401
OK  compte inconnu : réponse identique (pas d'énumération)
OK  connexion valide acceptée — 200
OK  cookie HttpOnly
OK  cookie SameSite=Strict
OK  /admin accessible avec le cookie — 200
OK  le tableau de bord dit que le moteur est injoignable
OK  cookie falsifié refusé — 307
OK  déconnexion traitée — 303
OK  cookie effacé à la déconnexion
OK  /admin refermé pour un navigateur déconnecté — 307
OK  journal d'audit écrit — 6 ligne(s)
OK  aucun mot de passe dans le journal
OK  aucune adresse e-mail en clair dans le journal
OK  tentatives limitées (429)
```

## 7. Limites connues, non corrigées

| Limite | Effet | Pourquoi ce n'est pas corrigé |
|---|---|---|
| **Pas de révocation à la déconnexion** | un cookie **copié avant** la déconnexion reste valide jusqu'à l'expiration (2 h) | jeton sans état ; révoquer exige un stockage partagé (incompatible serverless, possible sur VPS) |
| Révocation à la **modification du mot de passe** | immédiate (le jeton porte `f`, empreinte du compte) | déjà en place |
| Pas de second facteur | un mot de passe volé suffit | à décider |
| Pas de gestion des comptes dans l'interface | ajout/suppression par la ligne de commande | volontaire : aucune surface d'attaque supplémentaire |
| Journal d'audit optionnel | sans `MONRECOURS_AUDIT_FICHIER`, seuls les journaux serveur restent | à imposer en production |
| Limitation en mémoire | 5 tentatives/min par adresse et par visiteur, **par instance** | voir `docs/PREPRODUCTION_RESSOURCES.md` |

## 8. Avant une mise en ligne réelle

1. **Héberger le moteur** sur une machine à disque persistant (cf. `docs/PREPRODUCTION_RESSOURCES.md`).
2. **Restreindre l'accès à `/admin`** par liste d'IP dans nginx, tant que le second facteur n'existe pas.
3. **Imposer le journal d'audit** (`MONRECOURS_AUDIT_FICHIER`) et le sauvegarder.
4. **Tester une restauration réelle** des sauvegardes chiffrées.
5. **Relecture juridique** : sans elle, le produit reste techniquement sérieux, pas juridiquement validé.
