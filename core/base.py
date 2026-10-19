# -*- coding: utf-8 -*-
"""Corpus de références juridiques — SQLite, métadonnées obligatoires.

Contrat de ce module (spec §7.C, §7.D, §10.1-3) :

* Une référence ne peut PAS être enregistrée sans titre, type de texte, source
  et URL (contraintes SQL, pas seulement des conventions).
* L'état par défaut est `NON_VERIFIE`. Rien ne promeut un statut tout seul.
* Le passage à `VERIFIE` exige une preuve : URL d'une source officielle +
  empreinte du contenu consulté + date de consultation. Sans preuve, la
  promotion est refusée par une exception, pas par un avertissement.
* Une citation (`extrait`) n'existe que si elle a été enregistrée avec la
  référence. `verifier_citation()` la retrouve dans l'extrait stocké ; une
  citation absente est signalée, jamais tolérée.

Ce module ne contient AUCUN article de loi : il est vide au départ, et c'est
volontaire. Le corpus se remplit par consultation réelle.
"""

import datetime
import hashlib
import os
import re
import sqlite3
import unicodedata

from config import CHEMIN_DB, STATUTS_VERIFICATION
from core.sources import est_hote_officiel

SCHEMA = """
CREATE TABLE IF NOT EXISTS references_juridiques (
    ref_id                TEXT PRIMARY KEY,
    titre_officiel        TEXT NOT NULL CHECK(length(trim(titre_officiel)) > 0),
    type_texte            TEXT NOT NULL CHECK(length(trim(type_texte)) > 0),
    numero_texte          TEXT,
    date_publication      TEXT,
    articles              TEXT,
    domaine               TEXT,
    source_nom            TEXT NOT NULL CHECK(length(trim(source_nom)) > 0),
    source_url            TEXT NOT NULL CHECK(source_url LIKE 'http%'),
    date_consultation     TEXT NOT NULL CHECK(date_consultation LIKE '____-__-__%'),
    etat_verification     TEXT NOT NULL DEFAULT 'NON_VERIFIE'
                          CHECK(etat_verification IN
                              ('VERIFIE','PARTIELLEMENT_VERIFIE','NON_VERIFIE','NON_CONFIRME','OBSOLETE')),
    texte_complet_present INTEGER NOT NULL DEFAULT 0 CHECK(texte_complet_present IN (0,1)),
    extrait_texte         TEXT,
    modifications         TEXT,
    limites_interpretation TEXT,
    empreinte_contenu     TEXT,
    cree_le               TEXT NOT NULL,
    maj_le                TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS verifications (
    verification_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    ref_id            TEXT NOT NULL REFERENCES references_juridiques(ref_id),
    etat_precedent    TEXT NOT NULL,
    etat_nouveau      TEXT NOT NULL,
    preuve_url        TEXT,
    preuve_empreinte  TEXT,
    date_consultation TEXT,
    motif             TEXT NOT NULL DEFAULT '',
    horodatage        TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_refs_etat ON references_juridiques(etat_verification);
CREATE INDEX IF NOT EXISTS idx_refs_domaine ON references_juridiques(domaine);
"""


