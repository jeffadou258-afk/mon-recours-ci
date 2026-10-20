# HANDOFF HERMES — Mon Recours CI (20/10/2026)

## État actuel
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
