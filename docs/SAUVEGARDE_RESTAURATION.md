# Sauvegarde, restauration et conservation

Ce document décrit ce qui est **prêt**, ce qui a été **testé**, et ce qui reste
**à décider**. Rien ici n'est installé : aucune sauvegarde planifiée, aucune purge
en production.

## 1. Ce qu'il faut sauvegarder, et pourquoi

| Contenu | Sensibilité | Perte si absent |
|---|---|---|
`DOSSIERS/` — récits, courriers, traces de dossier | **très élevée** (données personnelles) | un utilisateur perd son dossier et son courrier, sans recours |
`KNOWLEDGE/corpus_juridique.sqlite3` | moyenne (textes publics, mais coûteux à reconstruire) | le service ne peut plus citer aucun texte |
`KNOWLEDGE/catalogue.json`, fiches | moyenne | les réponses perdent leur structure |

Le corpus est reconstructible par `bin/reconstruire_base.py` ; **les récits ne le
sont pas**. C'est ce qui rend la sauvegarde de `DOSSIERS/` prioritaire.

## 2. Conception

```
DOSSIERS/ ─┐
           ├─► copie dans un répertoire temporaire (700) ─► tar.gz ─► AES-256-CBC ─► .enc (600)
base ──────┘        (instantané SQLite cohérent)                    + HMAC-SHA256
```

* **La base est copiée par l'API `sqlite3.backup()`**, pas par un `cp` : la copie
  est cohérente même si le moteur écrit au même moment.
* **Chiffrement avant toute sortie** : rien de lisible ne quitte le répertoire
  temporaire. La vérification est faite sur l'archive produite (aucune chaîne du
  contenu n'y apparaît).
* **Encrypt-then-MAC** : AES-256-CBC puis HMAC-SHA256 sur `IV ‖ chiffré`. Une
  mauvaise clé ou une altération échoue **toujours** — le padding CBC, lui,
  laisserait passer environ 1 cas sur 256.
* **Deux clés dérivées** d'une clé maître par HMAC avec des étiquettes
  distinctes (`…/enc/v1`, `…/mac/v1`) : une seule clé à conserver.
* **Noms d'archives neutres** : `sauvegarde-<AAAAMMJJ-HHMMSS>-<8 hex>.enc`.
  Aucun identifiant de dossier, aucun nom de personne.
* **En-tête séparé** (`.json`, 600) : version, date, IV, MAC, taille, empreinte,
  **nombre** de fichiers. Aucun chemin, aucun identifiant, aucun contenu.
* **Manifeste chiffré** (à l'intérieur de l'archive) : chemin relatif, SHA-256 et
  taille de chaque fichier — c'est lui qui permet de prouver la fidélité.

### La clé

* 32 octets en hexadécimal (64 caractères) : `openssl rand -hex 32 > fichier`.
* **Hors du dépôt, hors de l'archive, hors du serveur sauvegardé.**
  `/etc/mon-recours-ci/cle-sauvegarde`, propriétaire `monrecours`, mode `600`.
* Perte de la clé = archives définitivement illisibles. Conserver une copie dans
  un coffre séparé (gestionnaire de secrets ou enveloppe scellée).
* Clé absente, vide, non hexadécimale ou de mauvaise longueur : la commande
  **échoue** (code 2) et ne produit rien.

## 3. Utilisation

```bash
# clé (une fois)
openssl rand -hex 32 > /etc/mon-recours-ci/cle-sauvegarde
chmod 600 /etc/mon-recours-ci/cle-sauvegarde

# sauvegarde
python3 bin/sauvegarde.py sauvegarder \
  --dossiers DOSSIERS --base KNOWLEDGE/corpus_juridique.sqlite3 \
  --sortie /srv/sauvegardes --cle /etc/mon-recours-ci/cle-sauvegarde

# contrôle sans restaurer
python3 bin/sauvegarde.py verifier --archive /srv/sauvegardes/sauvegarde-….enc --cle …

# restauration dans un répertoire NEUF
python3 bin/sauvegarde.py restaurer --archive /srv/sauvegardes/sauvegarde-….enc \
  --sortie /srv/restauration/DOSSIERS \
  --base-destination /srv/restauration/corpus.sqlite3 --cle …
```

Codes de sortie : `0` succès · `2` usage ou clé · `3` archive invalide ou clé
incorrecte · `4` échec de chiffrement · `5` destination non vide (`--ecraser`
requis) · `6` `openssl` absent.

