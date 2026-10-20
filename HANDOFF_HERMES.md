# HANDOFF HERMES — Mon Recours CI (20/10/2026)

> **INSTANTANÉ DATÉ — PÉRIMÉ SUR LES CHIFFRES.** Ce document décrit l'état au
> moment de sa rédaction (36 documents, 4 707 articles, 481 tests). L'état courant
> est : **37 documents, 5 593 articles, 34 références, 92 fiches, 515 tests** —
> voir `README.md` et `CLAUDE_HANDOFF.md`, qui font foi. Les constats de méthode
> et l'historique des refus restent valables ; les compteurs, non.

## État actuel (à la date de rédaction)
- Moteur juridique Python (stdlib seule) + interface Next.js (`web/`). Aucun fournisseur IA payant activé (`MONRECOURS_LLM_FOURNISSEUR` non défini = mode déterministe) : le laisser ainsi.
- Base `KNOWLEDGE/corpus_juridique.sqlite3` : integrity_check ok, 0 violation de clé étrangère, 36 documents, 4 707 articles, 33 références (29 PARTIELLEMENT_VERIFIE, 4 VERIFIE). sha256 `3deec08f…c1d707`.
  Reconstruite par `bin/reconstruire_base.py` (8 contrôles OK) ; sauvegarde locale de la précédente non versionnée (`KNOWLEDGE/.sauvegardes/`).
- Textes intégrés par OCR (journal `KNOWLEDGE/collecte/integrations_ocr.json`) : Code pénal 2019-574 (557 art.), CPP 2018-975 (841), mariage 2019-570 (105), successions 2019-573 (130), minorité 2019-572 (157), AUCOOP 2010 (365), AUPCAP 2015 JO OHADA (249, nouveau).
- Refusés, volontairement : état civil 2018-862 (couverture 83 % < 85 %), pupilles 2015-539, AUDTMR 2003, versions OHADA abrogées, CIMA/MEF (sources candidates), Code du travail (fac-similé FAOLEX secondaire seulement : fiches en brouillon, non chargées).
- 77 fiches, 28 questions de clarification. Toutes les fiches sont A_RELIRE_PAR_UN_JURISTE : aucune n'est validée juridiquement.

## Branches (aucune n'est fusionnée dans `main`)
Elles s'empilent sans conflit : main → feature/interface-web → feature/domaine-famille → feature/produit-fonctionnel → audit/24-domaines → corpus/collecte-24-domaines → **corpus/collecte-autonome** (branche de référence, elle contient toutes les autres).
- `corpus/archives-pdf` : archive des PDF collectés (pas du code ; `python3 bin/integrer_collecte.py pdf` les récupère).
- Un push sur `corpus/collecte-autonome` déclenche le workflow GitHub Actions « Corpus — collecte documentaire », gratuit dans le quota, environ 400 minutes utilisées sur 2 000. Le bot pousse ses constats sur la branche : toujours faire `git pull --rebase` avant de pousser.

## Tâches restantes (par priorité)
1. Lancer la suite complète de tests. Elle n'a **pas** été relancée après l'intégration d'AUCOOP et d'AUPCAP (dernière exécution complète : 481 tests OK, avant ces deux intégrations).
2. Le prochain run collectera `ohada_jo_bulletin_1696_explnum_2799` (arbitrage/médiation 2017) et `ohada_jo_bulletin_1722_explnum_3974`. Ensuite : `pdf`, `controler`, identifier le texte, `ocr_local.py` si c'est un scan, puis `reconstruire_base.py`.
3. Trouver le JO OHADA en vigueur de l'AUDCG 2010 et de l'AUSCGIE 2014 (bulletin 1561 sans fichier) ; trouver le Code du travail 2015-532 officiel ; obtenir un meilleur scan de l'état civil 2018-862.
4. Fiches pour les coopératives et les procédures collectives (citations mot pour mot via `bin/ajouter_fiches.py`, statut A_RELIRE).
5. Décisions réservées au propriétaire : relecture par un juriste, identité des hôtes CIMA/MEF, mise en ligne, fusion dans `main`.

