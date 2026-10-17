# 01 — Sources officielles : registre et résultats mesurés

## Avertissement sur la portée de ce document

Ce fichier contient un **registre d'URL** et les **résultats d'accessibilité
mesurés**. Il ne contient aucune affirmation sur la validité, la vigueur ou le
contenu des textes publiés par ces sources.

> Une source joignable n'est pas une source qui dit la vérité sur votre
> situation. L'accessibilité se mesure ; la vigueur d'un texte se vérifie, texte
> par texte, dans `core/base.py`.

## Registre (config.SOURCES_OFFICIELLES)

| ID | Nom | URL | Rôle |
|---|---|---|---|
| `SGG` | Secrétariat Général du Gouvernement | https://www.sgg.gouv.ci/ | Journal officiel, documenthèque, textes |
| `JORCI` | Portail des Journaux officiels (ONECI) | https://jorci.oneci.ci/ | Publication des Journaux officiels |
| `CNDJ` | Centre National de Documentation Juridique | https://www.cndj.ci/ | Documentation juridique nationale |
| `CNDJ_TEXTES` | CNDJ — Textes législatifs et réglementaires | `…/bases-de-recherche/textes-legislatifs-et-reglementaires.html` | Base de recherche |
| `CNDJ_CODES` | CNDJ — Codes et recueils de textes | `…/bases-de-recherche/codes-et-recueils-de-textes.html` | Base de recherche |
| `CNDJ_JURIS` | CNDJ — Jurisprudence nationale | `…/bases-de-recherche/jurisprudence-nationale.html` | Base de recherche |
| `CNDJ_COMMUNAUTAIRE` | CNDJ — Droit communautaire | `…/bases-de-recherche/droit-communautaire.html` | UEMOA, OHADA, CEDEAO |
| `CNDJ_BIBLIO` | CNDJ — Bibliothèque numérique | https://biblio.cndj.ci | Bibliothèque (accès possiblement restreint) |

## Résultat mesuré — 2026-10-16T23:51 UTC

Commande : `python3 bin/verifier_sources.py` (requêtes HTTP réelles).

| Source | Statut | HTTP | Détail |
|---|---|---|---|
| SGG | ACCESSIBLE | 200 | page servie |
| **JORCI** | **INDISPONIBLE** | **503** | `HTTPError 503 : Service Unavailable` |
| CNDJ | ACCESSIBLE | 200 | page servie |
| CNDJ_TEXTES | ACCESSIBLE | 200 | base de recherche servie |
| CNDJ_CODES | ACCESSIBLE | 200 | base de recherche servie |
| CNDJ_JURIS | ACCESSIBLE | 200 | base de recherche servie |
| CNDJ_COMMUNAUTAIRE | ACCESSIBLE | 200 | base de recherche servie |
| CNDJ_BIBLIO | ACCESSIBLE | 200 | bibliothèque numérique servie |

**7 accessibles sur 8. JORCI hors service au moment de la mesure.**

Ce 503 n'est pas contourné : il est enregistré dans
`KNOWLEDGE/verifications_sources.json` avec sa date. Tant qu'il dure, aucune
conclusion ne peut s'appuyer sur une publication du Journal officiel non
retrouvée ailleurs. L'agent le dit au lieu de le masquer.

## Ce que la mesure a confirmé sur les sources

- **`biblio.cndj.ci` est une bibliothèque numérique fonctionnelle** (93 Ko de
  page, 2 717 caractères visibles) exposant : Droit national, Textes législatifs
  & réglementaires, Codes et Recueils, Jurisprudence nationale, Autorités
  administratives indépendantes (ARTCI), Droit communautaire (UEMOA, OHADA,
  CEDEAO). C'est le point d'entrée le plus riche pour constituer le corpus.
- **`sgg.gouv.ci`** expose Journal officiel, Documenthèque, Foire aux questions,
  Liens utiles (page de 16,5 Ko, rendu serveur).
- **`jorci.oneci.ci`** répond 503 « Service Unavailable ».

## Ce que ce document ne dit PAS

- Il ne dit pas que tous les textes applicables sont disponibles en ligne.
- Il ne dit pas que les bases du CNDJ sont exhaustives ou à jour.
- Il ne dit pas que JORCI est définitivement hors service (un 503 est
  temporaire par nature).
- Il ne dit rien sur la valeur juridique d'un contenu trouvé sur ces sites.

## Sources ajoutées en phase 2 (corpus documentaire)

Le registre ci-dessus reste le socle. La collecte du corpus a fait apparaître
des **publications officielles librement téléchargeables**, distinctes des
portails de consultation :

| Hôte | Nature | Constat |
|---|---|---|
| `www.dgi.gouv.ci` | republications de lois (`assets/documents/…/lois_reglements/`) | PDF intégraux accessibles ; **répertoire non énumérable** (page XML « ACCES INTERDIT ») |
| `construction.gouv.ci` | publications du Ministère de l'Urbanisme (`uploads/publications/<id>.pdf`) | PDF accessibles ; **pas d'index** (403 sur le dossier) |
| `www.sgg.gouv.ci/photo_doc/<id>.pdf` | documents numérisés du SGG | accessible ; contenu souvent **scanné sans calque texte** |
| `patrimoine.gouv.ci/doc/loi/…` | textes officiels | accessible |

**Obstacles constatés, non contournés :**

- `sgg.gouv.ci/jo.php` — Journal Officiel **derrière un identifiant** ; le site
  rappelle que seule la version originale en ses locaux a valeur probante.
- `biblio.cndj.ci/search/codes/<id>` — **mur de connexion** ; accès payant
  (10 000 FCFA/an étudiant, 10 000 FCFA/mois Express). Les pages de recherche
  publiques restent consultables et exposent des extraits, mais un extrait
  **n'est pas le document** : une référence fondée sur un extrait ne peut pas
  être promue `VERIFIE`.
- `jorci.oneci.ci` — **HTTP 503 « Maintenance en cours »** au 2026-10-16.
- `web.construction.gouv.ci` — **DNS non résolvable** depuis ce poste.

Détail complet des documents collectés, des empreintes et des lacunes :
`04_CORPUS_LOGEMENT_BAUX_FONCIER.md`.


## Vérification d'un hôte avant promotion d'état

`core.sources.est_hote_officiel` n'accepte que les hôtes du registre ou du
domaine `*.gouv.ci`. Conséquence : une URL de blog, de forum ou de réseau social
ne peut pas fonder une promotion `VERIFIE`, même si son contenu est exact. Le
périmètre est une propriété du code, pas une bonne intention.
