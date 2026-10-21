# CLAUDE_HANDOFF — état technique réel et reprise du développement

Document destiné à la personne (ou à l'agent) qui reprendra ce projet pour
construire l'application. Il décrit **ce qui existe**, ce qui est simulé, ce qui
est bloqué — et il ne promet rien.

Généré à partir du code et des mesures du projet, pas d'une intention.

---

## 1. Audit d'interface — résultat

**Il n'existe aucune interface.** Vérifié : aucun serveur HTTP, aucune route,
aucune page, aucun gabarit, aucun module d'API, aucun fichier front. Le seul
module réseau du cœur est `core/sources.py` (vérification des sources
officielles) ; les collecteurs `bin/*` touchent le réseau pour télécharger des
PDF.

Aucune application n'est « déjà construite » : tout ce qui suit est une
**spécification d'intégration**, pas un état livré.

## 2. Ce qu'il faut installer

```bash
# Runtime de l'agent : Python 3.9+ et la bibliothèque standard, plus fpdf2 pour
# l'export PDF (requirements.txt). Rien d'autre.
cd /Users/mac/mon_recours_ci
python3 -m pip install -r requirements.txt   # fpdf2 — sans lui, pas de PDF
python3 tests/run_all.py                  # 553 tests (552 OK, 1 ignoré), doit finir par exit 0
python3 bin/verifier_sources.py           # requêtes HTTP réelles sur les sources

# Collecte uniquement (n'affecte pas le runtime)
python3 -m venv .venv-corpus
./.venv-corpus/bin/pip install pypdf      # extraction de texte PDF
./.venv-corpus/bin/python bin/collecter_domaine.py --domaine famille_mariage_filiation
python3 bin/ocr_collecter.py              # OCR macOS : swiftc + macOS 13+
```

| Dépendance | Requis pour | Absence |
|---|---|---|
| stdlib Python (`sqlite3`, `urllib`, `json`, `difflib`, `unittest`) | l'agent entier | — |
| `pypdf` (venv séparé) | extraction du texte des PDF | les textes extraits sont conservés à côté des PDF, donc le runtime fonctionne sans |
| `swiftc` + macOS Vision/PDFKit | lecture des scans | `bin/ocr_collecter.py` se déclare indisponible, il ne fait pas semblant |
| `fpdf2==2.8.4` (`requirements.txt`) | export PDF des courriers | pas de PDF : `pdf.ok = false` avec sa raison, aucun lien de téléchargement |

**Variables de configuration attendues** : aucune clé d'API, aucun secret. Le
projet n'appelle aucun service payant. `config.CHEMIN_DB` et
`config.SOURCES_OFFICIELLES` sont les seuls points d'entrée à adapter.

## 3. Contrats d'entrée / sortie

### `MonRecoursCI().ouvrir_dossier(dossier_id, demande, elements_connus=())`

| Entrée | Type | Note |
|---|---|---|
| `dossier_id` | `str` | refusé s'il contient `/`, `\`, `..` ou `\x00` |
| `demande` | `str` | langage courant, fautes acceptées |
| `elements_connus` | `tuple[str]` | ce que l'utilisateur a déjà fourni |

Retourne : `dossier_id`, `ouvert_le`, `agent`, `demande`, `statut`
(`EN_COURS` \| `REFUS`), `garde_fous`, `qualification`
({`domaines_probables`, `scores_domaines`, `nature_demande`, `urgence`,
`ambiguite_domaine`}), `urgence` ({`niveau`, `declencheurs`}), `faits`,
`questions_a_poser`, `references_candidates`, `verrous_humains`, `note_corpus`.

### `MonRecoursCI().clore_dossier(dossier_id, analyse, brouillons=(), validations_humaines=(), plan=None, sources_testees=None)`

Retourne : `dossier_id`, `statut_reponse` (`ANALYSE_CONFORME` \|
`CONCLUSION_IMPOSSIBLE` \| `ANALYSE_REFUSEE` \| `REFUS`), `analyse`, `plan`,
`brouillons`, `avertissement`, `traceabilite` (chemin du JSON),
`controles_qualite` ({`violations`, `analyse_conforme`,
`raisons_absence_de_conclusion`, `raisons_verrous_ouverts`,
`references_utilisees`, `references_inconnues`, `actions_externes_autorisees`,
`aucune_fonction_d_envoi`, `garde_fous_demande`}).

Lève `ValueError` si le dossier n'a jamais été ouvert, ou si l'analyse n'est pas
conforme (`core.analyse.exiger_conformite`).

### `MonRecoursCI().etat()`

`agent`, `version`, `pays`, `corpus`, `sources`, `dossiers`, `capacites`
(capacités **et** limites).

### Contrat d'analyse (`core.analyse`)

Construite par l'appelant, validée par le cœur :

```python
analyse = A.nouvelle_analyse(dossier_id, ["logement_baux_foncier"])
A.ajouter_regle(analyse, ref_id, "énoncé", articles="Article 416",
                citation="« extrait exact du texte indexé »")
A.ajouter_application(analyse, "application aux faits", ref_ids=[ref_id], faits_ids=["F01"])
A.ajouter_hypothese(analyse, "énoncé", pour_conclure="condition")
A.declarer_incertitude(analyse, ref_id, "raison")
```

`A.valider(analyse, references, faits_texte)` → liste de violations
(`REGLE_SANS_SOURCE`, `REF_INCONNUE`, `REF_VIDE`, `APPLICATION_SANS_REGLE`,
`APPLICATION_SANS_FAIT`, `HYPOTHESE_SANS_CONDITION`, `CITATION_NON_VERIFIABLE`,
`INCERTITUDE_NON_DECLAREE`, `NOMBRE_NON_SOUTENU`, `DOMAINE_INDETERMINE`,
`PROVENANCE_OCR_NON_DECLAREE`).

**Un format de citation doit toujours transporter** : `ref_id`, `numero`
d'article, le texte exact indexé, `sha256_article`, `origine_texte`
(`CALQUE_TEXTE` \| `OCR_AUTO`), et l'état de vérification de la référence.

## 4. Modèle de données (`KNOWLEDGE/corpus_juridique.sqlite3`)

| Table | Rôle | Contraintes notables |
|---|---|---|
| `references_juridiques` | le texte de loi | métadonnées obligatoires non NULL ; `etat_verification` par défaut `NON_VERIFIE` |
| `verifications` | journal des changements d'état | conserve `etat_precedent` et le motif : aucune transition silencieuse |
| `documents` | l'exemplaire téléchargé | `sha256` obligatoire ; `calque_texte=1` exige `fichier_texte` ; URL d'un hôte officiel |
| `articles_corpus` | l'article indexé | clés étrangères vers `documents` **et** `references` ; `sha256_article` ; `origine_texte` ∈ {`CALQUE_TEXTE`, `OCR_AUTO`, `VERIFIE_MANUELLEMENT`} |

Toute écriture passe par `core.base` et `core.corpus` : les contraintes sont dans
le schéma, pas dans une convention.

## 5. Formats de provenance à exposer dans l'interface

Toute réponse affichée à un utilisateur doit pouvoir montrer :

```
Titre officiel · type et numéro · date de publication · domaine
Article N — « extrait exact »
Source : URL · empreinte SHA-256 · page · date de consultation
Lecture : CALQUE_TEXTE | OCR_AUTO (confiance x,xx, recoupé oui/non)
État : VERIFIE | PARTIELLEMENT_VERIFIE | NON_VERIFIE
Limites : texte de vigueur non garantie après le … · mesure temporaire · …
```

## 6. Fournisseur de langage : état réel et stratégie

**Il n'y a aucun fournisseur de langage, et aucun `mock` non plus.** Le cœur est
100 % déterministe. Le « raisonnement » vient de l'appelant.

Stratégie recommandée pour la suite, dans cet ordre :

1. **Conserver le cœur déterministe comme autorité.** Une couche LLM propose une
   analyse ; `core.analyse.valider` la refuse si elle n'est pas traçable. Le
   modèle ne doit jamais pouvoir écrire directement une affirmation juridique.
2. **Brancher le LLM en amont uniquement** : extraire les faits, choisir les
   domaines, proposer des articles candidats. Puis laisser le cœur vérifier.
3. **Ne jamais donner au modèle le droit d'inventer un `ref_id`** : il doit
   choisir dans les résultats de `chercher_articles`.
4. **Tester avec le corpus réel**, pas avec des exemples inventés : les attendus
   des tests doivent venir d'articles présents en base.

`SYSTEM_PROMPT.md` décrit le comportement attendu de cette couche. Il n'est
**pas** chargé aujourd'hui.

## 6 bis. Couche conversationnelle — construite et testée (déterministe)

```
core/catalogue.py    fiches : question courante -> article réel + citation verbatim
core/conversation.py machine à états : qualifier -> questions -> analyse -> restitution
core/service.py      API de service (entrées/sorties typées, erreurs, aucune exception)
bin/dialogue.py      CLI de recette
```

**Aucun modèle de langage n'intervient.** Une fiche ne contient pas de droit : elle
pointe vers un article du corpus et reprend son texte **mot pour mot**. Chaque fiche
est **revalidée au chargement** (référence existante, article citable, citation
littéralement présente, énoncé non dépassant la source) ; une fiche fausse fait lever
`CatalogueInvalide` — elle ne peut pas être servie.

* Catalogue actuel : **92 fiches** sur 5 domaines (famille 31, contrats/OHADA 26,
  pénal 24, logement 10, transport 1). Toutes pointent vers un article réellement
  indexé ; aucune n'est juridiquement validée par un humain.
* Une question **sans fiche** reçoit `CONCLUSION_IMPOSSIBLE` et la liste de ce que le
  catalogue sait traiter — jamais un article au hasard.
* Les réponses de l'utilisateur sont **persistées** dans le dossier en cours, donc
  présentes dans `DOSSIER_TRACABILITE.json`.

### Contrat d'API (`core/service.py`)

```python
service.ouvrir(dossier_id, demande)      -> {"ok": True, "data": {...}}
service.repondre(dossier_id, reponses)   -> {"ok": True, "data": {...}}
service.sante()                          -> catalogue, corpus, domaines
```

Retour d'erreur, toujours de la même forme : `{"ok": False, "erreur": {"code",
"message", "libelle", "detail"}}` avec `code` ∈ {`ENTREE_INVALIDE`,
`DOSSIER_INVALIDE`, `DOSSIER_INCONNU`, `CATALOGUE_INVALIDE`, `INTERNE`}.
`service.SCHEMAS` publie les formes d'entrée/sortie. **Aucune exception ne sort du
service.** Le transport HTTP est fourni par `bin/serveur_api.py` (section 6 ter), qui
n'ajoute aucune logique juridique.

## 6 ter. Serveur HTTP local — construit et testé, NON exposé

`bin/serveur_api.py` (stdlib `http.server`) enveloppe `core/service.py` **sans aucune
logique juridique**. Trois routes : `GET /sante`, `POST /ouvrir`, `POST /repondre`.

| Garde-fou | Mise en œuvre | Test |
|---|---|---|
| Clé obligatoire | `MONRECOURS_API_KEY`, refus de démarrer si absente ou < 16 car. | `test_aucune_cle_par_defaut_dans_le_code`, `test_cle_trop_courte_refusee` |
| Comparaison sûre | `hmac.compare_digest` | `test_mauvaise_cle` |
| Écoute locale | hôte forcé `127.0.0.1` ; `0.0.0.0` lève | `test_ecoute_publique_refusee` |
| Débit | fenêtre glissante 30 req/60 s, `429` + `Retry-After` | `test_depassement_puis_retry_after` |
| Taille | corps ≤ 64 Ko, `413` | `test_corps_trop_volumineux` |
| Entrées | JSON invalide `400`, champ manquant `400`, service en erreur `422` | 3 tests |
| Journal | méthode, route, statut, durée, **empreinte SHA-256 tronquée** du dossier ; jamais la demande | `test_le_journal_ne_contient_ni_identifiant_ni_demande` |
| Isolation | un état par dossier, aucun partage | `test_deux_dossiers_par_http` |

**Ce qui reste absent** : TLS, authentification multi-utilisateurs, quotas persistants,
protection anti-DDoS. Le serveur n'est **pas** exposé sur Internet et ne doit pas l'être
en l'état.

## 6 quater. Interface fournisseur de langage — écrite, NON opérationnelle

```
core/llm.py              contrat + contrôles + repli déterministe (AUCUN import réseau)
bin/fournisseur_http.py  adaptateur de transport (urllib), chargé paresseusement
```

**Le réseau reste hors du cœur** : le garde-fou « seul `core/sources.py` atteint le
réseau » est maintenu, et deux tests le vérifient (`test_le_coeur_ne_contient_aucun_client_reseau`,
`test_l_adaptateur_reseau_est_en_bordure`).

Règle : **un LLM ne produit que des propositions**. `llm.valider_propositions()` repasse
chaque proposition par `corpus.verifier_citation_article` et
`corpus.verifier_enonce_contre_article`. Un article inventé ou une citation modifiée est
**rejeté et conservé dans les rejets**. Testé avec un fournisseur bavard qui tente
d'injecter `REF-BIDON` → 0 acceptation de cette entrée.

Repli : fournisseur absent, en erreur, en délai dépassé ou n'ayant rien fait accepter →
`mode = "deterministe"`, le service répond exactement comme aujourd'hui.

**État réel : `llm.statut()["operationnel"] == False`.** Aucune clé dans le code, aucun
appel réseau effectué, aucune dépense engagée. Ne pas déclarer le mode LLM actif.

## 6 quinquies. Variables d'environnement, exemples, limites

### Variables attendues (aucune valeur secrète dans le dépôt)

| Variable | Rôle | Obligatoire |
|---|---|---|
| `MONRECOURS_API_KEY` | clé d'accès au serveur local (≥ 16 car.) | oui pour `bin/serveur_api.py` |
| `MONRECOURS_LLM_URL` | URL du fournisseur de langage | non |
| `MONRECOURS_LLM_API_KEY` | clé du fournisseur | non |
| `MONRECOURS_LLM_FOURNISSEUR` | `desactive` (défaut) ou `http` | non |

Sans `MONRECOURS_API_KEY`, le serveur **refuse de démarrer**. Sans fournisseur, le mode
déterministe s'applique — c'est l'état actuel.

### Exemple de requête et de réponse réels

```bash
curl -s -X POST http://127.0.0.1:8765/ouvrir \
  -H "X-API-Key: $MONRECOURS_API_KEY" -H "Content-Type: application/json" \
  -d '{"dossier_id":"D1","demande":"Mon bailleur garde ma caution de deux mois."}'