## 4. Ce qui a été testé (données synthétiques uniquement)

| Étape | Résultat observé |
|---|---|
Archive produite | 4 fichiers, 1 616 octets chiffrés, `.enc` et `.json` en **600** |
Opacité | marqueur secret et nom de répertoire **absents** de l'archive |
En-tête | aucun chemin, aucun identifiant, aucun contenu |
Restauration | 3 fichiers aux empreintes **identiques**, PDF relu (1 page, texte intact) |
Base | **logiquement identique** (schéma + lignes + `integrity_check ok`) — pas octet pour octet, c'est le comportement de `sqlite3.backup` |
Permissions restaurées | répertoires **700**, fichiers **600** |
Mauvaise clé | refus, code 3, **aucun répertoire créé** |
Archive altérée (1 octet) | refus, code 3, empreinte divergente nommée |
Clé absente | refus, code 2 |
Destination non vide | refus, code 5 |
Originaux | empreintes **inchangées** après le cycle complet |

## 5. Conservation des consultations — 90 jours

**Hypothèse de conception, à faire valider juridiquement.** La durée n'est ni
annoncée aux utilisateurs ni appliquée nulle part pour l'instant.

| Règle | Valeur |
|---|---|
Durée | **90 jours** |
Départ du délai | **dernière modification** du dossier (`mtime`) — la date la plus récente observable ; elle ne peut que conserver plus longtemps, jamais moins |
Éligibilité | `mtime` de **plus de** 90 jours ; un dossier à exactement 90 jours est conservé |
Périmètre | uniquement les dossiers `web-<uuid v4>` ; tests, démonstrations et CLI jamais touchés |
Défaut | **simulation** ; suppression seulement avec `--confirmer` |
Journal | `KNOWLEDGE/qualite/purge.jsonl` — date, mode, durée, **compteurs**. Aucun identifiant, aucun récit, aucun nom |
Confinement | `realpath` doit rester sous `DOSSIERS/` ; liens symboliques ignorés |
Erreurs | un échec de suppression n'interrompt pas les autres ; code de sortie 1 |

### Cas limites vérifiés

| Cas | Attendu | Observé |
|---|---|---|
89 jours | conservé | conservé |
90 jours + 1 h | éligible | supprimé |
91 jours | éligible | supprimé |
`CLI_DEMO` vieux de 400 jours | conservé (hors motif) | conservé |
lien symbolique `web-…` | ignoré | ignoré |
simulation sans `--confirmer` | rien supprimé | rien supprimé |

### Sauvegardes et purge : deux durées distinctes

Purger un dossier de `DOSSIERS/` **ne purge pas** les archives : un récit peut
survivre jusqu'à 90 jours dans une sauvegarde, plus la durée de vie des archives.
Deux choix possibles, à trancher :

1. **Durée de vie des archives ≥ celle des consultations** (simple) : les
   données personnelles survivent plus longtemps dans les sauvegardes — il faut
   alors l'annoncer.
2. **Archives à durée courte** (30 jours, par exemple) : la restauration ne
   couvre plus qu'un mois d'historique.

Tant que ce choix n'est pas fait, ne pas présenter la purge comme une garantie
d'effacement complet.

## 6. Installation contrôlée (non effectuée)

1. Créer la clé (voir §3), propriétaire `monrecours`, mode `600`, **hors du
   serveur** sauvegardé si possible.
2. Planifier `bin/sauvegarde.py sauvegarder` (timer systemd ou cron), sortie sur
   un volume distinct du serveur.
3. **Tester une restauration** sur un répertoire et une base de test — une
   sauvegarde jamais restaurée n'est pas une sauvegarde.
4. Ajouter un contrôle d'âge : alerter si aucune archive de moins de 24 h.
5. Installer le couple `monrecours-purge.service` + `monrecours-purge.timer`
   (le timer seul ne déclenche rien).
6. Fixer la durée de vie des archives et l'écrire dans la page « comprendre ».

## 7. Ce qui reste non vérifié

* Sauvegarde d'un volume **réel** de 133 dossiers (seul un jeu synthétique a été
  mesuré) : la durée et la taille restent à observer.
* Restauration sur une **autre machine** (le test a eu lieu sur la même).
* Comportement si le disque est plein pendant la sauvegarde.
* Rotation et purge des archives (aucune décidée).
* Chiffrement au repos du volume de destination (hors périmètre de l'outil).
