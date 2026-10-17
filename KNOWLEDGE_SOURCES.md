# KNOWLEDGE_SOURCES — sources officielles et obstacles constatés

Chaque ligne a été **appelée pour de vrai** pendant la mission. Un obstacle
constaté est écrit tel quel : il n'est pas contourné, il n'est pas maquillé en
succès.

Le registre machine est dans `config.SOURCES_OFFICIELLES` ; l'historique
horodaté dans `KNOWLEDGE/verifications_sources.json`
(`python3 bin/verifier_sources.py`).

---

## 1. La règle du périmètre officiel

`core.sources.est_hote_officiel(url)` accepte **deux** choses, et rien d'autre :

1. un domaine `*.gouv.ci` (ou `gouv.ci`) ;
2. un hôte figurant au **registre** `SOURCES_OFFICIELLES`.

Un site de cabinet, un blog, un agrégateur commercial n'y entrent **jamais**,
même s'ils publient le bon texte. C'est cette fonction qui garde la promotion
`VERIFIE` : sans elle, n'importe quelle page web deviendrait une « preuve ».

`TestStatutsDeDomaine` refuse qu'une institution soit déclarée officielle sans
figurer au registre : la porte d'entrée reste explicite et révisable.

### Institutions officielles hors `*.gouv.ci` (vérifiées accessibles)

| Hôte | Institution | Justification |
|---|---|---|
| `oneci.ci` | Office National de l'État Civil et de l'Identification | publie les textes d'état civil |
| `mffe.ci` | Ministère de la Famille, de la Femme et de l'Enfant | publie les textes famille/enfance |
| `autoritedeprotection.ci` | Autorité de protection des données personnelles | publie la loi 2013-450 |
| `artci.ci` | Autorité de Régulation des Télécommunications/TIC | régulation du numérique |
| `ohada.org` | OHADA | organisation supranationale compétente (droit des affaires) |
| `courconstitutionnelle.ci` | Conseil constitutionnel | textes et décisions constitutionnels |

## 2. État mesuré des sources

| Source | Résultat | Usage réel |
|---|---|---|
| `sgg.gouv.ci` | **HTTP 200** | portail ; `photo_doc/<id>.pdf` sert des textes |
| `sgg.gouv.ci/jo.php` | **mur d'authentification** | Journal officiel non consultable |
| `jorci.oneci.ci` | **HTTP 503** (« maintenance ») | aucun Journal officiel |
| `cndj.ci` + 4 bases de recherche | **HTTP 200** | recherche ; les pages de codes redirigent |
| `biblio.cndj.ci` | accessible, **accès payant** (10 000 FCFA/an ou /mois) | respecté, non contourné |
| `dgi.gouv.ci` (`lois_reglements/`) | **page XML « ACCES INTERDIT »** | dossiers non énumérables ; téléchargement direct par URL possible |
| `construction.gouv.ci` | **HTTP 200** | 3 textes collectés |
| `famille.gouv.ci` | **HTTP 200** | **15 textes famille collectés** |
| `communication.gouv.ci` | **HTTP 200** | communiqué du Conseil des ministres (contexte) |
| `telecom.gouv.ci` | **HTTP 200** | 2 PDF (scans, à lire par OCR) |
| `justice.gouv.ci` | HTTP 200 | publications sans lien de texte exposé |
| `interieur.gouv.ci` | HTTP 200 | décrets de nomination, statistiques |
| `sante.gouv.ci` | HTTP 200 | décrets d'organisation administrative |
| `transports.gouv.ci` | HTTP 200 | pages d'information, pas de texte |
| `fonctionpublique.gouv.ci` | HTTP 200 | pages HTML, pas de PDF de texte |
| `commerce.gouv.ci` | HTTP 200 | publications sans lien de texte exposé |
| `travail.gouv.ci` | **HTTP 000** (DNS) | injoignable |
| `web.construction.gouv.ci` | **DNS non résolvable** | injoignable |
| `ohada.org` | HTTP 200 | page des actes uniformes : **liens PDF non exposés** dans le HTML servi |
| `civlii.laws.africa` | 404 sur les actes 2025, 403 sur `/search/` | aucune fiche utile |

## 3. Textes cherchés et NON obtenus sur un domaine officiel

| Texte | Domaine | Où il a été trouvé | Décision |
|---|---|---|---|
| Code du travail (loi 2015-532) | C — travail | nulle part sur un domaine officiel | **non intégré** |
| Code pénal (loi 2019-574) | G — pénal | seulement cabinets / agrégateurs | **non intégré** |
| Code de procédure pénale (loi 2018-975) | G — pénal | `droitci.info` (privé) | **non intégré** |
| Loi 2016-412 (consommation) | E — dettes | FAO (dépôt international) | **non intégré** |
| Loi 60-315 (associations) | H — associations | seulement agrégateurs | **non intégré** |
| Loi 2013-450 (données personnelles) | I — numérique | `telecom.gouv.ci` (**scans**, OCR en cours) + `autoritedeprotection.ci` | en cours |
| Loi 2025-221 (contentieux des baux) | A — logement | aucun exemplaire officiel | **non intégrée**, journal dans `KNOWLEDGE/05_LACUNE_LOI_2025_221.md` |
| Actes uniformes OHADA | D — entreprises | `ohada.org` (liens PDF non exposés) | **non intégrés** |

**Une référence trouvée en ligne ne devient jamais un texte vérifié sans
consultation du document officiel correspondant.** C'est la règle qui explique
cette colonne « non intégré ».

## 4. Pièges de collecte (mesurés, pas supposés)

1. **Chercher les publications ministérielles, pas seulement les portails.** Les
   textes intégraux libres sont sur
   `construction.gouv.ci/uploads/publications/<id>.pdf`,
   `famille.gouv.ci/uploads/publications/<id>.pdf`,
   `dgi.gouv.ci/assets/documents/…/lois_reglements/`,
   `sgg.gouv.ci/photo_doc/<id>.pdf`,
   `telecom.gouv.ci/new/uploads/publications/<id>.pdf`.
2. **Ces dossiers ne sont pas indexables** (403, ou page XML « ACCES INTERDIT »).
   Passer par une recherche web restreinte au domaine, puis vérifier chaque URL
   par une requête réelle.
3. **Une page de publications n'expose pas toujours ses PDF** : `interieur`,
   `sante`, `transports`, `justice`, `commerce` renvoient du HTML sans liens de
   texte. Ne pas en conclure que les textes n'existent pas — conclure que
   **l'accès n'est pas établi**.
4. **Un PDF publié par une autorité peut être une reproduction d'un éditeur
   tiers.** Vérifié : un texte famille était une copie **Laws.Africa (CC BY 4.0)**
   avec les pieds de page de l'éditeur tombant dans le corps des articles.
   Détection automatique : `core.corpus.textes_contaminants`.