```

```json
{"ok": true, "data": {"etape": "clarification",
  "fiches_identifiees": [{"titre": "Dépôt de garantie (caution)", "article": "416",
                          "numero_texte": "2019-576", "etat_verification": "VERIFIE"}],
  "questions": [{"cle": "logement", "question": "..."}], "urgence": {...},
  "verrous_humains": []}}
```

```bash
curl -s -X POST http://127.0.0.1:8765/repondre \
  -H "X-API-Key: $MONRECOURS_API_KEY" -H "Content-Type: application/json" \
  -d '{"dossier_id":"D1","reponses":{"logement":"oui"}}'
```

La réponse contient `statut_reponse` (`ANALYSE_CONFORME` | `CONCLUSION_IMPOSSIBLE` |
`ANALYSE_REFUSEE` | `REFUS`), six sections (`1_faits` … `6_sources`), `verrous_humains`,
`traceabilite` et `brouillon`. Chaque source porte `sha256_article`, `url_source`,
`etat_verification`, `origine_texte`, `recoupe`.

Codes HTTP : `200` succès, `400` corps invalide, `401` non authentifié, `404` route
inconnue, `405` méthode, `415` Content-Type, `422` refus du service, `429` débit,
`413` corps trop grand.

### Limites de sécurité avant toute exposition publique

**Non fait, et indispensable :** TLS, gestion d'utilisateurs (une clé partagée ne suffit
pas), quotas persistants et distribués, journalisation centralisée avec rétention,
protection anti-DDoS, audit de code externe, revue RGPD/données personnelles, chiffrement
au repos des dossiers. **Le serveur local n'est pas prêt pour la production.**

### Recommandations pour construire l'interface web

1. Consommer **uniquement** `core/service.py` (ou `bin/serveur_api.py`) — ne jamais
   réimplémenter la recherche ou la citation côté client.
2. Afficher `statut_reponse` **tel quel** : ne pas transformer
   `CONCLUSION_IMPOSSIBLE` en réponse affirmative.
3. Toujours afficher `etat_verification` et `origine_texte` à côté de chaque citation ;
   marquer visiblement `OCR_AUTO` non recoupé.
4. Afficher `verrous_humains` en encadré, non masquable.
5. Ne jamais présenter l'outil comme un avocat ; reprendre l'avertissement de
   `SYSTEM_PROMPT.md`.
6. Un dossier = un identifiant opaque ; ne pas exposer les chemins de fichiers.
7. Ne pas ajouter d'endpoint HTTP : le contrat est `ouvrir`, `repondre`, `sante`,
   `supprimer` et — depuis la mission Document/RAG — `rechercher` (localisation
   seule, sans conclusion).

## 6 quinquies bis. Recherche documentaire — exposée, mesurée, bornée

`core/service.rechercher(question, domaine=None, texte=None, limite=5)`

**Ajout** au contrat : aucune des quatre opérations existantes n'est modifiée
(`ouvrir`, `repondre`, `supprimer`, `sante` inchangées, test dédié).

```
{"ok": true, "data": {
    "question": str, "domaine": str|null, "texte": str|null,
    "resultats": [{ref_id, numero_texte, numero, domaine, titre, etat_verification,
                   origine_texte, exemplaires, score, termes_reconnus, extrait}],
    "abstention": bool, "message": str|null, "avertissement": str}}
