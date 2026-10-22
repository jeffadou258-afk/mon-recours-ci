#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sauvegarde chiffrée et restauration vérifiée — Mon Recours CI.

OBJET
    Produire une archive chiffrée des récits de consultation (`DOSSIERS/`) et de
    la base du corpus, puis la restaurer en vérifiant son intégrité.

CE QUI EST PROTÉGÉ
    * `DOSSIERS/` : les récits, courriers et traces de dossier. Données
      personnelles les plus sensibles du produit.
    * la base SQLite : copiée par l'API `sqlite3.backup()`, donc **cohérente**
      (jamais un fichier copié pendant une écriture).

CHIFFREMENT
    AES-256-CBC (openssl) + HMAC-SHA256 en mode « encrypt-then-MAC ».
    Deux clés dérivées d'une clé maître par HMAC avec des étiquettes distinctes.
    Le MAC couvre l'IV et le chiffré : une archive altérée ou une mauvaise clé
    échoue **toujours**, sans dépendre du hasard du remplissage CBC.

CLÉ
    Fichier de 64 caractères hexadécimaux (32 octets), hors dépôt, en 600.
        openssl rand -hex 32 > /etc/mon-recours-ci/cle-sauvegarde && chmod 600 …
    Fournie par `--cle` ou `MONRECOURS_CLE_SAUVEGARDE`. Absente ou trop courte :
    la commande échoue, elle ne sauvegarde pas en clair.

USAGE
    sauvegarde.py sauvegarder --sortie DIR (--dossiers P | --sans-dossiers) --base P
                              [--inclure P ...] [--cle F]
    sauvegarde.py verifier    --archive F [--cle F]
    sauvegarde.py restaurer   --archive F [--sortie DIR] [--base-destination P]
                              [--permanent-destination DIR] [--cle F] [--ecraser]

    Conservation de 24 h : en production, `--sans-dossiers` exclut les
    consultations des archives (aucune copie ne survit à la purge) ; `--inclure`
    ajoute la configuration et le journal d'audit, qui sont permanents.

CODES DE SORTIE
    0 succès · 2 usage ou clé · 3 archive invalide ou clé incorrecte
    4 échec de chiffrement · 5 restauration refusée · 6 outil manquant
"""

import argparse
import hashlib
import hmac
import json
import os
import secrets
import shutil
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path

VERSION = 1
ETIQUETTE_ENC = b"monrecours/sauvegarde/enc/v1"
ETIQUETTE_MAC = b"monrecours/sauvegarde/mac/v1"
NOM_MANIFESTE = "manifeste.json"
TAILLE_CLE = 32
MODE_FICHIER = 0o600
MODE_DOSSIER = 0o700


class Erreur(Exception):
    """Erreur portant un code de sortie et un message destiné à l'exploitant."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


# --------------------------------------------------------------------------
# Clé et cryptographie
# --------------------------------------------------------------------------

def lire_cle(chemin=None):
    """Lit la clé maître. Échoue si elle est absente, vide ou trop courte."""
    chemin = chemin or os.environ.get("MONRECOURS_CLE_SAUVEGARDE")
    if not chemin:
        raise Erreur(2, "clé absente : fournir --cle ou MONRECOURS_CLE_SAUVEGARDE")
    fichier = Path(chemin)
    if not fichier.is_file():
        raise Erreur(2, "fichier de clé introuvable : %s" % fichier)
    brut = fichier.read_text(encoding="utf-8").strip()
    if not brut:
        raise Erreur(2, "fichier de clé vide : %s" % fichier)
    try:
        cle = bytes.fromhex(brut)
    except ValueError:
        raise Erreur(2, "clé invalide : 64 caractères hexadécimaux attendus")
    if len(cle) != TAILLE_CLE:
        raise Erreur(2, "clé de %d octets : %d attendus" % (len(cle), TAILLE_CLE))
    return cle


def deriver(cle, etiquette):
    return hmac.new(cle, etiquette, hashlib.sha256).digest()


def verifier_openssl():
    if shutil.which("openssl") is None:
        raise Erreur(6, "openssl introuvable : chiffrement impossible")


