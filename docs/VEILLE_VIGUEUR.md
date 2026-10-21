# Veille de vigueur — ce qui est technique, ce qui est juridique

État mesuré le 21/10/2026 sur `KNOWLEDGE/corpus_juridique.sqlite3`.

## 1. Ce que la base sait aujourd'hui

| Indicateur | Valeur |
|---|---|
Références | **34** |
dont `VERIFIE` | 4 |
dont `PARTIELLEMENT_VERIFIE` | 30 |
dont `VERIFIE_MANUELLEMENT` | **0** |
Champ `modifications` renseigné | **0 / 34** |
Table d'abrogation | **aucune** |
Documents avec empreinte SHA-256 | 37 / 37 |
Documents avec URL source | 37 / 37 |
Articles issus d'OCR | 4 482 / 5 593 (**80 %**) |

Traduction : pour aucun texte le service ne peut affirmer qu'il est **en vigueur**
à une date donnée. Le moteur le dit déjà au lecteur
(`limites_texte` : « L'état de vigueur n'est pas garanti au-delà de la date de
consultation »), mais cette prudence repose sur une absence d'information, pas
sur une vérification.

## 2. Ce qu'une machine peut constater — et ce que fait `bin/veille_vigueur.py`

L'outil produit `KNOWLEDGE/veille_vigueur.json`. Par référence, il rassemble :

| Constat | Comment |
|---|---|
Adresse de la source | lue dans la base |
État de vérification enregistré | lu, jamais recalculé |
Présence du texte | longueur de l'extrait |
Qualité de lecture (OCR ou calque) | `note_qualite`, `note_ocr` |
Empreinte du document connu | `documents.sha256` |
Joignabilité de la source (`--reseau`) | code HTTP |
Document inchangé (`--reseau --empreintes`) | SHA-256 distant comparé au connu |

Et il inscrit, pour **chaque** entrée :

```
"statut_vigueur": "NON_VERIFIEE",
"a_valider_par_un_juriste": true
```

**Aucune exception, même si la source répond parfaitement.** C'est le point
central : une source joignable n'est pas une source à jour, et une empreinte
identique prouve seulement que le fichier n'a pas changé — pas qu'un texte
modificatif n'a pas été publié ailleurs.

## 3. Ce que seule une relecture juridique peut établir

Pour chaque texte, un juriste ivoirien doit répondre — et **rien ne peut être
déduit à sa place** :

1. **Le texte est-il en vigueur** à la date de consultation ?
2. **A-t-il été modifié** ? Par quel texte, à quelle date, sur quels articles ?
3. **A-t-il été abrogé**, totalement ou partiellement ?
4. **Les articles cités par le catalogue** (92 fiches) sont-ils ceux qui
   s'appliquent encore ?
5. **Le texte indexé est-il fidèle** à l'original, en particulier les 80 %
   issus d'OCR ? Une comparaison au fac-similé est nécessaire sur les articles
   réellement cités.
6. **La portée par forme sociale** est-elle exacte (AUSCGIE : art. 17, 65, 108,
   274 ne distinguent pas SARL/SA/SAAS) ?

Chaque réponse doit être enregistrée avec : qui, quand, sur quel document, et
quelle pièce le prouve. Un champ rempli sans pièce est pire qu'un champ vide.

## 4. Travaux techniques restants (réalisables sans juriste)

| # | Travail | État |
|---|---|---|
1 | Outil d'inventaire et de constats (`bin/veille_vigueur.py`) | **fait, testé** |
2 | Colonne `statut_vigueur` + `verifie_par` + `piece_justificative` dans la base | à faire (migration) |
3 | Affichage du statut de vigueur dans la réponse et dans les fiches | à faire |
4 | Blocage des fiches dont la vigueur n'est pas vérifiée, si l'on veut être strict | à décider |
5 | Rapport mensuel : sources mortes, documents modifiés, références sans relecture | outil prêt (`--reseau --empreintes`) |
6 | Comparaison OCR ↔ fac-similé sur les articles cités | partiel (`bin/comparer_lectures.py`) |

Ces travaux rendent la relecture **possible et traçable**. Ils ne la remplacent
pas.

## 5. Travaux juridiques (hors de portée d'un développeur)

| # | Travail | Pourquoi |
|---|---|---|
1 | Établir la vigueur des 34 textes | interprétation de textes modificatifs |
2 | Renseigner `modifications` et les abrogations | idem |
3 | Relire les 92 fiches (0 validée à ce jour) | responsabilité juridique |
4 | Vérifier les 80 % d'articles issus d'OCR | fiabilité de la citation |
5 | Valider les 90 jours de conservation | loi n° 2013-450, déclaration éventuelle |
6 | Trancher la provenance du Code du travail (3 exemplaires en quarantaine) | décision de source officielle |

## 6. Ce qu'il ne faut pas faire

- **Remplir `modifications` par déduction** (« ce texte est récent, il doit être
  en vigueur ») : c'est inventer une affirmation juridique.
- **Passer un statut à `VERIFIE`** parce que l'URL répond 200.
- **Présenter une couverture de 24 domaines** alors que 17 n'ont aucun texte.
- **Utiliser le rapport de veille comme preuve de vigueur** : il ne contient que
  des constats techniques.

## 7. Usage

```bash
# inventaire hors ligne (aucune requête réseau)
python3 bin/veille_vigueur.py

# constats réseau : source joignable ?
python3 bin/veille_vigueur.py --reseau

# document officiel inchangé depuis la collecte ?
python3 bin/veille_vigueur.py --reseau --empreintes
```

Le rapport est écrit dans `KNOWLEDGE/veille_vigueur.json` ; **la base n'est
jamais modifiée par cet outil**.
