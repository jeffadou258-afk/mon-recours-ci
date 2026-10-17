# -*- coding: utf-8 -*-
"""Corpus documentaire — documents officiels téléchargés, texte et articles indexés.

Ce module est ADDITIF : il ajoute deux tables au même fichier SQLite
(`documents`, `articles_corpus`) et ne modifie aucune règle existante de
`core/base.py`. Les invariants déjà testés restent en place.

Ce qu'il garantit :

1. **Un document n'entre qu'avec sa preuve.** `importer_document` recalcule le
   SHA-256 du fichier local et le compare à celui déclaré ; il exige une URL
   d'origine sur un hôte officiel, une licence/condition d'accès explicite, et
   le nombre de pages. Un fichier absent, un hôte non officiel ou une empreinte
   qui ne correspond pas lèvent une exception.
2. **Un scan n'est pas un texte.** `calque_texte = 0` pour un PDF sans police
   embarquée : il est enregistré comme accessible mais NON exploitable, et le
   `texte_complet_present` de la référence correspondante reste à 0. Une
   citation ne pourra donc jamais s'y appuyer.
3. **Un article est toujours rattaché à un document et à une référence.**
   `articles_corpus` porte une clé étrangère vers les deux, plus l'empreinte du
   texte de l'article.
4. **L'intégrité se revérifie.** `verifier_integrite()` recalcule les empreintes
   sur disque : c'est ce qui prouve que le corpus n'a pas dérivé.

La sélection est MÉCANIQUE, pas éditoriale : le parseur indexe tous les articles
du texte (`extraire_articles`), avec un taux de couverture mesuré et rapporté.
"""

import datetime
import hashlib
import math
import os
import re
import sqlite3

import config
from config import CHEMIN_DB
from core.base import horodatage, normaliser
from core.sources import est_hote_officiel

# Taux de couverture minimal du parseur d'articles. En dessous, l'import est
# refusé : un parseur qui rate un quart des articles produirait un corpus
# silencieusement troué.
COUVERTURE_MINIMALE = 0.85

SCHEMA_CORPUS = """
CREATE TABLE IF NOT EXISTS documents (
    doc_id            TEXT PRIMARY KEY,
    ref_id            TEXT REFERENCES references_juridiques(ref_id),
    titre             TEXT NOT NULL CHECK(length(trim(titre)) > 0),
    type_texte        TEXT NOT NULL CHECK(length(trim(type_texte)) > 0),
    numero_texte      TEXT,
    date_texte        TEXT,
    domaine           TEXT NOT NULL CHECK(length(trim(domaine)) > 0),
    autorite          TEXT NOT NULL DEFAULT '',
    url_source        TEXT NOT NULL CHECK(url_source LIKE 'http%'),
    hote_officiel     INTEGER NOT NULL CHECK(hote_officiel IN (0,1)),
    chemin_local      TEXT NOT NULL,
    sha256            TEXT NOT NULL CHECK(sha256 LIKE 'sha256:%'),
    octets            INTEGER NOT NULL CHECK(octets > 0),
    pages             INTEGER NOT NULL CHECK(pages > 0),
    calque_texte      INTEGER NOT NULL CHECK(calque_texte IN (0,1)),
    fichier_texte     TEXT,
    sha256_texte      TEXT,
    licence_conditions TEXT NOT NULL CHECK(length(trim(licence_conditions)) > 0),
    note_qualite      TEXT,
    date_collecte     TEXT NOT NULL,
    cree_le           TEXT NOT NULL,
    -- Champs ajoutés en phase 3 (migration additive sur les bases existantes)
    methode_extraction TEXT NOT NULL DEFAULT 'AUCUNE',
    fichier_ocr       TEXT,
    sha256_ocr        TEXT,
    recoupe_avec      TEXT,
    qualite_ocr       REAL
);

CREATE TABLE IF NOT EXISTS articles_corpus (
    article_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_id         TEXT NOT NULL REFERENCES references_juridiques(ref_id),
    doc_id         TEXT NOT NULL REFERENCES documents(doc_id),
    numero         TEXT NOT NULL CHECK(length(trim(numero)) > 0),
    texte          TEXT NOT NULL CHECK(length(trim(texte)) > 0),
    sha256_article TEXT NOT NULL CHECK(sha256_article LIKE 'sha256:%'),
    -- Provenance du texte de CET article : jamais confondue entre une lecture
    -- de document (calque texte) et une reconnaissance automatique (OCR).
    origine_texte  TEXT NOT NULL DEFAULT 'CALQUE_TEXTE',
    confiance_ocr  REAL,
    recoupe        INTEGER NOT NULL DEFAULT 0,
    doc_reference  TEXT,
    UNIQUE (doc_id, numero)
);

CREATE INDEX IF NOT EXISTS idx_articles_ref ON articles_corpus(ref_id);
CREATE INDEX IF NOT EXISTS idx_documents_domaine ON documents(domaine);
"""

# Un en-tête d'article. Deux formes réelles dans le corpus :
#   « Article 552. La présente loi… »      (texte suivi d'une ponctuation)
#   « Article Premier » / « Article 4 »     (titre seul, article en dessous)
# Le préfixe numérique optionnel absorbe les numéros de page collés au titre par
# l'extraction PDF (cas réel : « 72Article 1. »). Le nombre doit être suivi soit
# d'une ponctuation, soit d'une fin de ligne — sans quoi une phrase du type
# « l'article 5 du code » en début de ligne créerait un faux article.
MOTIF_ARTICLE = re.compile(
    r"(?m)^[ \t]*(?:\d{1,3}[ \t]*)?(?:Article|ARTICLE|Art\.)[ \t]+"
    r"(\d{1,4}(?:[ \t]*(?:bis|ter|quater|quinquies))?|premier|premiere|unique)"
    r"[ \t]*(?:[\.\-:)]|$)",
    re.IGNORECASE,
)

# Formes littérales : la loi 98-750 écrit « Article Premier », pas « Article 1 ».
NUMEROS_LITTERAUX = {
    "premier": "1",
    "premiere": "1",
    "1er": "1",
}


def connexion(chemin=None):
    chemin = str(chemin or CHEMIN_DB)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialiser(chemin=None):
    with connexion(chemin) as conn:
        conn.executescript(SCHEMA_CORPUS)
    migrer(chemin)
    return str(chemin or CHEMIN_DB)