def chiffrer(cle, source, destination, iv):
    """Chiffre `source` vers `destination`. Échoue explicitement."""
    verifier_openssl()
    enc = deriver(cle, ETIQUETTE_ENC)
    commande = ["openssl", "enc", "-aes-256-cbc", "-K", enc.hex(),
                "-iv", iv.hex(), "-nosalt", "-in", str(source), "-out", str(destination)]
    resultat = subprocess.run(commande, capture_output=True)
    if resultat.returncode != 0:
        raise Erreur(4, "chiffrement impossible : %s"
                     % resultat.stderr.decode("utf-8", "replace").strip()[:200])
    os.chmod(destination, MODE_FICHIER)


def dechiffrer(cle, source, destination, iv):
    verifier_openssl()
    enc = deriver(cle, ETIQUETTE_ENC)
    commande = ["openssl", "enc", "-d", "-aes-256-cbc", "-K", enc.hex(),
                "-iv", iv.hex(), "-nosalt", "-in", str(source), "-out", str(destination)]
    resultat = subprocess.run(commande, capture_output=True)
    if resultat.returncode != 0:
        raise Erreur(3, "déchiffrement impossible (clé incorrecte ou archive altérée)")
    os.chmod(destination, MODE_FICHIER)


def calculer_mac(cle, iv, chemin_chiffre):
    mac = hmac.new(deriver(cle, ETIQUETTE_MAC), digestmod=hashlib.sha256)
    mac.update(iv)
    with open(chemin_chiffre, "rb") as flux:
        for bloc in iter(lambda: flux.read(1 << 20), b""):
            mac.update(bloc)
    return mac.hexdigest()


def sha256_fichier(chemin):
    empreinte = hashlib.sha256()
    with open(chemin, "rb") as flux:
        for bloc in iter(lambda: flux.read(1 << 20), b""):
            empreinte.update(bloc)
    return empreinte.hexdigest()


# --------------------------------------------------------------------------
# Préparation du contenu
# --------------------------------------------------------------------------

def copier_base_coherente(base, destination):
    """Copie la base par l'API SQLite : l'instantané est cohérent."""
    if not Path(base).is_file():
        raise Erreur(2, "base introuvable : %s" % base)
    source = sqlite3.connect(str(base))
    cible = sqlite3.connect(str(destination))
    try:
        source.backup(cible)
    finally:
        cible.close()
        source.close()
    os.chmod(destination, MODE_FICHIER)


def construire_manifeste(racine_prepa):
    fichiers = []
    for chemin in sorted(Path(racine_prepa).rglob("*")):
        if chemin.is_file() and chemin.name != NOM_MANIFESTE:
            relatif = chemin.relative_to(racine_prepa).as_posix()
            fichiers.append({
                "chemin": relatif,
                "sha256": sha256_fichier(chemin),
                "octets": chemin.stat().st_size,
            })
    return {"version": VERSION, "cree_le": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "fichiers": fichiers}


def ajouter_arbre(archive, source, prefixe):
    """Ajoute un arbre au tar en ignorant les fichiers parasites du système."""
    for chemin in sorted(Path(source).rglob("*")):
        if chemin.name in (".DS_Store",):
            continue
        if chemin.is_file():
            arcname = "%s/%s" % (prefixe, chemin.relative_to(source).as_posix())
            archive.add(str(chemin), arcname=arcname, recursive=False)


# --------------------------------------------------------------------------
# Commandes
# --------------------------------------------------------------------------