Règles : ne jamais inventer de règle juridique ; garder la citation et la provenance ; ne pas contourner les paywalls ou les connexions (CIVLII réservé aux abonnés) ; ne jamais intégrer un OCR douteux comme source certaine ; ne pas fusionner dans `main` ni déployer sans accord.

## Commandes (Mac)
```bash
cd /Users/mac/mon_recours_ci        # ou : git clone https://github.com/jeffadou258-afk/mon-recours-ci.git
git fetch origin && git checkout corpus/collecte-autonome && git pull --rebase
MONRECOURS_PDF_NON_DISTRIBUES=1 python3 tests/run_all.py       # moteur (Python 3.9+)
(cd web && npm ci --ignore-scripts && npm run typecheck && npm test)   # interface (Node 20.9+)
bash scripts/demarrer-local.sh                                  # moteur 127.0.0.1:8765 + web :3000
# Collecte / OCR : brew install poppler tesseract tesseract-lang
python3 bin/integrer_collecte.py pdf && python3 bin/integrer_collecte.py controler
TESSDATA_BEST=/chemin/tessdata_best python3 bin/ocr_local.py --cle <clé>
python3 bin/reconstruire_base.py --depart 1ca6e7f --cle <clé> ... [--remplacer]   # remplace la base seulement si tous les contrôles passent
```
Pour `reconstruire_base.py`, reprendre la liste des `--cle` du dernier rapport : `KNOWLEDGE/collecte/reconstruction_base.json`, champ `integrations_demandees`, plus la nouvelle clé.

## Prochaine action recommandée
Lancer `MONRECOURS_PDF_NON_DISTRIBUES=1 python3 tests/run_all.py` sur `corpus/collecte-autonome` et corriger tout échec avant d'entreprendre autre chose.

---

# Journal de la session Hermes du 20/10/2026 (soir)

## Tests — mesurés, pas repris
`MONRECOURS_PDF_NON_DISTRIBUES=1 python3 tests/run_all.py` → **485 tests, FAIL=0, ERR=0,
SKIP=1, SUCCES=484, exit 0** (336 s). Aucun test à corriger après l'intégration d'AUCOOP
et d'AUPCAP : les 481 annoncés sont devenus 485, tous verts. Le seul test ignoré ne
teste quelque chose que si le PDF est absent.

## `bin/rapport_couverture.py` — trois défauts corrigés
1. Il calculait l'inventaire **avant** de lancer la suite : les deux processus se
   disputaient la base SQLite et le rapport enregistrait des échecs qui n'existaient
   pas (`FAIL=2 ERR=2` constatés, `0` en exécution isolée). Les tests sont désormais
   lancés **en premier**.
2. `MONRECOURS_PDF_NON_DISTRIBUES` n'atteignait ni la suite ni `verifier_integrite()` :
   le rapport annonçait `ECHEC` et `ECART DETECTE` alors que tout était sain. Le mode
   est maintenant transmis aux deux, avec `MONRECOURS_PDF_NON_DISTRIBUES=0` pour
   rétablir le mode strict sur un poste qui possède les PDF.
3. Il ne conservait que `TESTS=`/`VERDICT=`, jamais **quel** test avait échoué. Le
   journal complet est écrit dans `KNOWLEDGE/collecte/derniers_tests.log` et chaque
   échec (nature, test, module, trace) est enregistré dans `RAPPORT_FINAL_MISSION.json`.

## Fiches OHADA — 6 ajoutées (77 → 83)
`bin/construire_fiches_ohada.py` génère les définitions ; `bin/ajouter_fiches.py` les
revalide contre la base avant écriture. Les bornes de citation sont **extraites** du
texte indexé (recherche tolérante aux apostrophes typographiques), jamais retapées.