```

### Ce qu'elle garantit

* un article `articles_fiables = 0` **ne remonte jamais** (filtre déjà présent dans
  `corpus.chercher_articles`, vérifié par `test_un_article_neutralise_ne_remonte_jamais`) ;
* `domaine` inconnu → `ENTREE_INVALIDE` **avec la liste réelle** des 12 clés ;
* `limite` hors `1..25` → `ENTREE_INVALIDE` (y compris `True`, `"5"`, `2.5`) ;
* **aucune écriture** : ni base, ni dossier, ni fiche (empreinte logique avant/après) ;
* **aucune conclusion** : la sortie ne contient ni `sections`, ni `statut_reponse`,
  ni brouillon ; un `avertissement` le dit à chaque appel.

### Ce qu'elle ne fait pas, et pourquoi

* **pas d'endpoint HTTP.** Aucun client n'existe ; exposer une route maintenant
  ajouterait authentification, débit et journalisation sans usage. La fonction de
  service suffit et se branche plus tard sans réécriture.
* **pas de recherche vectorielle.** Non nécessaire pour ce qui est mesuré ici.
* **pas de fiches automatiques.** Les 549 articles « sans fiche » ne justifient pas
  549 fiches : la plupart sont déjà retrouvables (voir ci-dessous).

### Mesures réelles (20/10/2026)

| Mesure | Résultat |
|---|---|
| Atteignabilité des textes sans fiche (auto-récupération) | **858 / 858 articles (100 %)** |
| … dont par la référence exacte | 571 (le reste = même texte, autre exemplaire) |
| Rappel@5 sur 92 déclencheurs du catalogue | **20/92 (22 %)** |
| Rappel@25 | **42/92 (46 %)** |
| Présent quelque part dans le classement | **72/92 (78 %)** |
| Citations exactes acceptées | **15/15** |
| Citations altérées refusées | **15/15** |
| Abstentions attendues prononcées | **3/4** (voir limite 2 ci-dessous) |

Reproduire : `python3 bin/mesurer_recherche.py --rapport`.

**Deux articles avaient été comptés « manquants » (856/858) : c'était un défaut de la
mesure, pas du corpus.** La requête était construite avec le texte de l'exemplaire
**OCR**, donc avec ses corruptions (`Lerropriation` pour `L'expropriation`,
`lUrbanisme` pour `l'Urbanisme`) — introuvables par construction. Les articles 200
et 216 existent en calque propre et sortent aux rangs 2 et 1 dès que la requête est
propre. L'outil interroge désormais l'exemplaire `CALQUE_TEXTE` quand il existe ;
aucun score n'a été modifié.