def commande_sauvegarder(args):
    cle = lire_cle(args.cle)
    # Politique de conservation de 24 h : les consultations peuvent être EXCLUES
    # des archives (--sans-dossiers), pour qu'aucune copie ne survive à la purge.
    dossiers = None if args.sans_dossiers else Path(args.dossiers).resolve()
    base = Path(args.base).resolve()
    sortie = Path(args.sortie).resolve()
    permanents = [Path(p).resolve() for p in (args.inclure or [])]

    if dossiers is not None and not dossiers.is_dir():
        raise Erreur(2, "répertoire de consultations introuvable : %s" % dossiers)
    noms_permanents = set()
    for chemin in permanents:
        if not chemin.exists():
            raise Erreur(2, "élément permanent introuvable : %s" % chemin)
        if chemin.name in noms_permanents:
            raise Erreur(2, "deux éléments permanents portent le même nom : %s" % chemin.name)
        noms_permanents.add(chemin.name)
    sortie.mkdir(parents=True, exist_ok=True, mode=MODE_DOSSIER)
    os.chmod(sortie, MODE_DOSSIER)

    travail = Path(tempfile.mkdtemp(prefix="sauvegarde-"))
    os.chmod(travail, MODE_DOSSIER)
    try:
        preparation = travail / "contenu"
        preparation.mkdir(mode=MODE_DOSSIER)
        if dossiers is not None:
            shutil.copytree(dossiers, preparation / "dossiers", symlinks=False)
        for chemin in permanents:
            destination = preparation / "permanent" / chemin.name
            destination.parent.mkdir(parents=True, exist_ok=True, mode=MODE_DOSSIER)
            if chemin.is_dir():
                shutil.copytree(chemin, destination, symlinks=False)
            else:
                shutil.copy2(chemin, destination)
        base_locale = preparation / "base" / base.name
        base_locale.parent.mkdir(parents=True, mode=MODE_DOSSIER)
        copier_base_coherente(base, base_locale)

        manifeste = construire_manifeste(preparation)
        (preparation / NOM_MANIFESTE).write_text(
            json.dumps(manifeste, ensure_ascii=False, indent=1), encoding="utf-8")

        paquet = travail / "paquet.tar.gz"
        with tarfile.open(paquet, "w:gz") as archive:
            for entree in sorted(preparation.iterdir()):
                if entree.name == NOM_MANIFESTE:
                    archive.add(str(entree), arcname=NOM_MANIFESTE, recursive=False)
                else:
                    ajouter_arbre(archive, entree, entree.name)
            # Le manifeste en dernier : il décrit ce qui précède.
            archive.add(str(preparation / NOM_MANIFESTE), arcname=NOM_MANIFESTE, recursive=False)
        os.chmod(paquet, MODE_FICHIER)

        horodatage = time.strftime("%Y%m%d-%H%M%S", time.gmtime())
        nom = "sauvegarde-%s-%s" % (horodatage, secrets.token_hex(4))
        chemin_chiffre = sortie / (nom + ".enc")
        chemin_entete = sortie / (nom + ".json")

        iv = os.urandom(16)
        chiffrer(cle, paquet, chemin_chiffre, iv)
        mac = calculer_mac(cle, iv, chemin_chiffre)

        entete = {
            "version": VERSION,
            "cree_le": manifeste["cree_le"],
            "algorithme": "aes-256-cbc+hmac-sha256",
            "iv": iv.hex(),
            "mac": mac,
            "octets_chiffre": chemin_chiffre.stat().st_size,
            "sha256_chiffre": sha256_fichier(chemin_chiffre),
            "nb_fichiers": len(manifeste["fichiers"]),
            "contient": {"dossiers": dossiers is not None, "base": base.name,
                         "permanent": sorted(noms_permanents)},
        }
        chemin_entete.write_text(json.dumps(entete, indent=1), encoding="utf-8")
        os.chmod(chemin_entete, MODE_FICHIER)

        print("sauvegarde : %s" % chemin_chiffre)
        print("  fichiers   : %d" % len(manifeste["fichiers"]))
        print("  chiffré    : %d octets" % entete["octets_chiffre"])
        print("  empreinte  : %s" % entete["sha256_chiffre"][:16])
        print("  en-tête    : %s" % chemin_entete.name)
        return 0
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def lire_entete(archive):
    chemin = Path(archive)
    if chemin.suffix == ".json":
        entete = chemin
    elif chemin.suffix == ".enc":
        entete = chemin.with_suffix(".json")
    else:
        entete = Path(str(chemin) + ".json")
    if not entete.is_file():
        raise Erreur(3, "en-tête introuvable : %s" % entete)
    try:
        donnees = json.loads(entete.read_text(encoding="utf-8"))
    except ValueError:
        raise Erreur(3, "en-tête illisible : %s" % entete)
    for cle in ("version", "iv", "mac", "sha256_chiffre"):
        if cle not in donnees:
            raise Erreur(3, "en-tête incomplet (champ « %s » absent)" % cle)
    return donnees, entete


