# Conditions de mise en préproduction

Ce document liste ce qui est **vérifié**, ce qui **reste à faire**, et ce qui
**bloque** avant d'exposer Mon Recours CI derrière HTTPS. Il ne remplace pas
`web/deploiement/README.md` (procédure d'installation) : il en donne les
conditions de sécurité.

## 1. Architecture imposée

```
Internet ──HTTPS──► nginx (443) ──► Next.js (127.0.0.1:3000) ──► moteur (127.0.0.1:8765)
                    TLS, HSTS,        cookie signé,               clé d'API,
                    débit, taille     limite par visiteur         débit global
```

Le moteur **n'écoute que sur `127.0.0.1`** et ne sait pas faire de TLS : il n'est
jamais exposé directement. C'est pourquoi un hébergement serverless (Vercel) ne
convient pas — il ne peut pas joindre le moteur sans l'exposer.

## 2. Vérifié aujourd'hui

| Point | État | Preuve |
|---|---|---|
| Dossiers de consultation privés | **corrigé** — 700 / 600 | `bin/restreindre_permissions.py`, 278 entrées, test d'ensemble |
| Secrets absents du bundle navigateur | **oui** | `verifier:secrets` — 26 fichiers, 0 secret |
| Aucun secret dans les fichiers suivis | **oui** | recherche `sk-`, `Bearer`, clés privées |
| Journal du moteur sans contenu utilisateur | **oui** | horodatage, route, statut, durée, **empreinte** du dossier |
| Journal de l'interface sans contenu | **oui** | `{horodatage, evenement, route, statut, code}` |
| Cookie de session | **oui** | HttpOnly, SameSite=Strict, path `/api`, HMAC + temps constant |
| Téléchargement PDF confiné | **oui** | cookie signé, motif verrouillé, `realpath`, 8 tests |
| Clé d'API obligatoire | **oui** | 401 sans clé, `hmac.compare_digest` |
| Débit limité | **oui** | interface (par visiteur) + moteur (global) |
| Corps borné | **oui** | 64 Ko moteur, type `application/json` exigé (415) |
| En-têtes navigateur | **oui** | CSP, `nosniff`, `DENY`, `no-referrer` |
| Fournisseur LLM | **désactivé** | `operationnel=False`, aucune clé |
| Purge des consultations | **outil prêt** | `web/scripts/purger-consultations.mjs` (simulation par défaut) |
| Sauvegarde de la base | **outil prêt** | `bin/reconstruire_base.py` → `KNOWLEDGE/.sauvegardes/` |

## 3. À faire avant d'ouvrir au public

1. **TLS** : certificat (Let's Encrypt), redirection 80→443, HSTS après validation,
   suites TLS modernes. Sans TLS, la clé d'API et les récits circulent en clair.
2. **Sauvegarde des dossiers** : `DOSSIERS/` contient des récits personnels. Une
   sauvegarde doit être **chiffrée au repos** et soumise à la même durée de
   conservation que les dossiers (sinon la purge ne sert à rien).
3. **Durée de conservation écrite** : choisir un nombre de jours, le documenter
   dans la page « comprendre », et planifier `purger-consultations.mjs`.
4. **Journalisation exploitée** : les journaux ne contiennent pas de données
   personnelles — il faut encore les **conserver et les surveiller** (rotation,
   alerte sur 5xx et sur 429 anormaux).
5. **Sauvegarde/restauration testée** : une restauration non essayée n'est pas une
   sauvegarde. À faire sur une base de test.
6. **Revue de l'hébergeur** : localisation des données, sous-traitance, accès
   administrateur — décision du responsable du projet, pas technique.

## 4. Bloquants juridiques (aucun n'est technique)

* **17 domaines sur 24 sans texte** : le service répond correctement mais s'abstient
  sur la majorité des sujets.
* **0 validation humaine** : `VERIFIE_MANUELLEMENT = 0`. Aucune fiche n'a été relue
  par un juriste ivoirien.
* **Code du travail non intégré** : bornes démontrées (p. 7 → 183 d'un recueil),
  mais l'hôte n'est pas au périmètre officiel — décision requise.
* **Aucune veille d'abrogation** : la vigueur n'est établie qu'à la date de
  consultation.

## 5. Décisions qui ne m'appartiennent pas

1. Accepter (ou non) `economie-ivoirienne.ci` comme source de provenance.
2. Autoriser le `git push` (la CI n'a jamais tourné).
3. Choisir l'hébergeur, le domaine, la durée de conservation.
4. Lancer une relecture juridique humaine.

Tant que ces quatre points ne sont pas tranchés, le produit est **prêt pour une
décision de préproduction**, pas pour une mise en ligne.