Conclusion mesurée : le problème est le **classement**, pas la couverture. Un article
cité par une fiche descend souvent sous le top 5. C'est pourquoi les fiches restent
le seul chemin qui conclut, et pourquoi la recherche est annoncée comme un outil de
localisation.

### Deux limites assumées, testées comme témoins

1. **Le domaine est un seau à 12 clés** : AUSCGIE, AUSCOOP et AUPCAP partagent
   `contrats_dettes_commerce` (1 500 articles). « capital minimum d'une SARL » remonte
   une coopérative. D'où le paramètre `texte`, qui restreint par `numero_texte`
   (`test_sans_filtre_la_confusion_entre_actes_ohada_est_reelle` documente le défaut).
2. **Le lexical ne juge pas la pertinence** : « recette du gâteau au chocolat » remonte
   des articles fiscaux (« recettes »), avec un score supérieur à celui d'une vraie
   question. Trois signaux testés — couverture de la requête (33–100 %), vocabulaire
   absent du corpus (0–1 fragment), score (4,86–17,91) — **ne séparent pas** les deux
   classes. Aucun seuil n'est donc appliqué : il rejetterait une question légitime
   avant une question absurde. L'abstention n'est prononcée que sur absence de résultat.
   **Conséquence mesurée** : « quorum cooperative » restreint au domaine logement ne
   s'abstient pas (3/4 abstentions attendues) — les mots existent dans le texte du bail,
   mais la question n'a pas de réponse là. Le filtre de domaine borne le périmètre,
   il ne juge pas la pertinence.