def controler_archive(archive, entete):
    """Vérifie l'empreinte du chiffré puis le MAC. Échoue si altérée."""
    if not Path(archive).is_file():
        raise Erreur(3, "archive introuvable : %s" % archive)
    reel = sha256_fichier(archive)
    if reel != entete["sha256_chiffre"]:
        raise Erreur(3, "archive altérée : empreinte %s, attendue %s"
                     % (reel[:16], entete["sha256_chiffre"][:16]))


def commande_verifier(args):
    cle = lire_cle(args.cle)
    entete, _ = lire_entete(args.archive)
    controler_archive(args.archive, entete)
    iv = bytes.fromhex(entete["iv"])
    attendu = entete["mac"]
    calcule = calculer_mac(cle, iv, args.archive)
    if not hmac.compare_digest(attendu, calcule):
        raise Erreur(3, "MAC invalide : clé incorrecte ou archive altérée")
    print("archive valide : %s (%d fichiers, %d octets chiffrés)"
          % (Path(args.archive).name, entete["nb_fichiers"], entete["octets_chiffre"]))
    return 0


def extraire_surement(paquet, destination):
    """Extrait en refusant tout chemin sortant de la destination."""
    destination = Path(destination).resolve()
    with tarfile.open(paquet, "r:gz") as archive:
        for membre in archive.getmembers():
            if membre.issym() or membre.islnk():
                raise Erreur(3, "lien refusé dans l'archive : %s" % membre.name)
            cible = (destination / membre.name).resolve()
            if destination != cible and destination not in cible.parents:
                raise Erreur(3, "chemin hors destination refusé : %s" % membre.name)
        # Deuxième barrière, celle de la bibliothèque standard (Python 3.12+,
        # et correctifs de sécurité de 3.9 à 3.11) : refuse aussi les fichiers
        # spéciaux et les chemins absolus. Elle deviendra le défaut en 3.14.
        if hasattr(tarfile, "data_filter"):
            archive.extractall(destination, filter="data")
        else:
            archive.extractall(destination)