# Colonnes ajoutées après coup. `CREATE TABLE IF NOT EXISTS` ne les ajoute pas à
# une table déjà créée : il faut une migration explicite, additive, idempotente.
COLONNES_DOCUMENTS = (
    ("methode_extraction", "TEXT NOT NULL DEFAULT 'AUCUNE'"),
    ("fichier_ocr", "TEXT"),
    ("sha256_ocr", "TEXT"),
    ("recoupe_avec", "TEXT"),
    ("qualite_ocr", "REAL"),
    # Deux faits distincts, deux colonnes : `note_qualite` décrit l'état
    # d'EXTRACTION (le collecteur l'écrit), `note_ocr` décrit ce qu'a donné la
    # TENTATIVE d'OCR (le lecteur OCR l'écrit). Les mettre dans la même colonne
    # faisait qu'une re-collecte effaçait la trace d'un refus d'OCR — vérifié en
    # conditions réelles.
    ("note_ocr", "TEXT"),
    # 1 = les articles de ce document sont attribuables au texte annoncé ;
    # 0 = ils ne le sont PAS (OCR ayant entremêlé plusieurs actes d'un même
    # Journal officiel, par exemple). Un article non citable est conservé pour
    # l'audit, jamais servi dans une réponse.
    ("articles_fiables", "INTEGER NOT NULL DEFAULT 1"),
)
COLONNES_ARTICLES = (
    ("origine_texte", "TEXT NOT NULL DEFAULT 'CALQUE_TEXTE'"),
    ("confiance_ocr", "REAL"),
    ("recoupe", "INTEGER NOT NULL DEFAULT 0"),
    ("doc_reference", "TEXT"),
)


def migrer(chemin=None):
    """Ajoute les colonnes manquantes et rattrape les lignes anciennes.

    Idempotent : appelable à chaque `initialiser()`. Ne supprime jamais rien.
    Retourne la liste des colonnes réellement ajoutées.
    """
    ajouts = []
    with connexion(chemin) as conn:
        for table, colonnes in (("documents", COLONNES_DOCUMENTS),
                                ("articles_corpus", COLONNES_ARTICLES)):
            existantes = {ligne[1] for ligne in
                          conn.execute("PRAGMA table_info(%s)" % table).fetchall()}
            for nom, definition in colonnes:
                if nom not in existantes:
                    conn.execute("ALTER TABLE %s ADD COLUMN %s %s" % (table, nom, definition))
                    ajouts.append("%s.%s" % (table, nom))
        # Rattrapage des documents antérieurs à la colonne : un document qui
        # porte un calque texte a été extrait par lecture, pas par OCR.
        conn.execute(
            "UPDATE documents SET methode_extraction = 'CALQUE_TEXTE'"
            " WHERE calque_texte = 1 AND methode_extraction = 'AUCUNE'")
    return ajouts


def empreinte_fichier(chemin):
    """SHA-256 d'un fichier réel. Lève si le fichier n'existe pas."""
    if not os.path.isfile(chemin):
        raise FileNotFoundError("document introuvable : %s" % chemin)
    h = hashlib.sha256()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return "sha256:" + h.hexdigest()


def empreinte_texte(texte):
    return "sha256:" + hashlib.sha256((texte or "").encode("utf-8")).hexdigest()


def identifiant_document(url_source, sha256):
    """Clé déterministe : même URL + mêmes octets ⇒ même document."""
    base = "%s|%s" % (url_source, sha256)
    return "DOC-" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:12].upper()


# --------------------------------------------------------------------------
# Extraction d'articles
# --------------------------------------------------------------------------
def _normaliser_numero(brut):
    """« Premier » -> « 1 ». Les autres formes restent telles quelles."""
    return NUMEROS_LITTERAUX.get(brut, brut)


ARTEFACTS_EDITEURS = (
    # Pieds de page d'une reproduction tierce : ils tombent DANS le corps des
    # articles. Un texte publie par une autorite peut etre une REPRODUCTION d'un
    # document edite ailleurs ; ce n'est pas pour autant le texte officiel, et
    # cela doit rester visible dans les metadonnees du document.
    re.compile(r"(?im)^\s*Par\s+Laws\.Africa et contributeurs\..*$"),
    re.compile(r"(?im)^\s*www\.laws\.africa\s*$"),
    re.compile(r"(?im)^\s*info@laws\.africa\s*$"),
    re.compile(r"(?im)^\s*FRBR URI:.*$"),
    re.compile(r"(?im)^\s*Cette copie PDF est sous licence Creative Commons.*$"),
    re.compile(r"(?im)^\s*Il n'existe aucun droit d'auteur sur le contenu législatif.*$"),
)


def retirer_artefacts_editeurs(texte):
    """Retire les mentions d'editeur tiers et dit ce qui a ete retire.

    Renvoie (texte_nettoye, [lignes retirees]) : une suppression silencieuse
    serait un effacement de provenance, donc une perte d'information.
    """
    if not texte:
        return texte, []
    retirees = []
    for motif in ARTEFACTS_EDITEURS:
        for correspondance in motif.findall(texte):
            retirees.append(" ".join(correspondance.split())[:120])
        texte = motif.sub("", texte)
    return texte, retirees


def textes_contaminants(texte):
    """Marques d'origine tierce reperables dans un texte (controle d'integrite).

    Sert a REFUSER le statut VERIFIE a un document qui n'est qu'une
    reproduction : le contenu peut etre exact, la source n'est pas officielle.
    """
    if not texte:
        return []
    trouves = []
    for marque in ("laws.africa", "creative commons", "ivoire-juriste", "lexterra",
                   "droitci.info", "scribd"):
        if re.search(re.escape(marque), texte, re.I):
            trouves.append(marque)
    return trouves


