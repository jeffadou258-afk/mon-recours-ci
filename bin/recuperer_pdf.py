#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Récupère les PDF du corpus absents du disque, avec vérification d'empreinte.

CONTEXTE
    La base enregistre pour chaque document le SHA-256 du PDF officiel. Quand le
    fichier manque sur une machine (installation neuve, transfert incomplet,
    document collecté ailleurs), l'intégrité passe en « ECART DETECTE » — un
    signal juste, mais qui masque les autres.

CE QUE FAIT CET OUTIL
    Pour chaque document dont le PDF est absent, il retélécharge depuis
    `url_source` et n'écrit le fichier **que si l'empreinte correspond à celle
    enregistrée**. Aucun fichier n'est remplacé : un document présent n'est
    jamais touché. Une source morte reste morte, et l'écart reste visible.

CE QU'IL NE FAIT PAS
    Il ne contourne aucune protection : pas d'authentification forcée, pas de
    paywall franchi, pas d'agent qui se ferait passer pour un navigateur humain.
    Une source qui refuse reste refusée.

USAGE
    python3 bin/recuperer_pdf.py               # simulation : montre ce qui serait fait
    python3 bin/recuperer_pdf.py --telecharger # récupère réellement, empreinte vérifiée
"""

import argparse
import hashlib
import json
import pathlib
import sqlite3
import sys
import urllib.error
import urllib.request

RACINE = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import config  # noqa: E402

AGENT = "Mozilla/5.0 (compatible; MonRecoursCI/1.0; verification d'integrite)"
DELAI_S = 60
LIMITE_OCTETS = 60 * 1024 * 1024

RECUPERE = "RECUPERE"
DEJA_PRESENT = "DEJA_PRESENT"
EMPREINTE_DIFFERENTE = "EMPREINTE_DIFFERENTE"
INACCESSIBLE = "INACCESSIBLE"
SANS_URL = "SANS_URL"
TROP_VOLUMINEUX = "TROP_VOLUMINEUX"


def empreinte_attendue(valeur):
    """La base stocke `sha256:<hex>` ; on compare au hexadécimal nu."""
    return str(valeur or "").split(":")[-1].strip().lower()


def resoudre(chemin_local):
    """Chemin absolu d'origine -> chemin valide sur cette machine."""
    if not chemin_local:
        return None
    if "KNOWLEDGE/" in chemin_local:
        return pathlib.Path(str(config.KNOWLEDGE_DIR)) / chemin_local.split("KNOWLEDGE/", 1)[1]
    return pathlib.Path(chemin_local)


def telecharger(url, ouvreur=urllib.request.urlopen):
    """Renvoie (octets | None, statut). N'élève jamais."""
    try:
        requete = urllib.request.Request(url, headers={"User-Agent": AGENT})
        with ouvreur(requete, timeout=DELAI_S) as reponse:
            brut = reponse.read(LIMITE_OCTETS + 1)
    except urllib.error.HTTPError as erreur:
        return None, "%s_%d" % (INACCESSIBLE, erreur.code)
    except Exception as e:
        return None, "%s_%s" % (INACCESSIBLE, type(e).__name__)
    if len(brut) > LIMITE_OCTETS:
        return None, TROP_VOLUMINEUX
    return brut, RECUPERE


def traiter(doc_id, chemin_local, url, sha, telecharger_vraiment=False, ouvreur=urllib.request.urlopen):
    cible = resoudre(chemin_local)
    if cible is None:
        return doc_id, SANS_URL, ""
    if cible.exists():
        return doc_id, DEJA_PRESENT, str(cible)
    if not url:
        return doc_id, SANS_URL, str(cible)
    brut, statut = telecharger(url, ouvreur)
    if brut is None:
        return doc_id, statut, str(cible)
    attendu = empreinte_attendue(sha)
    reel = hashlib.sha256(brut).hexdigest()
    if not attendu or reel != attendu:
        return doc_id, EMPREINTE_DIFFERENTE, "attendu %s… reçu %s…" % (attendu[:12], reel[:12])
    if telecharger_vraiment:
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(brut)
        cible.chmod(0o600)
    return doc_id, RECUPERE, "%s (%d octets)" % (cible.name, len(brut))


def recuperer(chemin_db, telecharger_vraiment=False, ouvreur=urllib.request.urlopen):
    connexion = sqlite3.connect(str(chemin_db))
    try:
        lignes = connexion.execute(
            "SELECT doc_id, chemin_local, url_source, sha256 FROM documents"
        ).fetchall()
    finally:
        connexion.close()
    resultats = []
    for doc_id, chemin, url, sha in lignes:
        doc_id, statut, detail = traiter(doc_id, chemin, url, sha, telecharger_vraiment, ouvreur)
        resultats.append({"doc_id": doc_id, "statut": statut, "detail": detail})
    return resultats


def main(argv=None):
    analyseur = argparse.ArgumentParser(description="Récupère les PDF absents, empreinte vérifiée.")
    analyseur.add_argument("--base", default=str(config.CHEMIN_DB))
    analyseur.add_argument("--telecharger", action="store_true",
                           help="écrire réellement les fichiers (sinon simulation)")
    args = analyseur.parse_args(argv)

    resultats = recuperer(args.base, telecharger_vraiment=args.telecharger)
    manquants = [r for r in resultats if r["statut"] != DEJA_PRESENT]
    for r in manquants:
        print("  %-18s %-22s %s" % (r["doc_id"], r["statut"], r["detail"][:70]))
    compte = {}
    for r in resultats:
        compte[r["statut"]] = compte.get(r["statut"], 0) + 1
    print("\n  " + " | ".join("%s : %d" % (k, v) for k, v in sorted(compte.items())))
    if not args.telecharger and any(r["statut"] == RECUPERE for r in manquants):
        print("  simulation : relancer avec --telecharger pour écrire les fichiers")
    return 0


if __name__ == "__main__":
    sys.exit(main())
