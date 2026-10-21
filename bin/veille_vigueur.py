#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Veille de vigueur — inventaire technique préparatoire à la relecture juridique.

CE QUE CET OUTIL FAIT
    Pour chaque référence du corpus, il rassemble ce qui est **observable sans
    interprétation** : l'adresse de la source, l'état de vérification enregistré,
    la date de consultation, et — si on le demande — si l'adresse répond encore
    et si le document officiel téléchargé est **identique** à celui qui a servi.

CE QU'IL NE FAIT PAS, ET NE FERA PAS
    Il ne dit jamais qu'un texte est « en vigueur ». La vigueur dépend de textes
    modificatifs et d'abrogations qu'aucune empreinte ne révèle : c'est un
    travail de juriste. Chaque entrée porte donc `statut_vigueur: NON_VERIFIEE`
    et `a_valider_par_un_juriste: true`, sans exception, même si la source
    répond parfaitement.

    Une source qui répond n'est pas une source à jour ; une empreinte identique
    prouve seulement que le fichier n'a pas changé.

USAGE
    python3 bin/veille_vigueur.py                     # inventaire hors ligne
    python3 bin/veille_vigueur.py --reseau            # + test de joignabilité
    python3 bin/veille_vigueur.py --reseau --empreintes  # + comparaison SHA-256
    python3 bin/veille_vigueur.py --sortie /tmp/veille.json

    L'outil n'écrit rien dans la base. Il produit un rapport JSON.
"""

import argparse
import hashlib
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE))

import config  # noqa: E402

DELAI_S = 20
LIMITE_OCTETS = 30 * 1024 * 1024
AGENT = "MonRecoursCI-veille/1.0 (inventaire technique, pas de moissonnage)"
NON_VERIFIEE = "NON_VERIFIEE"


def classer_joignabilite(code):
    """Traduit un code HTTP en constat factuel. Aucune interprétation juridique."""
    if code is None:
        return "INACCESSIBLE"
    if 200 <= code < 300:
        return "JOIGNABLE"
    if 300 <= code < 400:
        return "REDIRIGE"
    if 400 <= code < 500:
        return "REFUSE"
    return "ERREUR_SERVEUR"


def interroger(url, telecharger=False):
    """Répond (code_http | None, empreinte | None, octets | None). Ne lève pas."""
    requete = urllib.request.Request(url, headers={"User-Agent": AGENT})
    if not telecharger:
        requete.method = "HEAD"
    try:
        with urllib.request.urlopen(requete, timeout=DELAI_S) as reponse:
            code = reponse.status
            if not telecharger:
                return code, None, None
            empreinte = hashlib.sha256()
            total = 0
            for bloc in iter(lambda: reponse.read(1 << 16), b""):
                total += len(bloc)
                if total > LIMITE_OCTETS:
                    return code, None, total
                empreinte.update(bloc)
            return code, empreinte.hexdigest(), total
    except urllib.error.HTTPError as erreur:
        return erreur.code, None, None
    except Exception:
        return None, None, None


def charger_references(chemin_db):
    """Références + empreintes de documents si la table existe (base minimale possible)."""
    connexion = sqlite3.connect(str(chemin_db))
    try:
        lignes = connexion.execute(
            """
            SELECT ref_id, titre_officiel, numero_texte, source_url,
                   etat_verification, date_consultation, modifications,
                   length(extrait_texte)
            FROM references_juridiques
            ORDER BY titre_officiel
            """
        ).fetchall()
        empreintes = {}
        a_documents = connexion.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents'").fetchone()
        if a_documents:
            for ref_id, sha, qualite, ocr in connexion.execute(
                    "SELECT ref_id, sha256, note_qualite, note_ocr FROM documents"):
                # Un texte peut avoir plusieurs exemplaires : on garde le premier.
                empreintes.setdefault(ref_id, (sha, qualite, ocr))
        return [tuple(ligne) + empreintes.get(ligne[0], (None, None, None)) for ligne in lignes]
    finally:
        connexion.close()


def construire(chemin_db, reseau=False, empreintes=False, journal=print):
    lignes = charger_references(chemin_db)
    entrees = []
    for (ref_id, titre, numero, url, etat, consultation, modifications,
         taille_extrait, empreinte_doc, note_qualite, note_ocr) in lignes:
        entree = {
            "ref_id": ref_id,
            "titre_officiel": titre,
            "numero_texte": numero,
            "source_url": url,
            "etat_verification": etat,
            "date_consultation": consultation,
            "modifications_renseignees": bool(modifications and str(modifications).strip()),
            "texte_present": bool(taille_extrait),
            "empreinte_document_connue": empreinte_doc,
            "note_qualite": note_qualite,
            "note_ocr": note_ocr,
            # Jamais autre chose : la vigueur n'est pas déductible techniquement.
            "statut_vigueur": NON_VERIFIEE,
            "a_valider_par_un_juriste": True,
            "technique": {},
        }
        if reseau and url:
            code, empreinte_distante, octets = interroger(url, telecharger=empreintes)
            entree["technique"] = {
                "verifie_le": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "code_http": code,
                "joignabilite": classer_joignabilite(code),
            }
            if empreintes and code and 200 <= code < 300:
                entree["technique"]["octets_distants"] = octets
                if empreinte_distante and empreinte_doc:
                    entree["technique"]["empreinte_identique"] = empreinte_distante == empreinte_doc
                else:
                    entree["technique"]["empreinte_identique"] = None
            journal("  %-46s %s" % ((titre or "")[:46], entree["technique"].get("joignabilite", "-")))
        entrees.append(entree)
    return {
        "genere_le": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "avertissement": (
            "Aucun statut de vigueur n'est déduit automatiquement. Une source qui répond "
            "n'est pas une source à jour ; une empreinte identique prouve seulement que "
            "le fichier n'a pas changé. La vigueur exige une relecture juridique."
        ),
        "resume": {
            "references": len(entrees),
            "verifie": sum(1 for e in entrees if e["etat_verification"] == "VERIFIE"),
            "partiellement_verifie": sum(1 for e in entrees if e["etat_verification"] == "PARTIELLEMENT_VERIFIE"),
            "modifications_renseignees": sum(1 for e in entrees if e["modifications_renseignees"]),
            "statut_vigueur_verifie": 0,
        },
        "references": entrees,
    }


def main(argv=None):
    analyseur = argparse.ArgumentParser(
        description="Veille de vigueur : inventaire technique pour la relecture juridique.")
    analyseur.add_argument("--base", default=str(config.CHEMIN_DB))
    analyseur.add_argument("--sortie", default=str(config.BASE_DIR / "KNOWLEDGE" / "veille_vigueur.json"))
    analyseur.add_argument("--reseau", action="store_true", help="tester la joignabilité des sources")
    analyseur.add_argument("--empreintes", action="store_true", help="comparer le SHA-256 du document distant")
    args = analyseur.parse_args(argv)

    rapport = construire(args.base, reseau=args.reseau, empreintes=args.empreintes)
    sortie = Path(args.sortie)
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(json.dumps(rapport, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    r = rapport["resume"]
    print("rapport : %s" % sortie)
    print("  references        : %d" % r["references"])
    print("  VERIFIE           : %d" % r["verifie"])
    print("  PARTIELLEMENT     : %d" % r["partiellement_verifie"])
    print("  modifications     : %d reference(s) renseignee(s)" % r["modifications_renseignees"])
    print("  statut de vigueur etabli : %d" % r["statut_vigueur_verifie"])
    if not args.reseau:
        print("  (joignabilité non testée : ajouter --reseau)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