def horodatage():
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def normaliser(texte):
    if not texte:
        return ""
    # Les apostrophes typographiques doivent être converties AVANT l'encodage
    # ASCII : sinon elles sont purement supprimées et collent deux mots
    # (« d'habitation » devenait « dhabitation »), ce qui casse la recherche et
    # la vérification de citation sur des mots parmi les plus courants du
    # corpus (bail à usage d'habitation, d'immeuble, qu'il…).
    t = (str(texte)
         .replace("\u2019", "'").replace("\u2018", "'")
         .replace("\u00b4", "'").replace("`", "'"))
    # Trait d'union conditionnel (U+00AD) : par d\u00e9finition une coupure de mot
    # FACULTATIVE, invisible hors fin de ligne. L'extraction PDF le laisse suivi
    # d'un saut de ligne (\u00ab filia\u00ad\ntion \u00bb). Sans ce retrait, le mot coup\u00e9
    # devenait deux mots (\u00ab filia tion \u00bb) et une citation exacte du mot entier
    # \u00e9tait d\u00e9clar\u00e9e absente. Constat\u00e9 sur le Journal officiel du 12 juillet 2019
    # (loi n\u00b0 2019-571).
    t = re.sub("\u00ad\\s*", "", t)
    t = unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode("ascii")
    # Réparation des références numériques abîmées par l'extraction PDF.
    # Constaté sur le PDF officiel DGI du Code de la Construction et de
    # l'Habitat : le texte extrait porte « la loi 99 -478 », « n°65 -248 ».
    # Sans cette réparation, une citation contenant un numéro de texte ne peut
    # JAMAIS être retrouvée dans le texte source — le contrôle de citation
    # déclarerait « absente » une citation pourtant exacte.
    t = re.sub(r"(\d)\s*-\s*(\d)", r"\1-\2", t)
    t = re.sub(r"\bn\s*([o°º])\s*(\d)", r"n\1\2", t)
    return re.sub(r"\s+", " ", t).strip().lower()


def connexion(chemin=None):
    chemin = str(chemin or CHEMIN_DB)
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    conn = sqlite3.connect(chemin)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialiser(chemin=None):
    """Crée le schéma. Idempotent."""
    with connexion(chemin) as conn:
        conn.executescript(SCHEMA)
    return str(chemin or CHEMIN_DB)


def _identifiant(titre_officiel, type_texte, numero_texte):
    """Clé DÉTERMINISTE : dérivée, jamais tirée au sort ni horodatée.

    Deux saisies du même texte produisent la même clé (donc pas de doublon),
    deux textes différents produisent des clés différentes.
    """
    base = " | ".join(normaliser(x) for x in (titre_officiel, type_texte, numero_texte or ""))
    return "REF-" + hashlib.sha256(base.encode("utf-8")).hexdigest()[:12].upper()


def empreinte_texte(texte):
    return "sha256:" + hashlib.sha256((texte or "").encode("utf-8")).hexdigest()