| Fiche | Article | Situation |
|---|---|---|
| `OHADA_AUPCAP_CESSATION` | AUPCAP 1 | entreprise qui ne peut plus payer ses dettes |
| `OHADA_AUPCAP_SALAIRES` | AUPCAP 95 | salaires impayés en procédure collective |
| `OHADA_AUSCOOP_DEFINITION` | AUSCOOP 4 | ce qu'est une coopérative |
| `OHADA_AUSCOOP_PARTS` | AUSCOOP 208 | parts sociales, valeur fixée par les statuts |
| `OHADA_AUSCOOP_ENGAGEMENTS` | AUSCOOP 62 | augmentation des engagements sans consentement |
| `OHADA_AUSCOOP_RESERVE` | AUSCOOP 114 | réserve générale sur les excédents |

Toutes sont `PARTIELLEMENT_VERIFIE`, `origine_texte = OCR_AUTO`, `recoupe = False`, et
leur citation porte l'avertissement de césure OCR (`réu- nies`, `géné- rale`). Aucune
n'est validée juridiquement. **Il reste 365 articles AUSCOOP et 249 AUPCAP sans fiche** :
ces six fiches couvrent des situations courantes, pas le texte entier.

## AUSCGIE 2014 — PDF authentifié, INTÉGRATION REFUSÉE APRÈS CONTRÔLE QUALITÉ
Séquence réellement exécutée :

1. `git fetch --depth=1 origin corpus/archives-pdf` a **réussi** (la branche fait 76 PDF) ;
   `pdf/ohada_jo_bulletin_1722_explnum_3974.pdf` y est.
2. PDF extrait : **sha256 `143aab11d2fe189d…` identique** à l'empreinte enregistrée par
   la collecte, 6 288 638 octets, PDF 1.4. Identité confirmée.
3. `integrer_collecte.py controler` → `EXPLOITABLE_OFFICIEL`, `CALQUE_TEXTE`,
   `integrite_pdf = OK`, 240 pages, aucune quarantaine.
4. Intégration effectuée : 37 documents, 5 613 articles (+906), intégrité ok.
5. **Contrôle qualité : REFUSÉ, base restaurée** (sauvegarde
   `KNOWLEDGE/.sauvegardes/corpus_20261020-132725_avant_auscgie.sqlite3`).

Motif mesuré — le calque texte de ce PDF InDesign 2014 est **systématiquement dégradé** :

| Indice | Valeur |
|---|---|
| caractères accentués | **0,21 %** (987 / 469 160) |
| comparaison 2019-576 (calque sain) | **3,28 %** (3 293 / 100 446) |
| « Ie » au lieu de « le » | 1 366 |
| « societe » sans accent | 1 039 |
| « Btat » au lieu d'« État » | 4 |

**Défaut du moteur mis au jour** : `officialiser` (voie calque) promeut la référence
`VERIFIE` sur la seule couverture des numéros d'articles (98 % de 1..920), sans mesurer
la qualité des caractères. Un texte à 0,21 % d'accents a donc été publié `VERIFIE`.
**À corriger avant tout usage** : un seuil de qualité de caractères doit bloquer la
promotion `VERIFIE` (et sans doute l'indexation) sur un calque dégradé.

**Prochaine action pour l'AUSCGIE** : passer par `bin/ocr_local.py` (tesseract, double
lecture concordante) comme pour AUPCAP/AUSCOOP, et non par le calque. Le PDF est
authentique et disponible ; c'est la lecture qui doit être refaite.

## Doublon `2019-572` — proposition, aucune suppression
| | `DOC-A443F2E78D1D` | `DOC-25C3088D557C` |
|---|---|---|
| Source | famille.gouv.ci | oneci.ci (republication du JO) |
| OCR | **refusé, couverture 58 %** | `OCR_EDITEUR`, 157 articles |
| Rôle | exemplaire mort | **exemplaire utilisable** |

Les deux doivent rester : l'un porte la trace du refus, l'autre le texte. Résolution
proposée — conserver les deux documents et leurs deux références, et annoter la
référence du scan refusé pour qu'elle renvoie explicitement à l'exemplaire indexé. Une
correction par `UPDATE` direct ne survivrait pas à `reconstruire_base.py` : il faut
passer par le manifeste/journal d'intégration. **Décision à valider par le propriétaire.**

