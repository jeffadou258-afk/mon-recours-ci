# -*- coding: utf-8 -*-
"""Vérification RÉELLE des sources officielles.

Deux garanties tenues par ce module :

1. Une source n'est jamais *déclarée* accessible : elle est *testée* (requête
   HTTP réelle) et le résultat est horodaté, avec le code retour.
2. Un échec n'est jamais converti en succès. Un 503, un timeout DNS ou un
   certificat invalide sont enregistrés tels quels, avec leur libellé.

Corollaire assumé : ce module ne dit PAS qu'un texte est en vigueur. Il dit
seulement si la SOURCE répond à l'instant de la consultation. La vigueur d'un
texte relève de l'état de vérification de la référence (voir core/base.py).

Aucune dépendance hors bibliothèque standard (urllib, ssl, json).
"""

import datetime
import json
import os
import ssl
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

from config import (
    CHEMIN_VERIFICATIONS_SOURCES,
    SOURCES_OFFICIELLES,
    SOURCES_SECONDAIRES,
    USER_AGENT,
    source_par_id,
)

# Statuts possibles d'une vérification de source.
STATUT_ACCESSIBLE = "ACCESSIBLE"
STATUT_INDISPONIBLE = "INDISPONIBLE"
STATUT_REFUSE = "REFUSE"
STATUT_INTROUVABLE = "INTROUVABLE"
STATUT_INJOIGNABLE = "INJOIGNABLE"
STATUT_INATTENDU = "INATTENDU"


def horodatage():
    """Horodatage UTC ISO-8601, seconde près."""
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


def classer_statut(code_http):
    """Traduit un code HTTP en statut. `None` = pas de réponse (réseau/DNS/TLS).

    Un test unitaire pur couvre cette table : elle ne doit jamais dépendre du
    réseau pour être vérifiée.
    """
    if code_http is None:
        return STATUT_INJOIGNABLE
    code = int(code_http)
    if 200 <= code < 300:
        return STATUT_ACCESSIBLE
    if code in (401, 403, 407, 429):
        return STATUT_REFUSE
    if code == 404 or code == 410:
        return STATUT_INTROUVABLE
    if 500 <= code < 600:
        return STATUT_INDISPONIBLE
    if 300 <= code < 400:
        # urllib suit les redirections : un 3xx ici signifie une redirection
        # non suivie, cas limite. On le classe INATTENDU plutôt que de trancher.
        return STATUT_INATTENDU
    return STATUT_INATTENDU


def verifier_url(url, timeout=20, user_agent=USER_AGENT, lire_octets=4096):
    """Effectue une requête HTTP réelle et retourne un enregistrement factuel.

    Le corps n'est lu qu'en partie (4 Ko par défaut) : on vérifie l'accès, pas
    le contenu. Ne lève pas : les erreurs deviennent des champs.
    """
    enregistrement = {
        "url": url,
        "statut": STATUT_INJOIGNABLE,
        "http_status": None,
        "url_finale": None,
        "content_type": None,
        "octets_lus": 0,
        "date_consultation": horodatage(),
        "erreur": None,
        "duree_s": None,
    }
    debut = time.time()
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
            "Accept-Language": "fr-FR,fr;q=0.9",
        },
    )
    contexte = ssl.create_default_context()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=contexte) as reponse:
            enregistrement["http_status"] = reponse.getcode()
            enregistrement["url_finale"] = reponse.geturl()
            enregistrement["content_type"] = reponse.headers.get("Content-Type")
            corps = reponse.read(lire_octets)
            enregistrement["octets_lus"] = len(corps)
    except urllib.error.HTTPError as erreur:
        enregistrement["http_status"] = erreur.code
        enregistrement["url_finale"] = erreur.geturl() if hasattr(erreur, "geturl") else url
        enregistrement["content_type"] = None
        enregistrement["erreur"] = "HTTPError %s : %s" % (erreur.code, erreur.reason)
    except urllib.error.URLError as erreur:
        enregistrement["erreur"] = "URLError : %s" % (erreur.reason,)
    except ssl.SSLError as erreur:
        enregistrement["erreur"] = "SSLError : %s" % (erreur,)
    except Exception as erreur:  # noqa: BLE001 — l'échec doit être enregistré, pas masqué
        enregistrement["erreur"] = "%s : %s" % (type(erreur).__name__, erreur)

    enregistrement["duree_s"] = round(time.time() - debut, 3)
    enregistrement["statut"] = classer_statut(enregistrement["http_status"])
    return enregistrement


# --------------------------------------------------------------------------
# Persistance des vérifications (journal horodaté, jamais écrasé)
# --------------------------------------------------------------------------
def charger_verifications(chemin=None):
    chemin = chemin or CHEMIN_VERIFICATIONS_SOURCES
    if not os.path.exists(chemin):
        return []
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            donnees = json.load(f)
    except (ValueError, OSError):
        return []
    return donnees if isinstance(donnees, list) else []


