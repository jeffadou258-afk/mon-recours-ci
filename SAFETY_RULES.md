# SAFETY_RULES — Mon Recours CI

Règles non négociables du projet. Elles sont **encodées dans le code**, pas
seulement écrites ici : chaque règle cite le module qui la fait respecter et le
test qui la verrouille. Une règle qui n'est ni codée ni testée n'est pas une
règle, c'est une intention.

Ces règles passent avant la complétude, avant la vitesse, et avant l'envie
d'aider. Un refus explicite est toujours préférable à une réponse fausse.

---

## 1. Aucune invention

| Règle | Où c'est tenu | Test |
|---|---|---|
| Aucune loi, aucun article, aucun délai, aucune procédure n'est inventé | `core.analyse.valider` → `REF_INCONNUE`, `REF_VIDE`, `REGLE_SANS_SOURCE` | `test_analyse`, `Test11InventionRefusee` |
| Aucune référence ne sort du corpus | `core.base` exige des métadonnées obligatoires (contraintes SQL) | `test_base` |
| Aucun nombre (montant, durée, quantité) sans appui | `NOMBRE_NON_SOUTENU` + `core.corpus.verifier_regle_article` | `Test11InventionRefusee.test_nombre_non_soutenu` |
| Aucun article cité qui ne soit réellement indexé | `core.corpus.obtenir_article_par_reference` | `Test1`, `test_cas_juridiques` |

**Pourquoi un contrôle au niveau de l'article** : sur un texte de 290 000
caractères, « le plafond est de 95 000 FCFA » finit toujours par apparaître
quelque part. Comparer au **seul article cité** est ce qui refuse réellement
l'invention.

## 2. Une interprétation n'est jamais une citation

Une citation doit être **délimitée par des guillemets** et se retrouver
littéralement dans le texte indexé (`core.analyse.ajouter_regle` lève sinon).
`core.corpus.verifier_citation_article` recalcule l'empreinte de l'article pour
vérifier que le texte n'a pas bougé depuis.

## 3. La provenance ne disparaît jamais

| Règle | Tenue par |
|---|---|
| Un texte reconnu par OCR reste `OCR_AUTO` — il ne devient **jamais** `CALQUE_TEXTE` | `core.corpus.enregistrer_articles` (valeur d'`origine_texte` validée), `core.ocr.ORIGINES` |
| Une règle appuyée sur un article OCR **non recoupé** exige une incertitude déclarée | `core.corpus.verifier_provenance_analyse` → `PROVENANCE_OCR_NON_DECLAREE` |
| Un scan ne devient pas un document à calque texte après OCR (`calque_texte` reste 0) | `test_ocr.TestProvenanceDansLeCorpusLivre` |
| Une **reproduction tierce** (Laws.Africa, dépôt international) n'est **jamais** promue `VERIFIE` | `core.corpus.textes_contaminants` + `bin/collecter_domaine.py` |
| `VERIFIE_MANUELLEMENT` reste à **0** tant qu'aucun humain n'a relu | `Test14NonRegression.test_aucune_validation_humaine_nait_toute_seule` |

**Découverte réelle** : un PDF publié par un ministère (`famille.gouv.ci`) était
une reproduction **Laws.Africa sous licence CC BY 4.0**, avec les pieds de page
de l'éditeur tombant *dans le corps des articles*. Traitement retenu : les
mentions sont retirées du texte indexé, l'attribution est conservée dans les
métadonnées du document, et la référence est **dégradée** de `VERIFIE` à
`PARTIELLEMENT_VERIFIE`. La promotion est journalisée dans la table
`verifications` : rien n'est silencieux.

## 4. Aucune action extérieure

| Interdit | Preuve |
|---|---|
| Envoyer un courrier, un message, une plainte | `core/documents.py` n'a **aucune** fonction d'envoi ; un test lit l'**AST** du module (pas ses commentaires) |
| Déposer un document auprès d'une administration ou d'un tribunal | aucun code de dépôt n'existe |
| Publier, déployer, activer un service payant | aucune fonction de déploiement ; pas de clé API dans le dépôt |
| Ouvrir une connexion réseau hors du périmètre | seul `core/sources.py` et les collecteurs `bin/*` touchent le réseau — vérifié par lecture des sources |

Les brouillons portent la mention **BROUILLON — NON ENVOYÉ** et listent les
champs à compléter.

## 5. Confidentialité

* Chaque dossier est **cloisonné** : `config.dossier_utilisateur` refuse tout
  identifiant contenant `/`, `\`, `..` ou un octet nul (`test_confidentialite`).
* Aucun dossier d'un utilisateur n'est lisible depuis le dossier d'un autre.
* Les données des dossiers de **démonstration** (`DEMO_*`) sont séparées des
  dossiers de test (`TEST_*`), nettoyés par les tests.
* Aucune donnée personnelle n'est écrite dans les journaux techniques : les
  messages portent des identifiants de dossier, des numéros d'article et des
  empreintes — jamais un nom, une adresse ou un montant de dossier réel.

## 6. Escalade humaine obligatoire

L'intervention d'un humain est **obligatoire** (et le code pose un verrou) dès
qu'il y a : danger immédiat, violence, menace contre une personne, procédure
pénale, expulsion imminente, enfant ou personne vulnérable, délai de recours
proche, perte importante de droits, source contradictoire, texte essentiel
absent, ou représentation professionnelle nécessaire.

Un verrou humain **ne se ferme jamais tout seul** : sans marqueur explicite, le
code lève. Un refus (`statut == "REFUS"`) ne produit **aucune** analyse.

## 7. Faire face à la détresse, pas la bloquer

Le motif de refus `MENACE` / `VIOLENCE` exige un **marqueur de demande**
(*aide-moi à…*, *écris…*, *rédige…*, *je veux…*) suivi de l'acte demandé. Sans
cette règle, « mon mari menace de me tuer, quels sont mes droits ? » était
refusé — le pire défaut possible pour un agent citoyen.

**Six témoins légitimes** verrouillent ce comportement : chaque test de refus est
accompagné d'une demande légitime qui **ne doit pas** être refusée.

## 8. Ne jamais contourner une restriction d'accès

Aucune authentification forcée, aucun paywall franchi, aucun robots.txt ignoré.
Les obstacles rencontrés (`jorci.oneci.ci` en 503, `sgg.gouv.ci/jo.php` derrière
un identifiant, `biblio.cndj.ci` payant) sont **relevés, nommés et documentés** —
voir `KNOWLEDGE/01_SOURCES_OFFICIELLES.md`.

## 9. Ne pas promettre de résultat, ne pas représenter

L'agent n'est ni avocat, ni notaire, ni huissier, ni magistrat, ni autorité
administrative. Il ne garantit aucune victoire, aucun remboursement, aucune
expulsion, aucune condamnation. Aucun champ de la base ne permet de déclarer un
résultat obtenu.

## 10. Traçabilité proportionnée

Chaque dossier clos produit `DOSSIER_TRACABILITE.json` avec : demande, faits
déclarés **et** documentés, articles effectivement vérifiés (avec empreinte),
incertitudes, limites, plan d'action, orientations, et la liste explicite
`champs_non_renseignes`. Ce qui manque est **nommé**, jamais omis.

---

## Ce que ces règles ne garantissent pas

Elles garantissent qu'**aucune affirmation non tracée ne sort**. Elles ne
garantissent pas que le corpus soit complet, ni que les textes soient à jour
au-delà de leur date de consultation, ni qu'un juriste ait validé le contenu :
`VERIFIE_MANUELLEMENT = 0`. La fiabilité du raisonnement n'est pas la vérité du
droit.