def ajouter_reference(
    titre_officiel,
    type_texte,
    source_nom,
    source_url,
    date_consultation,
    numero_texte=None,
    date_publication=None,
    articles=None,
    domaine=None,
    extrait_texte=None,
    texte_complet_present=False,
    modifications=None,
    limites_interpretation=None,
    chemin=None,
):
    """Enregistre une référence avec ses métadonnées obligatoires.

    Lève ValueError si un champ obligatoire manque (message explicite).
    Lève sqlite3.IntegrityError si la contrainte SQL est violée (défense en
    profondeur : l'API et le schéma vérifient tous les deux).
    """
    obligatoires = {
        "titre_officiel": titre_officiel,
        "type_texte": type_texte,
        "source_nom": source_nom,
        "source_url": source_url,
        "date_consultation": date_consultation,
    }
    manquants = [k for k, v in obligatoires.items() if not (v and str(v).strip())]
    if manquants:
        raise ValueError("métadonnées obligatoires manquantes : %s" % ", ".join(sorted(manquants)))
    if not str(source_url).startswith("http"):
        raise ValueError("source_url doit être une URL http(s) — reçu %r" % (source_url,))
    if not re.match(r"^\d{4}-\d{2}-\d{2}", str(date_consultation)):
        raise ValueError("date_consultation doit être ISO (AAAA-MM-JJ) — reçu %r" % (date_consultation,))

    ref_id = _identifiant(titre_officiel, type_texte, numero_texte)
    existante = obtenir_reference(ref_id, chemin)
    if existante is not None:
        # IDEMPOTENT, ET NON ÉCRASANT. Réenregistrer le même texte ne crée pas de
        # doublon et ne peut PAS rétrograder une référence déjà vérifiée : c'est ce
        # qui protège l'état de vérification d'une nouvelle saisie naïve.
        return ref_id

    maintenant = horodatage()
    extrait = extrait_texte or ""
    with connexion(chemin) as conn:
        conn.execute(
            """
            INSERT INTO references_juridiques (
                ref_id, titre_officiel, type_texte, numero_texte, date_publication,
                articles, domaine, source_nom, source_url, date_consultation,
                etat_verification, texte_complet_present, extrait_texte,
                modifications, limites_interpretation, empreinte_contenu, cree_le, maj_le
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                ref_id, titre_officiel, type_texte, numero_texte, date_publication,
                articles, domaine, source_nom, source_url, date_consultation,
                "NON_VERIFIE", 1 if texte_complet_present else 0, extrait,
                modifications, limites_interpretation,
                empreinte_texte(extrait) if extrait else None, maintenant, maintenant,
            ),
        )
    return ref_id


def obtenir_reference(ref_id, chemin=None):
    with connexion(chemin) as conn:
        ligne = conn.execute(
            "SELECT * FROM references_juridiques WHERE ref_id = ?", (ref_id,)
        ).fetchone()
    return dict(ligne) if ligne else None


def annoter_reference(ref_id, note, source_url, chemin=None):
    """Ajoute une note datée et sourcée aux limites d'interprétation d'une référence.

    N'efface rien (la note précédente est conservée), ne change ni l'extrait ni
    l'état de vérification. Sert à consigner un recoupement ou une correction
    documentée. Idempotent : la même note n'est pas ajoutée deux fois.
    """
    if not note or not str(source_url or "").startswith("http"):
        raise ValueError("une note exige un texte et une source http(s)")
    existante = obtenir_reference(ref_id, chemin)
    if existante is None:
        raise ValueError("référence inconnue : %s" % ref_id)
    ajout = "[%s] %s (source : %s)" % (horodatage()[:10], note.strip(), source_url)
    actuelles = existante.get("limites_interpretation") or ""
    if note.strip() in actuelles:
        return actuelles
    nouvelles = (actuelles + " " + ajout).strip()
    with connexion(chemin) as conn:
        conn.execute("UPDATE references_juridiques SET limites_interpretation = ?, maj_le = ? "
                     "WHERE ref_id = ?", (nouvelles, horodatage(), ref_id))
    return nouvelles


def lister_references(etat=None, domaine=None, chemin=None):
    requete = "SELECT * FROM references_juridiques"
    conditions, params = [], []
    if etat:
        conditions.append("etat_verification = ?")
        params.append(etat)
    if domaine:
        conditions.append("domaine = ?")
        params.append(domaine)
    if conditions:
        requete += " WHERE " + " AND ".join(conditions)
    requete += " ORDER BY maj_le DESC"
    with connexion(chemin) as conn:
        return [dict(r) for r in conn.execute(requete, params).fetchall()]


def rechercher(mots_cles, chemin=None):
    """Recherche plein-texte tolérante (accents/casse). Retourne aussi un score.

    Aucun résultat n'est inventé : une liste vide est une réponse en soi.
    """
    termes = [normaliser(t) for t in re.split(r"[\s,;]+", mots_cles or "") if t.strip()]
    if not termes:
        return []
    resultats = []
    for ref in lister_references(chemin=chemin):
        champs = " ".join([
            str(ref.get("titre_officiel") or ""),
            str(ref.get("articles") or ""),
            str(ref.get("type_texte") or ""),
            str(ref.get("numero_texte") or ""),
            str(ref.get("extrait_texte") or ""),
        ])
        cible = normaliser(champs)
        score = sum(cible.count(t) for t in termes)
        if score > 0:
            ref["score"] = score
            resultats.append(ref)
    resultats.sort(key=lambda r: (-r["score"], r["ref_id"]))
    return resultats


def ref_ids_connus(chemin=None):
    with connexion(chemin) as conn:
        return {r[0] for r in conn.execute("SELECT ref_id FROM references_juridiques").fetchall()}


def promouvoir_verification(
    ref_id,
    etat_nouveau,
    preuve_url=None,
    preuve_empreinte=None,
    date_consultation=None,
    motif="",
    chemin=None,
):
    """Change l'état de vérification d'une référence. Exige une preuve.

    Règles (invariants, non négociables) :
      * `etat_nouveau` doit appartenir à STATUTS_VERIFICATION ;
      * `VERIFIE` exige preuve_url + preuve_empreinte + date_consultation ;
      * la preuve doit venir d'un hôte officiel du périmètre ;
      * tout changement est journalisé dans `verifications` (jamais silencieux).
    """
    if etat_nouveau not in STATUTS_VERIFICATION:
        raise ValueError("état de vérification inconnu : %r" % (etat_nouveau,))
    ref = obtenir_reference(ref_id, chemin=chemin)
    if ref is None:
        raise KeyError("référence inconnue : %r" % (ref_id,))

    if etat_nouveau == "VERIFIE":
        manquants = [n for n, v in (
            ("preuve_url", preuve_url),
            ("preuve_empreinte", preuve_empreinte),
            ("date_consultation", date_consultation),
        ) if not (v and str(v).strip())]
        if manquants:
            raise ValueError(
                "promotion VERIFIE refusée : preuve incomplète (%s)" % ", ".join(manquants)
            )
        if not est_hote_officiel(preuve_url):
            raise ValueError(
                "promotion VERIFIE refusée : %r n'appartient pas au périmètre des sources "
                "officielles du registre" % (preuve_url,)
            )

    maintenant = horodatage()
    with connexion(chemin) as conn:
        conn.execute(
            "UPDATE references_juridiques SET etat_verification = ?, maj_le = ? WHERE ref_id = ?",
            (etat_nouveau, maintenant, ref_id),
        )
        conn.execute(
            """
            INSERT INTO verifications (ref_id, etat_precedent, etat_nouveau, preuve_url,
                                       preuve_empreinte, date_consultation, motif, horodatage)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (ref_id, ref["etat_verification"], etat_nouveau, preuve_url,
             preuve_empreinte, date_consultation, motif, maintenant),
        )
    return obtenir_reference(ref_id, chemin=chemin)