def commande_restaurer(args):
    cle = lire_cle(args.cle)
    entete, _ = lire_entete(args.archive)
    controler_archive(args.archive, entete)

    iv = bytes.fromhex(entete["iv"])
    if not hmac.compare_digest(entete["mac"], calculer_mac(cle, iv, args.archive)):
        raise Erreur(3, "MAC invalide : clé incorrecte ou archive altérée")

    if not (args.sortie or args.base_destination or args.permanent_destination):
        raise Erreur(2, "rien à restaurer : indiquer --sortie, --base-destination ou --permanent-destination")
    destinations = [Path(d).resolve() for d in (args.sortie, args.permanent_destination) if d]
    for destination in destinations:
        if destination.exists() and any(destination.iterdir()) and not args.ecraser:
            raise Erreur(5, "destination non vide : %s (utiliser --ecraser)" % destination)
    sortie = Path(args.sortie).resolve() if args.sortie else None

    travail = Path(tempfile.mkdtemp(prefix="restauration-"))
    os.chmod(travail, MODE_DOSSIER)
    try:
        paquet = travail / "paquet.tar.gz"
        dechiffrer(cle, args.archive, paquet, iv)
        extraire_surement(paquet, travail / "extrait")

        racine = travail / "extrait"
        manifeste = json.loads((racine / NOM_MANIFESTE).read_text(encoding="utf-8"))
        abimes = []
        for entree in manifeste["fichiers"]:
            chemin = racine / entree["chemin"]
            if not chemin.is_file():
                abimes.append("absent : %s" % entree["chemin"])
            elif sha256_fichier(chemin) != entree["sha256"]:
                abimes.append("empreinte différente : %s" % entree["chemin"])
        if abimes:
            raise Erreur(3, "restauration refusée : contenu incohérent (%d fichier(s)) — %s"
                         % (len(abimes), abimes[0]))

        # Les récits retrouvent des permissions privées, jamais celles de l'archive.
        if sortie is not None:
            if not (racine / "dossiers").is_dir():
                raise Erreur(3, "cette archive ne contient pas de consultations (--sans-dossiers)")
            sortie.mkdir(parents=True, exist_ok=True)
            shutil.copytree(racine / "dossiers", sortie, dirs_exist_ok=True)
            os.chmod(sortie, MODE_DOSSIER)
            for chemin in sortie.rglob("*"):
                os.chmod(chemin, MODE_DOSSIER if chemin.is_dir() else MODE_FICHIER)

        if args.permanent_destination:
            if not (racine / "permanent").is_dir():
                raise Erreur(3, "aucun élément permanent dans l'archive")
            cible_permanente = Path(args.permanent_destination).resolve()
            cible_permanente.mkdir(parents=True, exist_ok=True)
            shutil.copytree(racine / "permanent", cible_permanente, dirs_exist_ok=True)
            os.chmod(cible_permanente, MODE_DOSSIER)
            for chemin in cible_permanente.rglob("*"):
                os.chmod(chemin, MODE_DOSSIER if chemin.is_dir() else MODE_FICHIER)

        base_restauree = None
        if args.base_destination:
            origine = next((racine / "base").glob("*.sqlite3"), None)
            if origine is None:
                raise Erreur(3, "aucune base dans l'archive")
            cible = Path(args.base_destination)
            cible.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origine, cible)
            os.chmod(cible, MODE_FICHIER)
            base_restauree = cible

        print("restauration : %s" % (sortie or "(consultations non demandées)"))
        print("  fichiers vérifiés : %d" % len(manifeste["fichiers"]))
        if base_restauree:
            print("  base : %s" % base_restauree)
        return 0
    finally:
        shutil.rmtree(travail, ignore_errors=True)


def construire_analyseur():
    analyseur = argparse.ArgumentParser(description="Sauvegarde chiffrée et restauration vérifiée.")
    sous = analyseur.add_subparsers(dest="commande", required=True)

    s = sous.add_parser("sauvegarder", help="créer une archive chiffrée")
    s.add_argument("--sortie", required=True)
    choix = s.add_mutually_exclusive_group(required=True)
    choix.add_argument("--dossiers", help="répertoire des consultations à inclure")
    choix.add_argument("--sans-dossiers", action="store_true",
                       help="exclure les consultations (politique de conservation de 24 h)")
    s.add_argument("--base", required=True)
    s.add_argument("--inclure", action="append",
                   help="fichier ou répertoire permanent à inclure (configuration, journal d'audit) ; répétable")
    s.add_argument("--cle")
    s.set_defaults(fonction=commande_sauvegarder)

    v = sous.add_parser("verifier", help="contrôler une archive sans la restaurer")
    v.add_argument("--archive", required=True)
    v.add_argument("--cle")
    v.set_defaults(fonction=commande_verifier)

    r = sous.add_parser("restaurer", help="restaurer une archive dans un répertoire")
    r.add_argument("--archive", required=True)
    r.add_argument("--sortie", help="répertoire où restaurer les consultations (si l'archive en contient)")
    r.add_argument("--base-destination")
    r.add_argument("--permanent-destination", help="répertoire où restaurer les éléments permanents")
    r.add_argument("--cle")
    r.add_argument("--ecraser", action="store_true")
    r.set_defaults(fonction=commande_restaurer)
    return analyseur


def main(argv=None):
    args = construire_analyseur().parse_args(argv)
    try:
        return args.fonction(args)
    except Erreur as erreur:
        print("ERREUR : %s" % erreur, file=sys.stderr)
        return erreur.code


if __name__ == "__main__":
    sys.exit(main())
