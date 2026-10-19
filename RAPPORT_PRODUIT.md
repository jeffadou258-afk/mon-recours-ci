# RAPPORT PRODUIT — Mon Recours CI

Branche `feature/produit-fonctionnel` · 19 octobre 2026 · `main` non modifiée,
rien déployé. « Vérifié » = vérifié **techniquement** par un test exécuté ; aucun
test ne vaut validation juridique.

## 1. Lots réalisés

| Lot | Résultat | Commits |
|---|---|---|
| 0 — Spécification | `SPEC_RECONSTITUEE.md` : sources retrouvées, spécification d'origine introuvable, 5 contradictions et leur résolution, hypothèses à valider | `df70915` |
| 1 — Conversation | 18 questions tirées des articles (contrôle : aucun nombre absent de l'article) ; jusqu'à 3 tours ; pré-remplissage depuis le récit ; contradictions relevées puis confirmées ; manques nommés avec leur raison | `b3c5e1a`, `d3bf24e` |
| 2 — Couche de langage | Compréhension par un modèle, revalidée par le moteur ; adaptateurs Anthropic et compatible OpenAI ; masquage des coordonnées ; **désactivée** ; coûts documentés | `e11c0cc` |
| 3 — Documents et données | Synthèse et brouillon téléchargeables (texte), impression / PDF, suppression de la consultation par la personne | `e205f97` |
| 4 — Fiabilité | Urgence affichée hors catalogue (défaut de sécurité corrigé) ; aiguillage corrigé ; 16 scénarios de référence ; 2013-711 levé ; voie d'accès 2025-221 | `7783af0` |
| 5 — Démarrage et rapport | `scripts/demarrer-local.sh`, coûts de mise en ligne, ce rapport | dernier commit |

## 2. Tests réellement exécutés

| Suite | Où | Résultat |
|---|---|---|
| Moteur (`python3 tests/run_all.py`) | espace de travail, et CI GitHub Actions | 425 tests, 0 échec, 5 ignorés (PDF officiels absents du dépôt) |
| Web — unitaires et composants | espace de travail, et CI | 54 / 54 |
| Web — intégration avec le moteur réel | espace de travail, et CI | 11 / 11 |
| Web — bout en bout, Chromium mobile et bureau | espace de travail, et CI | 10 / 10 |
| Typage, construction Next.js, audit npm, secrets | CI uniquement (dépendances complètes) | réussis sur `3f990d9` (un défaut de typage détecté par la CI sur `e205f97` a été corrigé) ; audit npm : 0 vulnérabilité |
| Sur le Mac du propriétaire | **non exécuté** (pas d'accès) | à lancer : `bash scripts/demarrer-local.sh --tests` |

## 3. Matrice de conformité — parcours utilisateur (mission du 19/10)

| # | Étape | Statut | Preuve |
|---|---|---|---|
| 1 | Comprendre l'utilité | Opérationnelle et vérifiée | accueil, couverture lue sur `/sante` ; e2e « accueil mobile » |
| 2 | Décrire librement | Opérationnelle et vérifiée | `Parcours.tsx`, `/api/ouvrir` ; e2e |
| 3 | Questions adaptées | Partiellement implémentée | 15 fiches sur 24 ont des questions ; tours successifs (`core/clarification.py`, `test_clarification.py`) ; compréhension fine du langage : seulement avec le modèle, désactivé |
| 4 | Analyse fondée sur les faits | Partiellement implémentée | lectures conditionnelles au vu des réponses ; analyse limitée aux fiches |
| 5 | Explication des règles | Partiellement implémentée | lectures en français simple, **non relues par un juriste** |
| 6 | Sources consultables | Opérationnelle et vérifiée | citation mot pour mot, empreinte, lien officiel ; e2e |
| 7 | Options et recours | Partiellement implémentée | démarches des fiches ; pas d'options comparées |
| 8 | Plan d'action | Partiellement implémentée | `4_demarches`, verrous humains |
| 9 | Pièces à réunir | Partiellement implémentée | indiquées dans les démarches de certaines fiches |
| 10 | Courriers préparés | Opérationnelle et vérifiée | brouillon de réclamation, « À COMPLÉTER » ; e2e |
| 11 | Consulter et télécharger | Opérationnelle et vérifiée | synthèse et brouillon en .txt, impression / PDF ; e2e lit le fichier téléchargé |
| 12 | Orientation vers un professionnel | Partiellement implémentée | verrous humains, numéros d'urgence sourcés ; **aucun annuaire de professionnels** (contacts vérifiés à fournir) |
| 13 | Retrouver son dossier | Absente — décision | pas de comptes (hypothèse 1 de la spécification) ; suppression possible |

## 4. Fonctions transverses

| Fonction | Statut | Preuve ou blocage |
|---|---|---|
| Aucune invention de citation | Opérationnelle et vérifiée | revalidation du catalogue au chargement ; `ANALYSE_REFUSEE` |
| Aucun délai ou chiffre ajouté par les questions | Opérationnelle et vérifiée | `clarification.valider` ; test d'un délai inventé |
| Contradictions | Partiellement implémentée | récit / réponse uniquement (`clarification.contradictions`) |
| Urgence et verrous, y compris hors catalogue | Opérationnelle et vérifiée | `test_scenarios_reference.py`, e2e violences |
| Modèle de langage | Bloquée par une décision | prêt et testé avec un faux fournisseur ; clé, budget et accord sur les données à fournir |
| Isolation des dossiers | Opérationnelle et vérifiée | cookie signé HttpOnly, identifiant serveur ; suppression ciblée testée |
| Suppression par la personne | Opérationnelle et vérifiée | `/api/supprimer`, intégration et e2e |
| Conservation et purge automatique | Bloquée par une décision | outil de purge prêt ; durée non décidée |
| Chiffrement au repos, sauvegardes | Absente | dépend de l'hébergement choisi |
| Mise en ligne | Bloquée par une décision | guide `web/deploiement/README.md` ; rien déployé |
| Domaines couverts | Partiellement implémentée | 4 domaines du moteur ; 14 des 24 domaines de la vision sans texte |
| Validation juridique humaine | Absente | aucune relecture tracée |

## 5. Corpus — lacunes vérifiées

* **Loi 2025-221** : reproduction CIVLII (CC BY 4.0, JO n° 32 du 21/04/2025)
  identifiée ; non intégrée (reproduction ; décision du propriétaire).
  `KNOWLEDGE/05_LACUNE_LOI_2025_221.md`.
* **Décret 2013-711** : numéro confirmé, écart « 2013-791 » levé et consigné sur la référence.
* **179 articles OCR (numérique)** : toujours neutralisés.
* **Questions et lectures** : statut `A_RELIRE_PAR_UN_JURISTE`.

## 6. Validations humaines encore nécessaires

1. Relecture juridique des 24 fiches et des 18 questions.
2. Accord, fournisseur et budget pour le modèle de langage.
3. Durée de conservation des récits.
4. Hébergement (serveur unique recommandé) et nom de domaine.
5. Contacts d'orientation vérifiés (aide juridictionnelle, barreau, cliniques).
6. Choix d'une source pour la loi 2025-221.

## 7. Obstacles à une utilisation publique

Absence de relecture juridique ; couverture étroite ; durée de conservation, chiffrement
au repos et sauvegardes non décidés ; pas de test d'intrusion ; conformité « données
personnelles » (loi 2013-450) non établie par un juriste.

**Prêt pour un pilote ?** Techniquement : le parcours complet fonctionne avec le moteur
réel, les erreurs sont gérées, les tests critiques passent, les secrets sont protégés,
l'isolation est testée, le démarrage est reproductible. **Non** au sens des critères de
fin de la mission tant que les domaines activés n'ont pas reçu de relecture juridique.