def historique_verifications(ref_id, chemin=None):
    with connexion(chemin) as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM verifications WHERE ref_id = ? ORDER BY verification_id", (ref_id,)
        ).fetchall()]


def verifier_citation(ref_id, citation, chemin=None):
    """La citation existe-t-elle littéralement dans l'extrait enregistré ?

    Retourne (ok: bool, raison: str). C'est le garde mécanique anti-fabrication
    de citation : aucune tolérance, aucune approximation sémantique.
    """
    ref = obtenir_reference(ref_id, chemin=chemin)
    if ref is None:
        return False, "référence inconnue : %s" % ref_id
    if not ref.get("texte_complet_present"):
        return False, (
            "texte intégral non présent pour %s : une citation ne peut pas être "
            "vérifiée, elle doit donc être signalée comme non vérifiable" % ref_id
        )
    extrait = ref.get("extrait_texte") or ""
    if not extrait:
        return False, "aucun extrait enregistré pour %s" % ref_id
    if normaliser(citation) and normaliser(citation) in normaliser(extrait):
        return True, "citation retrouvée dans l'extrait enregistré de %s" % ref_id
    return False, "citation ABSENTE de l'extrait enregistré de %s" % ref_id


def statistiques(chemin=None):
    with connexion(chemin) as conn:
        total = conn.execute("SELECT COUNT(*) FROM references_juridiques").fetchone()[0]
        par_etat = {r[0]: r[1] for r in conn.execute(
            "SELECT etat_verification, COUNT(*) FROM references_juridiques GROUP BY 1"
        ).fetchall()}
        nb_verifs = conn.execute("SELECT COUNT(*) FROM verifications").fetchone()[0]
    return {
        "total_references": total,
        "par_etat": par_etat,
        "tous_les_etats_nommes": {e: par_etat.get(e, 0) for e in STATUTS_VERIFICATION},
        "nb_entrees_verification": nb_verifs,
        "chemin": str(chemin or CHEMIN_DB),
    }
