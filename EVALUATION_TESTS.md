# EVALUATION_TESTS — Mon Recours CI

Comment le projet se prouve, et ce que ses preuves **ne** disent pas.

```bash
cd /Users/mac/mon_recours_ci
python3 tests/run_all.py          # suite complète : verdict factuel, code de sortie
python3 bin/rapport_couverture.py # rejoue la suite et écrit l'inventaire
```

Dernier état mesuré : **279 tests, FAIL=0 ERR=0 SKIP=0, exit 0**.

---

## 1. Quatre familles de tests, jamais confondues

| Famille | Ce qu'elle prouve | Fichiers |
|---|---|---|
| **Logicielle** | le code fait ce qu'il annonce | `test_analyse`, `test_base`, `test_faits`, `test_documents`, `test_orchestrateur`, `test_urgence`, `test_domaines` |
| **Sécurité / refus** | l'agent s'arrête quand il doit s'arrêter | `test_garde_fous`, `test_human_gate`, `test_confidentialite` |
| **Provenance** | d'où vient chaque texte, et est-ce dit | `test_ocr`, `test_corpus_foncier`, `Test14NonRegression` |
| **Juridique (domaines)** | le fond est adossé à des articles réels | `test_cas_juridiques`, `test_domaines` |

Aucune de ces familles ne constitue une **validation juridique humaine**. C'est
une cinquième catégorie, qui n'existe pas encore dans ce projet.

## 2. Les 14 épreuves exigées, par domaine

`tests/test_domaines.py` porte une classe par épreuve :

| # | Épreuve | Classe |
|---|---|---|
| 1 | Question simple soutenue par un texte officiel | `Test1QuestionSimpleSoutenueParUnTexteOfficiel` |
| 2 | Question nécessitant plusieurs articles | `Test2QuestionNecessitantPlusieursArticles` |
| 3 | Information manquante | `Test3InformationManquante` |
| 4 | Texte incomplet conservé mais non citable | `Test4TexteIncomplet` |
| 5 | État de vigueur incertain | `Test5VigueurIncertaine` |
| 6 | Fautes d'orthographe et formulations courantes | `Test6QuestionAvecFautes` |
| 7 | Mot juridique employé pour un autre | `Test7MotJuridiqueIncorrect` |
| 8 | Situation relevant de plusieurs domaines | `Test8PlusieursDomaines` |
| 9 | Cas à risque → orientation humaine | `Test9RisqueOrientationHumaine` |
| 10 | Hors corpus → refus de conclure | `Test10HorsCorpusRefusDeConclure` |
| 11 | Article ou délai inventé → refus | `Test11InventionRefusee` |
| 12 | La citation soutient réellement l'affirmation | `Test12LaCitationSoutientLaffirmation` |
| 13 | Confidentialité et contrôle des données | `Test13Confidentialite` |
| 14 | Non-régression des acquis | `Test14NonRegression` |

Plus `TestStatutsDeDomaine` : les statuts de couverture sont calculés,
cohérents, et **jamais flatteurs**.

### Règles d'écriture suivies (et pourquoi)

1. **Un cas s'appuie sur le corpus réel.** Aucun attendu n'est inventé pour faire
   passer un test. Quand un texte manque, le test vérifie que l'agent **dit**
   qu'il manque.
2. **Un test de refus exige un témoin légitime.** Six demandes légitimes
   verrouillent `MENACE`/`VIOLENCE`.
3. **Un témoin doit pouvoir échouer.** Le premier test de la régression
   `autojunk` comparait deux textes quasi identiques : l'écart mesuré était nul,
   il ne prouvait rien. Remplacé par un témoin à graine fixe où l'écart est réel
   (0,00 contre 0,26).
4. **Un contrôle sur le code se fait sur l'AST, pas sur le texte.** Chercher
   « smtp » dans `documents.py` déclenchait un faux positif sur sa docstring
   (« aucun envoi (smtp…) »). Le test lit maintenant l'arbre syntaxique.

## 3. Défauts réels trouvés par les tests pendant cette mission

Chacun a été corrigé, et chacun a laissé un test :

| Défaut | Impact | Correction |
|---|---|---|
| `enregistrer_articles` n'écrasait jamais un article existant | une correction d'extraction (nettoyage des artefacts d'éditeur) restait **invisible** en base : deux vérités dans le même corpus | `remplacer=True` (UPSERT), utilisé par les collecteurs |
| `importer_document` ne mettait jamais à jour un document existant | la note de qualité « découpage en articles non fiable » ne pouvait pas s'écrire | `actualiser=True` |
| `agent.dossier()` et `lire_en_cours()` levaient `FileNotFoundError` | une absence normale passait pour une panne | renvoient `None` ; `clore_dossier` refuse explicitement un dossier jamais ouvert |
| Le routage ne résistait pas aux fautes | « je veu comprendre le contrat de bai » ne routait pas vers le logement | troncature et distance 1 (`_distance_un`), score 0,5 |
| Un seuil `minimum_articles=5` refusait un texte valide | la loi 2020-623 (2 articles) était rejetée | seuil devenu un plancher explicite |
| Les marqueurs `--- PAGE n ---` de l'OCR entraient dans le corps des articles | artefact d'outil dans une citation potentielle | retirés à l'extraction |
| Les pieds de page d'un éditeur tiers entraient dans les articles | citation polluée + provenance effacée | `retirer_artefacts_editeurs` + dégradation de la référence |

## 4. Ce qu'un test vert ne prouve PAS

* Qu'un juriste a validé le contenu → **aucun article n'a été relu** (`VERIFIE_MANUELLEMENT = 0`).
* Que le corpus est complet → 9 domaines sur 11 sont `BLOQUE_SOURCE`.
* Que les textes sont à jour → l'état de vigueur est vérifié **à la date de consultation**, jamais au-delà.
* Qu'une réponse est juridiquement juste → elle est seulement **tracée** à un article réel.

`core/couverture.py` refuse de rendre `TERMINE_ET_VERIFIE` tant qu'une relecture
humaine n'est pas tracée, et `TestStatutsDeDomaine` verrouille ce refus.
