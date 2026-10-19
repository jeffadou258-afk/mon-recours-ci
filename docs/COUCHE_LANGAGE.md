# Couche de langage — fonctionnement, activation, coûts

**État : écrite et testée avec un faux fournisseur local. DÉSACTIVÉE.** Aucun appel
réel n'a été fait, aucune clé n'est configurée, aucune dépense n'est engagée.

## 1. Ce que fait le modèle, et ce qu'il ne fait pas

| Le modèle peut | Contrôle du moteur (`core/llm.valider_comprehension`) |
|---|---|
| choisir des fiches pour un récit, au-delà des mots-clés | identifiant présent dans le catalogue, sinon rejeté |
| pré-remplir une réponse que le récit donne déjà | clé du guide des fiches retenues, valeur oui/non, **extrait recopié du récit** vérifié littéralement ; la personne confirme |
| résumer la situation (« Ce que j'ai compris ») | 600 caractères au plus, **aucun nombre absent du récit** |

Il ne peut **pas** : citer un article, créer une fiche, répondre à la place de la
personne, écrire l'analyse. Les citations restent celles du catalogue, revalidées
contre le corpus. En cas de panne, de délai (8 s) ou de réponse illisible : repli
déterministe, sans interruption du service.

## 2. Activation (décision du propriétaire)

Trois variables sont nécessaires, côté serveur uniquement (`web/deploiement/env.exemple`) :
`MONRECOURS_LLM_FOURNISSEUR`, `MONRECOURS_LLM_API_KEY`, `MONRECOURS_LLM_ACCORD_DONNEES=oui`.

Avant envoi, `core/pseudonymisation.py` masque courriels et numéros de 9 chiffres et
plus. **Les noms et adresses écrits en clair ne sont pas masqués** : c'est pourquoi
l'accord explicite est exigé. Vérifier aussi, avec un juriste, les obligations
déclaratives liées à la loi n° 2013-450 (données personnelles) avant activation.

## 3. Coûts — prix publiés (consultés le 19/10/2026) et estimation

Estimation d'une consultation : environ 2 500 jetons envoyés (consigne + liste des
24 fiches + 18 questions + récit) et 300 jetons reçus. **C'est une estimation**,
à mesurer sur les premiers appels réels.

| Fournisseur et modèle | Prix publié (par million de jetons, entrée / sortie) | Estimation pour 1 000 consultations |
|---|---|---|
| Anthropic — Claude Haiku 5.5 | 0,10 $ / 0,50 $ ([source](https://platform.claude.com/docs/en/about-claude/pricing)) | ≈ 0,40 $ |
| Anthropic — Claude Sonnet 5.5 | 2 $ / 10 $ (même source) | ≈ 8 $ |
| OpenAI — gpt-6-luna | 0,10 $ / 0,50 $ ([source](https://developers.openai.com/api/docs/pricing)) | ≈ 0,40 $ |
| Mistral — Mistral Small 4 | 0,15 $ / 0,60 $ ([source](https://docs.mistral.ai/models/model-cards/mistral-small-4-0-26-03) ; la page n'indique pas lequel est l'entrée) | ≈ 0,55 $ |

Calcul : 2 500 × prix d'entrée + 300 × prix de sortie, par million, × 1 000.
Les prix changent : les relire avant tout engagement. Les modèles les moins
chers suffisent pour ce rôle limité (choisir, pré-remplir, résumer).

**Conflit d'intérêts à signaler** : ce code a été écrit par Claude, un modèle
d'Anthropic. L'adaptateur « compatible_openai » permet d'utiliser OpenAI,
Mistral ou un serveur local sans modifier le moteur ; le choix revient au
propriétaire.

## 4. Tests

`tests/test_comprehension_llm.py` (14 tests, faux serveur local au format de
l'API Messages) : fiche inventée, extrait non recopié, nombre ajouté au résumé,
clé hors sujet, erreur HTTP, serveur injoignable, réponse illisible, masquage
des coordonnées, absence de la clé dans tout message d'erreur.