## 6 quinquies ter. Courriers — générés, complétables, jamais envoyés

`core/service.rediger_courrier(dossier_id, informations=None)`
→ `POST /courrier` (moteur) → `POST /api/courrier` (interface)

**Ce qui a changé.** Le brouillon existait mais restait inutilisable : le PDF ne se
produisait **jamais** (`multi_cell` laissait le curseur au bord droit, fpdf2 levait
« Not enough horizontal space to render a single character »), et l'adresse de
l'expéditeur comme les pièces jointes étaient des trous permanents que personne ne
pouvait remplir.

**Contrat.**

```
{"dossier_id": str,
 "informations": {"expediteur"?, "destinataire"?, "pieces"?}}   # chaînes, jamais devinées
→ {"texte": str, "fondement": str|null, "champs_a_completer": [...],
   "genere": {"fichier_txt", "fichier_pdf", "pdf": {"ok", "erreur"}}, "note": str}
```

**Règles tenues, chacune couverte par un test.**

* **Rien n'est inventé** : nom, adresse, destinataire et pièces viennent de la personne.
  Ce qui manque est listé dans `champs_a_completer` avec la question à poser, et le
  remplissage `[À COMPLÉTER : …]` reste visible dans le texte.
* **Le fondement n'est cité que s'il est vérifié** : `article 416 de la loi n° 2019-576`
  n'apparaît que si la fiche repose sur une référence `VERIFIE`. Une fiche `OCR_AUTO`
  ou `PARTIELLEMENT_VERIFIE` produit un courrier **générique**, sans citation.