def extraire_articles(texte):
    """Découpe un texte législatif en articles. Retourne {numero: texte}.

    Quand un même numéro apparaît plusieurs fois (en-têtes de page, renvois),
    c'est le CHUNK LE PLUS LONG qui est conservé : c'est celui qui porte
    réellement la disposition.

    Une forme littérale (« Article Premier ») ne remplace JAMAIS un article
    numéroté : si le même numéro existe aussi sous forme chiffrée, c'est la
    forme chiffrée qui est retenue. Sans cette règle, un « Article Premier »
    cité dans le corps du texte pourrait écraser le véritable article 1.
    """
    trouves = {}
    chiffres = set()
    # Les marqueurs de page du texte OCR (« --- PAGE 3 --- ») ne sont pas du
    # contenu : les laisser ferait entrer un artefact d'outil dans le texte d'un
    # article, donc dans une citation potentielle.
    texte = re.sub(r"(?m)^--- PAGE \d+ ---[ \t]*\n?", "", texte or "")
    # Mentions d'editeur tiers : elles tombent dans le corps des articles et se
    # retrouveraient dans une citation. Retirees du texte ici, jamais cachees
    # ailleurs : la provenance reste inscrite dans les metadonnees du document.
    texte, _ = retirer_artefacts_editeurs(texte)
    for m in MOTIF_ARTICLE.finditer(texte):
        brut = re.sub(r"[ \t]+", " ", m.group(1)).strip().lower()
        numero = _normaliser_numero(brut)
        if re.match(r"^\d", brut):
            chiffres.add(numero)
        suivant = MOTIF_ARTICLE.search(texte, m.end())
        corps = texte[m.end(): suivant.start() if suivant else len(texte)].strip()
        # La ponctuation de tête vient de la mise en page : l'OCR rejette
        # parfois le point ou la puce au début de la ligne suivante
        # (« Article 115 » puis « . L'arrêté d'approbation… »). Elle n'appartient
        # pas à la disposition — on la retire, sans jamais toucher au contenu.
        corps = re.sub(r"^[\s\.\):;•·]+", "", corps)
        corps = re.sub(r"\n{3,}", "\n\n", corps)
        if not corps:
            continue
        precedent = trouves.get(numero)
        if precedent is None or len(corps) > len(precedent[0]):
            trouves[numero] = (corps, brut)

    for numero, (_, brut) in list(trouves.items()):
        if not re.match(r"^\d", brut) and numero in chiffres:
            del trouves[numero]

    return {numero: corps for numero, (corps, _) in trouves.items()}


def numeros_simples(articles):
    """Numéros purement numériques, sans bis/ter, triés."""
    nums = []
    for numero in articles:
        m = re.match(r"^(\d+)", numero)
        if m and numero.strip().isdigit():
            nums.append(int(m.group(1)))
    return sorted(nums)


def taux_couverture(articles):
    """(taux, maximum) : part des numéros 1..max effectivement présents."""
    nums = numeros_simples(articles)
    if not nums:
        return 0.0, 0
    maximum = max(nums)
    presents = {n for n in nums if 1 <= n <= maximum}
    return len(presents) / float(maximum), maximum