def enregistrer_verifications(enregistrements, chemin=None):
    """Écriture atomique : un fichier partiel ne doit jamais remplacer l'historique."""
    chemin = chemin or CHEMIN_VERIFICATIONS_SOURCES
    os.makedirs(os.path.dirname(chemin), exist_ok=True)
    historique = charger_verifications(chemin)
    historique.extend(enregistrements)
    fd, temporaire = tempfile.mkstemp(dir=os.path.dirname(chemin), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(historique, f, ensure_ascii=False, indent=2)
        os.replace(temporaire, chemin)
    except Exception:
        if os.path.exists(temporaire):
            os.unlink(temporaire)
        raise
    return len(historique)


def verifier_sources(source_ids=None, timeout=20, persister=True, chemin=None):
    """Vérifie les sources du registre (toutes, ou celles demandées).

    Retourne la liste des enregistrements produits dans CETTE exécution.
    """
    if source_ids:
        a_verifier = []
        for sid in source_ids:
            s = source_par_id(sid)
            if s is None:
                raise KeyError("source inconnue du registre : %r" % (sid,))
            a_verifier.append(s)
    else:
        a_verifier = [dict(s) for s in SOURCES_OFFICIELLES]

    resultats = []
    for source in a_verifier:
        rec = verifier_url(source["url"], timeout=timeout)
        rec["source_id"] = source["id"]
        rec["source_nom"] = source["nom"]
        rec["role"] = source["role"]
        resultats.append(rec)

    if persister and resultats:
        enregistrer_verifications(resultats, chemin=chemin)
    return resultats


def derniere_verification(source_id, chemin=None):
    """Dernier enregistrement connu pour une source, ou None.

    `None` signifie « jamais testée » — l'agent le dit, il ne suppose rien.
    """
    historique = charger_verifications(chemin)
    for rec in reversed(historique):
        if rec.get("source_id") == source_id:
            return rec
    return None


def rapport_sources(chemin=None):
    """Synthèse factuelle : ce qui répond, ce qui ne répond pas, ce qui n'a jamais été testé.

    Les sources jamais testées sont NOMMÉES (spec §15 : ne pas masquer l'absence).
    """
    historique = charger_verifications(chemin)
    par_source = {}
    for rec in historique:
        par_source[rec.get("source_id")] = rec

    lignes = []
    jamais_testees = []
    for source in SOURCES_OFFICIELLES:
        rec = par_source.get(source["id"])
        if rec is None:
            jamais_testees.append(source["id"])
            lignes.append({
                "source_id": source["id"],
                "nom": source["nom"],
                "url": source["url"],
                "statut": "JAMAIS_TESTEE",
                "http_status": None,
                "date_consultation": None,
                "erreur": None,
            })
        else:
            lignes.append({
                "source_id": source["id"],
                "nom": source["nom"],
                "url": source["url"],
                "statut": rec.get("statut"),
                "http_status": rec.get("http_status"),
                "date_consultation": rec.get("date_consultation"),
                "erreur": rec.get("erreur"),
            })

    accessibles = [l for l in lignes if l["statut"] == STATUT_ACCESSIBLE]
    inaccessibles = [l for l in lignes if l["statut"] not in (STATUT_ACCESSIBLE, "JAMAIS_TESTEE")]
    return {
        "horodatage_rapport": horodatage(),
        "nb_sources_registre": len(SOURCES_OFFICIELLES),
        "nb_verifications_enregistrees": len(historique),
        "accessibles": accessibles,
        "inaccessibles": inaccessibles,
        "jamais_testees": jamais_testees,
        "sources": lignes,
        "avertissement": (
            "Ce rapport porte sur l'ACCESSIBILITÉ des sources, pas sur la validité "
            "ou la vigueur des textes qu'elles publient."
        ),
    }


def est_hote_officiel(url):
    """Un hôte est-il du périmètre officiel ivoirien (registry ou *.gouv.ci) ?

    Sert de garde pour refuser de promouvoir une référence VERIFIE sur la base
    d'un blog ou d'un forum.
    """
    if not url:
        return False
    hote = urllib.parse.urlparse(url).hostname or ""
    hote = hote.lower().lstrip(".")
    if not hote:
        return False
    if hote.endswith(".gouv.ci") or hote == "gouv.ci":
        return True
    for source in SOURCES_OFFICIELLES:
        hote_registre = (urllib.parse.urlparse(source["url"]).hostname or "").lower()
        # « www.oneci.ci » au registre et « oneci.ci » dans l'URL : même institution.
        if hote_registre.startswith("www."):
            hote_registre = hote_registre[4:]
        if hote_registre and (hote == hote_registre or hote.endswith("." + hote_registre)):
            return True
    return False


def est_source_secondaire(url):
    """Identifiant de la source SECONDAIRE connue pour cet hôte, sinon None.

    Un texte lu chez un hébergeur non ivoirien (FAOLEX) peut être importé et
    cité, mais jamais promu VERIFIE : `core/base.py` réserve ce statut au
    périmètre officiel. Cette fonction ne dit donc pas « officiel » — elle dit
    « hôte connu et déclaré comme secondaire ».
    """
    if not url:
        return None
    hote = urllib.parse.urlparse(url).hostname or ""
    hote = hote.lower().lstrip(".")
    if not hote:
        return None
    for source in SOURCES_SECONDAIRES:
        hote_registre = (urllib.parse.urlparse(source["url"]).hostname or "").lower()
        if hote_registre.startswith("www."):
            hote_registre = hote_registre[4:]
        if hote_registre and (hote == hote_registre or hote.endswith("." + hote_registre)):
            return source["id"]
    return None