* **Un dossier sans analyse aboutie est refusé** (`ANALYSE_INCOMPLETE`) : on ne rédige
  pas un courrier avant d'avoir identifié le droit applicable.
* **Aucun envoi** : `genere.envoi` vaut `AUCUN — l'agent ne dispose d'aucune fonction d'envoi`.
* **Aucune écriture juridique** : les informations de courrier sont stockées dans
  `CONVERSATION.json` sous `courrier`, séparées des faits. Elles ne prouvent rien et
  ne modifient aucune analyse.

**Effet de bord corrigé au passage** : une fiche sans question de clarification
(`PENAL_457`, `TRANSP_2`…) produisait une étape de clarification **vide**, sans champ
à remplir ni bouton pour avancer. `ouvrir` conclut désormais directement quand
`questions` est vide.

**Tests** : `tests/test_courriers.py` (17), `web/tests/composants/affichage.test.tsx`,
`web/tests/integration/moteur.test.ts` (2 tests contre le moteur réel).

### Téléchargement du PDF — `GET /api/courrier/telecharger`

Le fichier existe côté moteur ; l'interface le sert sans jamais exposer de chemin.

**Quatre protections, dans cet ordre** (`web/src/lib/server/dossiers.ts`) :

1. **L'identifiant vient du cookie signé** (`deballer`, HMAC + comparaison en temps
   constant). Aucun identifiant n'est accepté en URL ni dans le corps : on ne peut
   pas demander le courrier d'un autre visiteur.