# --------------------------------------------------------------------------
# Import
# --------------------------------------------------------------------------
def importer_document(
    ref_id,
    titre,
    type_texte,
    numero_texte,
    date_texte,
    domaine,
    autorite,
    url_source,
    chemin_local,
    licence_conditions,
    pages,
    calque_texte,
    fichier_texte=None,
    sha256_declare=None,
    note_qualite=None,
    date_collecte=None,
    methode_extraction=None,
    actualiser=False,
    chemin=None,
):
    """Enregistre un document officiel téléchargé, avec sa preuve.

    Lève ValueError si une condition n'est pas remplie ; l'empreinte est
    RECALCULÉE sur le fichier, jamais crue sur parole.
    """
    for champ, valeur in (("titre", titre), ("type_texte", type_texte),
                          ("domaine", domaine), ("url_source", url_source),
                          ("licence_conditions", licence_conditions)):
        if not (valeur and str(valeur).strip()):
            raise ValueError("champ obligatoire manquant : %s" % champ)
    if not int(pages or 0) > 0:
        raise ValueError("le nombre de pages doit être > 0 (reçu %r)" % (pages,))
    if not est_hote_officiel(url_source):
        raise ValueError(
            "source non officielle refusée : %r n'appartient pas au périmètre "
            "(registre des sources ou *.gouv.ci)" % (url_source,))

    sha_reel = empreinte_fichier(chemin_local)
    if sha256_declare and sha256_declare != sha_reel:
        raise ValueError(
            "empreinte incohérente pour %s : déclarée %s, recalculée %s"
            % (chemin_local, sha256_declare, sha_reel))

    if calque_texte and not fichier_texte:
        raise ValueError("calque_texte=1 exige le chemin du texte extrait")
    sha_texte = None
    if fichier_texte:
        if not os.path.isfile(fichier_texte):
            raise FileNotFoundError("texte extrait introuvable : %s" % fichier_texte)
        sha_texte = empreinte_fichier(fichier_texte)

    doc_id = identifiant_document(url_source, sha_reel)
    maintenant = horodatage()
    date_collecte = date_collecte or datetime.date.today().isoformat()

    with connexion(chemin) as conn:
        existe = conn.execute("SELECT doc_id FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
        if existe:
            if not actualiser:
                return doc_id
            # `actualiser=True` : une réextraction du même document (empreinte
            # identique) fait autorité sur ses métadonnées descriptives. Sans
            # cela, une correction de lecture (nettoyage des artefacts d'éditeur,
            # découpage en articles jugé non fiable) resterait invisible dans la
            # base alors qu'elle est appliquée au texte indexé : deux vérités
            # contradictoires dans le même corpus.
            conn.execute(
                "UPDATE documents SET titre = ?, type_texte = ?, numero_texte = ?,"
                " date_texte = ?, domaine = ?, autorite = ?, licence_conditions = ?,"
                " pages = ?, calque_texte = ?, fichier_texte = ?, sha256_texte = ?,"
                " note_qualite = ?, methode_extraction = ? WHERE doc_id = ?",
                (titre, type_texte, numero_texte, date_texte, domaine, autorite,
                 licence_conditions, int(pages), 1 if calque_texte else 0, fichier_texte,
                 sha_texte, note_qualite, methode_extraction or
                 ("CALQUE_TEXTE" if calque_texte else "AUCUNE"), doc_id))
            return doc_id
        conn.execute(
            """
            INSERT INTO documents (
                doc_id, ref_id, titre, type_texte, numero_texte, date_texte, domaine,
                autorite, url_source, hote_officiel, chemin_local, sha256, octets, pages,
                calque_texte, fichier_texte, sha256_texte, licence_conditions,
                note_qualite, date_collecte, cree_le, methode_extraction
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (doc_id, ref_id, titre, type_texte, numero_texte, date_texte, domaine,
             autorite, url_source, 1, os.path.abspath(chemin_local), sha_reel,
             os.path.getsize(chemin_local), pages, 1 if calque_texte else 0,
             os.path.abspath(fichier_texte) if fichier_texte else None, sha_texte,
             licence_conditions, note_qualite, date_collecte, maintenant,
             methode_extraction or ("CALQUE_TEXTE" if calque_texte else "AUCUNE")),
        )
    return doc_id


def enregistrer_articles(ref_id, doc_id, articles, origine_texte="CALQUE_TEXTE",
                         confiance_ocr=None, recoupe=False, doc_reference=None,
                         remplacer=False, chemin=None):
    """Indexe les articles d'un document. Refuse un corpus troué.

    `origine_texte` : `CALQUE_TEXTE` (lecture du document) ou `OCR_AUTO`
    (reconnaissance automatique). `confiance_ocr` : dict {numero: similarité}
    mesurée pour les articles OCR. `recoupe` : le texte a-t-il été comparé à une
    autre copie officielle ? Ces informations voyagent avec chaque article : un
    texte reconnu automatiquement ne peut plus être pris pour une lecture.

    `remplacer=True` met à jour le texte des articles déjà présents (UPSERT) —
    jamais de suppression : réindexer un texte OCR ne doit pas laisser des
    lignes fantômes, mais ne doit pas non plus effacer des lignes d'autres
    documents.
    """
    from core.ocr import ORIGINES
    if origine_texte not in ORIGINES:
        raise ValueError("origine de texte inconnue : %r" % (origine_texte,))
    if not articles:
        raise ValueError("aucun article à enregistrer pour %s" % doc_id)
    taux, maximum = taux_couverture(articles)
    if taux < COUVERTURE_MINIMALE:
        raise ValueError(
            "couverture insuffisante pour %s : %.0f%% des articles 1..%d (minimum %.0f%%)"
            % (doc_id, 100 * taux, maximum, 100 * COUVERTURE_MINIMALE))
    confiance_ocr = confiance_ocr or {}
    lignes = [(ref_id, doc_id, numero, corps, empreinte_texte(corps), origine_texte,
               confiance_ocr.get(numero), 1 if recoupe else 0, doc_reference)
              for numero, corps in sorted(articles.items())]

    colonnes = ("ref_id, doc_id, numero, texte, sha256_article, origine_texte,"
                " confiance_ocr, recoupe, doc_reference")
    marques = "?,?,?,?,?,?,?,?,?"
    if remplacer:
        requete = ("INSERT INTO articles_corpus (%s) VALUES (%s)"
                   " ON CONFLICT(doc_id, numero) DO UPDATE SET texte = excluded.texte,"
                   " sha256_article = excluded.sha256_article, ref_id = excluded.ref_id,"
                   " origine_texte = excluded.origine_texte,"
                   " confiance_ocr = excluded.confiance_ocr,"
                   " recoupe = excluded.recoupe,"
                   " doc_reference = excluded.doc_reference" % (colonnes, marques))
    else:
        requete = "INSERT OR IGNORE INTO articles_corpus (%s) VALUES (%s)" % (colonnes, marques)

    with connexion(chemin) as conn:
        conn.executemany(requete, lignes)
    return {"doc_id": doc_id, "articles_indexes": len(lignes), "origine_texte": origine_texte,
            "couverture": round(taux, 4), "article_max": maximum,
            "recoupe": bool(recoupe), "remplacement": bool(remplacer)}


# --------------------------------------------------------------------------
# Lecture
# --------------------------------------------------------------------------
COLONNES_FICHIERS = ("chemin_local", "fichier_texte", "fichier_ocr")


def localiser_fichier(chemin_enregistre):
    """Chemin utilisable sur CETTE machine pour un fichier enregistré en base.

    La base conserve le chemin absolu de la machine de collecte
    (`/Users/mac/mon_recours_ci/KNOWLEDGE/...`). Sur un autre poste ou en CI,
    ce chemin n'existe pas alors que le fichier est bien dans le dépôt : on le
    retrouve par sa partie relative à `KNOWLEDGE/`. Si aucun des deux n'existe,
    le chemin enregistré est rendu tel quel — l'absence reste visible, rien
    n'est inventé. La base n'est jamais modifiée par cette fonction.
    """
    if not chemin_enregistre or os.path.exists(chemin_enregistre):
        return chemin_enregistre
    texte = str(chemin_enregistre).replace("\\", "/")
    if "KNOWLEDGE/" in texte:
        candidat = os.path.join(str(config.KNOWLEDGE_DIR), texte.split("KNOWLEDGE/", 1)[1])
        if os.path.exists(candidat):
            return candidat
    return chemin_enregistre


def _localiser(document):
    if document:
        for colonne in COLONNES_FICHIERS:
            if colonne in document:
                document[colonne] = localiser_fichier(document[colonne])
    return document


def obtenir_document(doc_id, chemin=None):
    with connexion(chemin) as conn:
        ligne = conn.execute("SELECT * FROM documents WHERE doc_id = ?", (doc_id,)).fetchone()
    return _localiser(dict(ligne)) if ligne else None


def lister_documents(domaine=None, chemin=None):
    requete = "SELECT * FROM documents"
    params = []
    if domaine:
        requete += " WHERE domaine = ?"
        params.append(domaine)
    requete += " ORDER BY date_texte DESC"
    with connexion(chemin) as conn:
        return [_localiser(dict(r)) for r in conn.execute(requete, params).fetchall()]


def obtenir_article(doc_id, numero, chemin=None):
    with connexion(chemin) as conn:
        ligne = conn.execute(
            "SELECT * FROM articles_corpus WHERE doc_id = ? AND numero = ?",
            (doc_id, str(numero).strip().lower())).fetchone()
    return dict(ligne) if ligne else None


def obtenir_article_par_reference(ref_id, numero, chemin=None):
    """Texte d'un article indexé, ou None.

    Un article peut exister et ne PAS être citable : si le document dont il
    provient a été marqué `articles_fiables = 0` (par exemple un Journal
    officiel dont l'OCR a entremêlé plusieurs actes sur la même page), le
    renvoyer laisserait croire qu'il dit ce qu'il ne dit pas. On renvoie None,
    et `raison_non_citable` dit pourquoi.
    """
    with connexion(chemin) as conn:
        ligne = conn.execute(
            "SELECT a.*, d.articles_fiables, d.note_ocr, d.note_qualite"
            " FROM articles_corpus a JOIN documents d ON d.doc_id = a.doc_id"
            " WHERE a.ref_id = ? AND a.numero = ?",
            (ref_id, str(numero).strip().lower())).fetchone()
    if ligne is None:
        return None
    article = dict(ligne)
    if not article.get("articles_fiables", 1):
        return None
    return article


def _nombres(texte):
    """Nombres d'un texte, espaces de milliers neutralisées (« 250 000 » = « 250000 »).

    Même logique que `core.analyse._nombres` ; la duplication est assumée pour
    ne pas faire dépendre ce module d'un utilitaire privé d'un autre.
    """
    if not texte:
        return set()
    t = re.sub(r"(?<=\d)[\s\u00a0\u202f](?=\d)", "", str(texte))
    return set(re.findall(r"\d+(?:[.,]\d+)?", t))


def verifier_regle_article(ref_id, numero, enonce, chemin=None):
    """Contrôle qu'un énoncé reste soutenu par LE TEXTE DE CET ARTICLE.

    Complète `core.analyse.NOMBRE_NON_SOUTENU`, dont le pouvoir discriminant
    baisse quand la référence porte le texte intégral d'une loi : un petit
    nombre (« 3 ») finit par apparaître quelque part dans 290 000 caractères.
    Ici la comparaison se fait contre l'article cité seulement, ce qui rend le
    contrôle réellement contraignant.
    """
    article = obtenir_article_par_reference(ref_id, numero, chemin=chemin)
    if article is None:
        return {"ok": False, "numero": numero, "raison": "ARTICLE_INCONNU",
                "nombres_non_soutenus": [], "article_sha256": None}
    soutenus = _nombres(article["texte"])
    non_soutenus = sorted(_nombres(enonce) - soutenus)
    return {
        "ok": not non_soutenus,
        "numero": numero,
        "raison": "SOUTENU" if not non_soutenus else "NOMBRES_NON_SOUTENUS_PAR_L_ARTICLE",
        "nombres_non_soutenus": non_soutenus,
        "article_sha256": article["sha256_article"],
    }


def citations_pour_reference(ref_id, chemin=None):
    """Liste les articles indexés d'une référence, avec leur empreinte."""
    with connexion(chemin) as conn:
        lignes = conn.execute(
            "SELECT numero, sha256_article, length(texte) AS taille"
            " FROM articles_corpus WHERE ref_id = ? ORDER BY CAST(numero AS INTEGER)",
            (ref_id,)).fetchall()
    return [dict(l) for l in lignes]


MOTS_VIDES_RECHERCHE = frozenset((
    "alors", "apres", "auquel", "aussi", "autre", "avec", "avoir", "celui", "cette", "ceux",
    "comme", "dans", "depuis", "donc", "dont", "elle", "elles", "encore", "enfin", "entre",
    "etait", "etant", "etre", "faire", "fait", "faut", "leurs", "lorsque", "mais", "meme",
    "moins", "mon", "nous", "parce", "pour", "pourquoi", "quand", "quel", "quelle", "sans",
    "selon", "sous", "sont", "suis", "tous", "toute", "toutes", "tout", "tres", "trop",
    "veut", "veux", "vouloir", "vous", "peut", "peuvent", "plus", "chez", "vers", "cela",
))

# Pont lexical CITOYEN -> VOCABULAIRE DE LA LOI. Ce n'est PAS une règle de droit,
# et cela ne dit rien de l'applicabilité d'un texte : c'est une table de
# recherche, mesurée sur le corpus livré.
#   * « caution » : le citoyen vise le dépôt de garantie du logement ; dans le
#     Code, le mot « caution » seul renvoie au cautionnement (un autre contrat).
#   * « augmenter » : le Code dit « révisé à la hausse », jamais « augmenté ».
#   * « logement » : le Code écrit « immeuble ou local » pour la reprise.
SYNONYMES_RECHERCHE = {
    "caution": ("depot", "garantie"),
    "cautionner": ("depot", "garantie"),
    "augmenter": ("revision", "hausse"),
    "augmentation": ("revision", "hausse"),
    "hausse": ("revision",),
    "reprendre": ("reprise",),
}


def _prefixe_recherche(mot):
    """Fragment de tête de 4 à 6 lettres.

    « expulser » et « expulsion » partagent « expul » ; « loyers » et « loyer »
    partagent « loye ». Ce n'est pas une analyse morphologique : c'est un pont
    assez large pour retrouver, assez court pour ne pas tout confondre.
    """
    return mot[:min(6, max(4, len(mot) - 3))]


def _fragments_de_requete(mots_cles):
    bruts = [normaliser(t) for t in re.split(r"[\s,;'’]+", mots_cles or "") if t]
    vocabulaire, fragments = [], []
    for mot in bruts:
        if len(mot) < 4 or mot in MOTS_VIDES_RECHERCHE:
            continue
        vocabulaire.append(mot)
        for variante in (mot,) + SYNONYMES_RECHERCHE.get(mot, ()):
            fragment = _prefixe_recherche(normaliser(variante))
            if fragment and fragment not in fragments:
                fragments.append(fragment)
    return vocabulaire, fragments


def chercher_articles(mots_cles, domaine=None, limite=25, chemin=None):
    """Recherche d'articles pour une question posée en langage courant.

    Score = somme des IDF des fragments reconnus (un fragment rare qui tombe
    pèse plus qu'un fragment banal). Deux limites assumées, mesurées :

      * la loi n'emploie pas toujours le mot du citoyen (« révisé » plutôt
        qu'« augmenter ») — d'où SYNONYMES_RECHERCHE, table de vocabulaire ;
      * un même article peut exister dans plusieurs documents (deux exemplaires
        officiels du même code, plus sa version OCR). Les doublons sont résolus
        en gardant la LECTURE DE DOCUMENT plutôt que la reconnaissance
        automatique, et le nombre d'exemplaires est signalé.

    Classement : mesuré sur 7 questions réelles, quatre variantes ont été
    comparées à l'IDF pur (pénalité de longueur 0,3 / 0,5 / forte, et bonus de
    couverture). Aucune ne DOMINE : toutes font remonter les articles courts
    (le domaine public passe de la 4e à la 1re place) mais font DESCENDRE les
    articles longs et décisifs (expropriation : 4e → 9e ; caution : 22e → 27e).
    Le pire rang reste identique ou meilleur avec l'IDF pur. Ne pas « améliorer »
    ce classement sans mesurer : le score total est un mauvais critère, le rang
    du pire cas en est un bon.
    """
    _, fragments = _fragments_de_requete(mots_cles)
    if not fragments:
        return []
    requete = ("SELECT a.*, d.titre, d.numero_texte, d.date_texte, d.domaine, d.doc_id,"
               " d.url_source, d.sha256, r.etat_verification"
               " FROM articles_corpus a"
               " JOIN documents d ON d.doc_id = a.doc_id"
               " JOIN references_juridiques r ON r.ref_id = a.ref_id")
    params = []
    # Un article non citable ne doit jamais remonter dans une recherche : c'est
    # ainsi qu'il finirait dans une réponse.
    requete += " WHERE d.articles_fiables = 1"
    if domaine:
        requete += " AND d.domaine = ?"
        params.append(domaine)
    with connexion(chemin) as conn:
        lignes = [dict(r) for r in conn.execute(requete, params).fetchall()]
    textes = [(ligne, normaliser(ligne.get("texte") or "")) for ligne in lignes]
    total = len(textes)
    if not total:
        return []
    frequence = {f: sum(1 for _, texte in textes if f in texte) for f in fragments}
    resultats = {}
    for ligne, texte in textes:
        presents = [f for f in fragments if f in texte]
        if not presents:
            continue
        ligne["score"] = round(sum(math.log(1.0 + total / max(1, frequence[f]))
                                   for f in presents), 4)
        ligne["termes_reconnus"] = presents
        # Un même article peut exister dans plusieurs exemplaires officiels du
        # même texte (dont sa version OCR) : la clé est le TEXTE + le numéro,
        # pas la référence, sinon le citoyen voit trois fois le même article.
        cle = (ligne.get("numero_texte") or ligne.get("ref_id"), str(ligne.get("numero")))
        precedent = resultats.get(cle)
        if precedent is None:
            ligne["exemplaires"] = 1
            ligne["references_exemplaires"] = [ligne.get("ref_id")]
            resultats[cle] = ligne
        else:
            precedent["exemplaires"] += 1
            precedent["references_exemplaires"].append(ligne.get("ref_id"))
            if (precedent.get("origine_texte") != "CALQUE_TEXTE"
                    and ligne.get("origine_texte") == "CALQUE_TEXTE"):
                ligne["exemplaires"] = precedent["exemplaires"]
                ligne["references_exemplaires"] = precedent["references_exemplaires"]
                resultats[cle] = ligne
    return sorted(resultats.values(), key=lambda r: (-r["score"], r["doc_id"], str(r["numero"])))[:limite]


# --------------------------------------------------------------------------
# Contrôles
# --------------------------------------------------------------------------
def enregistrer_ocr_document(doc_id, fichier_ocr, recoupe_avec=None, qualite_ocr=None,
                             note=None, chemin=None):
    """Attache un texte OCR à un document SANS calque texte.

    Ne touche NI `calque_texte` (le PDF reste un scan), NI
    `texte_complet_present` de la référence (le texte n'est pas vérifié). Le
    document gagne seulement la mention de sa méthode d'extraction et
    l'empreinte du texte reconnu.
    """
    if not os.path.isfile(fichier_ocr):
        raise FileNotFoundError("texte OCR introuvable : %s" % fichier_ocr)
    sha_ocr = empreinte_fichier(fichier_ocr)
    with connexion(chemin) as conn:
        ligne = conn.execute("SELECT calque_texte FROM documents WHERE doc_id = ?",
                             (doc_id,)).fetchone()
        if ligne is None:
            raise KeyError("document inconnu : %r" % (doc_id,))
        conn.execute(
            "UPDATE documents SET methode_extraction = 'OCR_VISION_AUTO', fichier_ocr = ?,"
            " sha256_ocr = ?, recoupe_avec = ?, qualite_ocr = ?,"
            " note_ocr = COALESCE(?, note_ocr) WHERE doc_id = ?",
            (os.path.abspath(fichier_ocr), sha_ocr, recoupe_avec, qualite_ocr, note, doc_id))
    return {"doc_id": doc_id, "methode_extraction": "OCR_VISION_AUTO",
            "sha256_ocr": sha_ocr, "recoupe_avec": recoupe_avec,
            "qualite_ocr": qualite_ocr}


def noter_refus_ocr(doc_id, motif, fichier_ocr=None, chemin=None):
    """Enregistre qu'un OCR a été TENTÉ et REFUSÉ, avec son motif.

    Écrit dans `note_ocr`, PAS dans `note_qualite` : cette dernière appartient au
    collecteur, qui décrit l'état d'extraction. Les confondre faisait qu'une
    re-collecte du domaine effaçait la trace du refus et remettait « OCR
    requis » — la base se remettait à dire le contraire du rapport, vérifié en
    conditions réelles.

    `methode_extraction` n'est PAS touchée : aucun article n'ayant été obtenu, il
    serait faux d'y écrire `OCR_VISION_AUTO`.
    """
    fichier = os.path.abspath(fichier_ocr) if fichier_ocr and os.path.isfile(fichier_ocr) else None
    with connexion(chemin) as conn:
        if conn.execute("SELECT 1 FROM documents WHERE doc_id = ?", (doc_id,)).fetchone() is None:
            raise KeyError("document inconnu : %r" % (doc_id,))
        conn.execute(
            "UPDATE documents SET note_ocr = ?,"
            " fichier_ocr = COALESCE(?, fichier_ocr),"
            " sha256_ocr = COALESCE(?, sha256_ocr) WHERE doc_id = ?",
            (motif, fichier, empreinte_fichier(fichier) if fichier else None, doc_id))
    return {"doc_id": doc_id, "note_ocr": motif, "fichier_ocr": fichier}


def marquer_articles_non_citables(doc_id, motif, chemin=None):
    """Retire un document de la circulation citable, sans rien supprimer.

    Cas d'usage mesuré : les exemplaires du Journal officiel dont l'OCR a
    entremêlé plusieurs actes sur la même page. Les articles restent en base
    pour l'audit et la lecture humaine, mais `obtenir_article_par_reference` et
    `chercher_articles` les refusent — sinon ils finiraient dans une réponse.
    """
    with connexion(chemin) as conn:
        if conn.execute("SELECT 1 FROM documents WHERE doc_id = ?", (doc_id,)).fetchone() is None:
            raise KeyError("document inconnu : %r" % (doc_id,))
        conn.execute(
            "UPDATE documents SET articles_fiables = 0,"
            " note_ocr = CASE WHEN note_ocr IS NULL THEN ? ELSE note_ocr || ' | ' || ? END"
            " WHERE doc_id = ?", (motif, motif, doc_id))
    return {"doc_id": doc_id, "articles_fiables": 0, "motif": motif}


def verifier_citation_article(ref_id, numero, citation, chemin=None):
    """La citation est-elle présente dans le texte de CET article, tel qu'indexé ?

    Retourne (ok, details). Les détails portent la PROVENANCE : citer un texte
    reconnu automatiquement n'est pas la même chose que citer une lecture de
    document, et l'appelant doit pouvoir le dire.
    """
    article = obtenir_article_par_reference(ref_id, numero, chemin=chemin)
    if article is None:
        return False, {"raison": "ARTICLE_INCONNU", "ref_id": ref_id, "numero": numero}
    details = {
        "ref_id": ref_id,
        "numero": numero,
        "origine_texte": article.get("origine_texte"),
        "confiance_ocr": article.get("confiance_ocr"),
        "recoupe": bool(article.get("recoupe")),
        "sha256_article": article["sha256_article"],
    }
    if not normaliser(citation):
        details["raison"] = "CITATION_VIDE"
        return False, details
    if normaliser(citation) in normaliser(article["texte"]):
        details["raison"] = "CITATION_RETROUVEE"
        if details["origine_texte"] == "OCR_AUTO":
            details["avertissement"] = (
                "Texte obtenu par reconnaissance automatique (OCR) : la citation doit "
                "être présentée comme telle tant qu'elle n'a pas été relue manuellement."
            )
        return True, details
    details["raison"] = "CITATION_ABSENTE"
    return False, details


def articles_par_origine(chemin=None):
    """Compte les articles par provenance. Aucune catégorie n'est omise."""
    from core.ocr import ORIGINES
    with connexion(chemin) as conn:
        lignes = conn.execute(
            "SELECT origine_texte, COUNT(*), SUM(recoupe), AVG(confiance_ocr)"
            " FROM articles_corpus GROUP BY origine_texte").fetchall()
    compte = {o: {"articles": 0, "recoupes": 0, "confiance_moyenne": None} for o in ORIGINES}
    for origine, total, recoupes, confiance in lignes:
        compte[origine] = {"articles": total or 0, "recoupes": recoupes or 0,
                           "confiance_moyenne": round(confiance, 4) if confiance else None}
    return compte


def articles_dun_document(doc_id, chemin=None):
    with connexion(chemin) as conn:
        lignes = conn.execute(
            "SELECT numero, origine_texte, confiance_ocr, recoupe, sha256_article,"
            " length(texte) AS taille FROM articles_corpus WHERE doc_id = ?"
            " ORDER BY CAST(numero AS INTEGER)", (doc_id,)).fetchall()
    return [dict(l) for l in lignes]


def documents_sans_articles(chemin=None):
    """Documents sans aucun article indexé — donc sans texte exploitable."""
    with connexion(chemin) as conn:
        lignes = conn.execute(
            "SELECT d.doc_id, d.titre, d.calque_texte, d.methode_extraction, d.note_qualite"
            " FROM documents d LEFT JOIN articles_corpus a ON a.doc_id = d.doc_id"
            " WHERE a.article_id IS NULL ORDER BY d.doc_id").fetchall()
    return [dict(l) for l in lignes]


def articles_hors_extraction(doc_id, articles_attendus, chemin=None):
    """Articles présents en base mais absents de l'extraction courante.

    Un changement de parseur peut laisser des lignes calculées par une version
    antérieure. Elles ne sont PAS supprimées (la base ne perd rien), mais elles
    doivent être NOMMÉES : une ligne fantôme non signalée se lit comme un
    article légitime.
    """
    with connexion(chemin) as conn:
        en_base = {ligne[0] for ligne in conn.execute(
            "SELECT numero FROM articles_corpus WHERE doc_id = ?", (doc_id,)).fetchall()}

    def cle(numero):
        m = re.match(r"(\d+)", str(numero))
        return (int(m.group(1)), str(numero)) if m else (999999, str(numero))

    return sorted(en_base - set(articles_attendus), key=cle)


MOTS_VIDES = frozenset((
    "alors", "apres", "aussi", "autre", "avec", "avoir", "cette", "comme", "dans", "depuis",
    "donc", "elle", "elles", "entre", "etre", "leur", "leurs", "mais", "meme", "nous", "parce",
    "pour", "peut", "quand", "sans", "selon", "sous", "sont", "suivant", "toute", "toutes",
    "tout", "vers", "vous", "cela", "celui", "dont", "ainsi", "encore", "moins", "plus",
    "notamment", "toutefois", "toutefois", "lorsque", "auquel", "laquelle", "lesquels",
))

SEUIL_COUVERTURE_LEXICALE = 0.60


def verifier_enonce_contre_article(ref_id, numero, enonce, chemin=None):
    """Mots de l'énoncé absents du texte de l'article cité.

    Contrôle LEXICAL mécanique : il attrape l'ajout d'une notion que l'article
    ne porte pas (parler d'« indemnité » sur un article qui n'en parle jamais).
    Il ne juge pas le sens — d'où un seuil, et non une exigence d'exhaustivité :
    une paraphrase fidèle emploie des mots qui ne sont pas ceux du texte.
    """
    article = obtenir_article_par_reference(ref_id, numero, chemin=chemin)
    if article is None:
        return {"ok": False, "raison": "ARTICLE_INCONNU", "mots_absents": [],
                "part_couverte": 0.0}
    texte_article = normaliser(article["texte"])
    mots = [m for m in re.findall(r"[a-z0-9']{4,}", normaliser(enonce))
            if m not in MOTS_VIDES]
    if not mots:
        return {"ok": False, "raison": "ENONCE_VIDE", "mots_absents": [], "part_couverte": 0.0}
    absents = sorted({m for m in mots if m not in texte_article})
    couverts = len(set(mots)) - len(absents)
    part = couverts / float(len(set(mots)))
    return {
        "ok": part >= SEUIL_COUVERTURE_LEXICALE,
        "raison": "SOUTENU" if part >= SEUIL_COUVERTURE_LEXICALE else "NOTIONS_HORS_ARTICLE",
        "mots_absents": absents[:20],
        "part_couverte": round(part, 4),
        "origine_texte": article.get("origine_texte"),
    }


def verifier_provenance_analyse(analyse, chemin=None):
    """Règles appuyées sur un texte OCR non recoupé, sans incertitude déclarée.

    Un texte obtenu par reconnaissance automatique n'est pas une lecture de
    document. Quand une règle s'appuie sur un article OCR qui n'a pas été
    recoupé avec une autre copie officielle, l'analyse DOIT porter une
    incertitude qui nomme la référence — sinon la provenance disparaît et le
    lecteur croit à une lecture.
    """
    refs_incertaines = {i.get("ref_id") for i in analyse.get("incertitudes", [])}
    violations = []
    for regle in analyse.get("regles", []):
        ref_id = regle.get("ref_id")
        if not ref_id:
            continue
        m = re.search(r"(\d{1,4}(?:\s*(?:bis|ter|quater))?)", str(regle.get("articles") or ""))
        if not m:
            continue
        numero = m.group(1).strip().lower()
        article = obtenir_article_par_reference(ref_id, numero, chemin=chemin)
        if article is None:
            continue
        if article["origine_texte"] == "OCR_AUTO" and not article["recoupe"]:
            if ref_id not in refs_incertaines:
                violations.append({
                    "code": "PROVENANCE_OCR_NON_DECLAREE",
                    "libelle": ("Règle appuyée sur un texte obtenu par OCR non recoupé, "
                                "sans incertitude déclarée."),
                    "detail": "%s article %s (origine %s, confiance %s)"
                              % (ref_id, numero, article["origine_texte"],
                                 article["confiance_ocr"]),
                })
    return violations


VARIABLE_PDF_NON_DISTRIBUES = "MONRECOURS_PDF_NON_DISTRIBUES"


def pdf_non_distribues_toleres():
    """Mode explicite pour un dépôt cloné SANS les PDF officiels.

    Les PDF ne sont pas versionnés (droit de redistribution non établi, voir
    .gitignore). Sur la machine de collecte, un PDF absent est un ÉCART : ce
    mode est désactivé par défaut. En CI ou sur un clone, la variable
    MONRECOURS_PDF_NON_DISTRIBUES=1 permet de vérifier ce qui EST distribué
    (les textes extraits, sur lesquels reposent les citations) sans faire
    passer l'absence d'un PDF pour une altération — ni pour une conformité.
    """
    return os.environ.get(VARIABLE_PDF_NON_DISTRIBUES, "") == "1"


def pdf_absent_et_tolere(document):
    return pdf_non_distribues_toleres() and not os.path.isfile(document.get("chemin_local") or "")


def _verifier_texte_distribue(document):
    """Empreintes des textes extraits (calque ou OCR) d'un document sans PDF."""
    controles = []
    for colonne_fichier, colonne_sha in (("fichier_texte", "sha256_texte"), ("fichier_ocr", "sha256_ocr")):
        fichier, attendu = document.get(colonne_fichier), document.get(colonne_sha)
        if not fichier or not attendu:
            continue
        if not os.path.isfile(fichier):
            controles.append({"fichier": colonne_fichier, "etat": "absent"})
            continue
        reel = empreinte_fichier(fichier)
        controles.append({"fichier": colonne_fichier,
                          "etat": "conforme" if reel == attendu else "altere",
                          "attendu": attendu, "reel": reel})
    return controles


def verifier_integrite(chemin=None):
    """Recalcule les empreintes sur disque. C'est la preuve que rien n'a dérivé."""
    conformes, absents, alteres, non_distribues = [], [], [], []
    tolere = pdf_non_distribues_toleres()
    documents = lister_documents(chemin=chemin)
    for document in documents:
        chemin_pdf = document["chemin_local"]
        try:
            sha = empreinte_fichier(chemin_pdf)
        except FileNotFoundError:
            if not tolere:
                absents.append({"doc_id": document["doc_id"], "chemin": chemin_pdf})
                continue
            textes = _verifier_texte_distribue(document)
            entree = {"doc_id": document["doc_id"], "textes_verifies": textes}
            if any(t["etat"] != "conforme" for t in textes):
                alteres.append(dict(entree, motif="texte extrait absent ou altéré"))
            else:
                non_distribues.append(entree)
            continue
        if sha != document["sha256"]:
            alteres.append({"doc_id": document["doc_id"], "attendu": document["sha256"],
                            "reel": sha, "chemin": chemin_pdf})
        else:
            conformes.append({"doc_id": document["doc_id"], "sha256": sha,
                              "octets": document["octets"]})
    return {
        "horodatage": horodatage(),
        "nb_documents": len(documents),
        "conformes": conformes,
        "alteres": alteres,
        "absents": absents,
        "pdf_non_distribues": non_distribues,
        "mode": "pdf_non_distribues_toleres" if tolere else "strict",
        "verdict": "INTEGRE" if not alteres and not absents else "ECART DETECTE",
    }


def rapport(domaine=None, chemin=None):
    with connexion(chemin) as conn:
        docs = conn.execute(
            "SELECT doc_id, titre, type_texte, numero_texte, date_texte, domaine, autorite,"
            " url_source, sha256, octets, pages, calque_texte, note_qualite,"
            " methode_extraction, fichier_ocr, sha256_ocr, recoupe_avec, qualite_ocr"
            " FROM documents" + (" WHERE domaine = ?" if domaine else "") +
            " ORDER BY date_texte DESC",
            ([domaine] if domaine else [])).fetchall()
        docs = [dict(d) for d in docs]
        nb_articles = conn.execute("SELECT COUNT(*) FROM articles_corpus").fetchone()[0]
        par_doc = {r[0]: r[1] for r in conn.execute(
            "SELECT doc_id, COUNT(*) FROM articles_corpus GROUP BY doc_id").fetchall()}
    exploitables = [d for d in docs if d["calque_texte"]]
    origine = articles_par_origine(chemin=chemin)
    return {
        "horodatage": horodatage(),
        "domaine": domaine or "tous",
        "nb_documents": len(docs),
        "nb_documents_exploitables": len(exploitables),
        "nb_documents_scans_seulement": len(docs) - len(exploitables),
        "nb_articles_indexes": nb_articles,
        "articles_par_origine": origine,
        "documents": [{**d, "articles_indexes": par_doc.get(d["doc_id"], 0),
                       "exploitable": bool(d["calque_texte"])} for d in docs],
    }