2. **Format verrouillé** (`MOTIF_ID` : `web-<uuid v4>`) : aucun `/`, aucun `.`, donc
   aucune traversée possible par construction — plus une seconde vérification dans
   `dernierCourrierPdf`.
3. **Nom de fichier non choisi par l'appelant** : le dossier BROUILLONS est listé et
   seuls les noms correspondant à `^\d{8}-\d{6}_reclamation\.pdf$` sont retenus.
4. **Confinement réel** : `realpath` du fichier doit avoir pour parent réel le dossier
   BROUILLONS attendu — un lien symbolique sortant est refusé (test dédié).

En-têtes servis : `Content-Type: application/pdf`, `Content-Disposition: attachment;
filename="courrier-mon-recours-ci.pdf"` (nom fixe, aucune donnée de l'utilisateur),
`Cache-Control: no-store`, `X-Content-Type-Options: nosniff`, CSP `default-src 'none'`.
Débit limité par le même limiteur que les autres routes. Aucun courrier → `404
COURRIER_ABSENT` (message explicite, pas d'erreur système).

Tests : `web/tests/unitaires/dossiers.test.ts` (8) et un test d'intégration qui
télécharge un vrai PDF (`%PDF-`) et vérifie qu'un cookie absent ou forgé est refusé.

## 6 sexies. Base SQLite et arbre de travail

`KNOWLEDGE/corpus_juridique.sqlite3` est versionnée : les tests en dépendent. Après une
exécution de tests, elle peut apparaître comme « modifiée » alors que **son contenu
logique est inchangé** — SQLite réécrit ses pages. Vérifier avant de committer :

```bash
python3 -c "import sqlite3;c=sqlite3.connect('KNOWLEDGE/corpus_juridique.sqlite3');\
print(c.execute('select count(*) from documents').fetchone()[0], \
c.execute('select count(*) from articles_corpus').fetchone()[0])"
# attendu : 26 1777
```

Si ces deux nombres sont bons, `git checkout -- KNOWLEDGE/corpus_juridique.sqlite3`
suffit. **Ne jamais committer une « mise à jour » de la base sans avoir vérifié ces
deux valeurs** : une base qui perd des articles se lit comme un corpus complet.

## 7. Commandes de validation

```bash
cd /Users/mac/mon_recours_ci
python3 tests/run_all.py                    # attendu : TESTS=515 ... VERDICT=SUCCES, exit 0
python3 bin/dialogue.py --catalogue          # les 92 fiches et leurs domaines
python3 bin/dialogue.py --dossier D1 --demande "Mon bailleur garde ma caution."
python3 bin/dialogue.py --dossier D1 --reponses logement=oui
python3 bin/rapport_sources.py             # KNOWLEDGE/ETAT_DES_SOURCES.md (état des sources)
python3 bin/rapport_couverture.py          # régénère l'inventaire + le rapport de mission
python3 bin/ocr_collecter.py --etat         # provenance des textes, sans réseau
python3 bin/demonstration.py                # 5 étapes sur 3 situations réelles
python3 bin/demonstration_corpus.py         # réponse documentée de bout en bout
./.venv-corpus/bin/python bin/collecter_corpus.py --etat
python3 bin/collecter_domaine.py --domaine famille_mariage_filiation --etat
```

## 8. Architecture recommandée pour l'application

```
[ Interface web ]
      │  POST /dossiers  {demande, elements_connus}
      ▼
[ Couche conversationnelle — À CONSTRUIRE ]   ← seul endroit où un LLM intervient
      │  propose : faits, domaines, ref_id candidats, brouillons
      ▼
[ Moteur déterministe — EXISTE ]              ← agent.py + core/*  (ne pas réécrire)
      │  valide, refuse, trace
      ▼
[ SQLite corpus + DOSSIERS/ ]                 ← EXISTE
```

Points d'attention pour l'intégration web :

* le moteur écrit des fichiers sous `DOSSIERS/` : prévoir un stockage
  cloisonné par utilisateur, avec la même garde que `config.dossier_utilisateur` ;
* ne jamais exposer `DOSSIER_TRACABILITE.json` d'un utilisateur à un autre ;
* l'ouverture de dossier est synchrone et rapide ; la **collecte** de corpus ne
  doit jamais être déclenchable depuis l'interface publique ;
* aucune fonction d'envoi ne doit être ajoutée dans `core/` : l'envoi, s'il
  arrive un jour, sera une action explicite de l'utilisateur, hors du cœur.

## 9. Tâches restantes, par priorité

| # | Tâche | Pourquoi |
|---|---|---|
| 1 | **Obtenir les textes des 9 domaines bloqués** (travail, pénal, consommation, associations, transport, santé, entreprises/OHADA, administration, numérique) | sans texte, ces domaines ne peuvent rien affirmer |
| 2 | **Obtenir la loi 2025-221** (contentieux des baux, exécution des expulsions) | lacune la plus grave du domaine A — voir `KNOWLEDGE/05_LACUNE_LOI_2025_221.md` |
| 3 | **Faire relire un échantillon d'articles par un juriste** | seul moyen d'atteindre `TERMINE_ET_VERIFIE` ; le statut existe déjà et se débloquera automatiquement |
| 4 | Améliorer le classement de recherche (l'article 3 remonte trop) | qualité de l'orientation |
| 5 | Construire la couche conversationnelle (LLM en amont, cœur en aval) | c'est le chaînon manquant vers une application |
| 6 | Ajouter des textes d'application (copropriété, foncier rural) | complète le domaine A |

**Ne pas** commencer par l'interface : elle n'a de valeur que si le moteur a des
textes à montrer. Le travail utile est la collecte et la relecture humaine.
