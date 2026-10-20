#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Reconstruction CONTRÔLÉE de la base du corpus.

La base active n'est jamais modifiée en place :

  1. la base de départ est extraite d'une version enregistrée (`git show`) ;
  2. les intégrations OCR sont rejouées dans une COPIE TEMPORAIRE, par un
     processus séparé (MONRECOURS_CHEMIN_DB, MONRECOURS_JOURNAL_OCR) ;
  3. la copie subit les contrôles ci-dessous ;
  4. seulement si TOUT passe, et avec --remplacer : la base active est
     sauvegardée (KNOWLEDGE/.sauvegardes/, empreinte dans le nom), puis
     remplacée atomiquement, avec le journal d'intégration.

Contrôles (tous bloquants) :
  * PRAGMA integrity_check = ok, PRAGMA foreign_key_check vide ;
  * empreinte de chaque article recalculée = empreinte enregistrée ;
  * aucune référence NOUVELLE munie d'un extrait sans article indexé ;
  * pour chaque référence intégrée, chaque article indexé figure dans l'extrait ;
  * nombre d'articles par document = journal d'intégration ;
  * corpus.verifier_integrite (mode « PDF non distribués » toléré) sans altération ;
  * catalogue et guide de questions revalidés contre la copie.

    python3 bin/reconstruire_base.py --depart 1ca6e7f --cle <clé> [--cle ...] [--remplacer]
"""

import argparse
import datetime
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE_ACTIVE = os.path.join(RACINE, "KNOWLEDGE", "corpus_juridique.sqlite3")
JOURNAL_ACTIF = os.path.join(RACINE, "KNOWLEDGE", "collecte", "integrations_ocr.json")
SAUVEGARDES = os.path.join(RACINE, "KNOWLEDGE", ".sauvegardes")
RAPPORT = os.path.join(RACINE, "KNOWLEDGE", "collecte", "reconstruction_base.json")


def sha256(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as flux:
        for bloc in iter(lambda: flux.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()


def base_de_depart(revision, cible):
    contenu = subprocess.run(["git", "-C", RACINE, "show", "%s:KNOWLEDGE/corpus_juridique.sqlite3" % revision],
                             check=True, capture_output=True).stdout
    with open(cible, "wb") as flux:
        flux.write(contenu)


def integrer(cles, base, journal):
    env = dict(os.environ, MONRECOURS_CHEMIN_DB=base, MONRECOURS_JOURNAL_OCR=journal)
    commande = [sys.executable, os.path.join(RACINE, "bin", "integrer_collecte.py"), "officialiser_ocr"]
    for cle in cles:
        commande += ["--cle", cle]
    sortie = subprocess.run(commande, env=env, capture_output=True, text=True, cwd=RACINE)
    if sortie.returncode != 0:
        raise SystemExit("intégration en échec :\n" + sortie.stdout[-2000:] + sortie.stderr[-3000:])
    bilan = [l for l in sortie.stdout.splitlines() if l.strip()]
    return bilan


def controler(base, journal, depart):
    """Renvoie (liste des contrôles {nom, ok, detail})."""
    controles = []

    def noter(nom, ok, detail=""):
        controles.append({"controle": nom, "ok": bool(ok), "detail": detail})

    conn = sqlite3.connect(base)
    conn.row_factory = sqlite3.Row
    noter("PRAGMA integrity_check", conn.execute("PRAGMA integrity_check").fetchone()[0] == "ok")
    fk = conn.execute("PRAGMA foreign_key_check").fetchall()
    noter("PRAGMA foreign_key_check", not fk, "%d violation(s)" % len(fk))

    faux = []
    for ligne in conn.execute("SELECT article_id, texte, sha256_article FROM articles_corpus"):
        if "sha256:" + hashlib.sha256((ligne["texte"] or "").encode("utf-8")).hexdigest() != ligne["sha256_article"]:
            faux.append(ligne["article_id"])
    noter("empreintes des articles recalculées", not faux, "%d écart(s)" % len(faux))

    avant = sqlite3.connect(depart)
    refs_avant = {r[0] for r in avant.execute("SELECT ref_id FROM references_juridiques")}
    orphelines = [r["ref_id"] for r in conn.execute(
        "SELECT ref_id, extrait_texte FROM references_juridiques r WHERE coalesce(extrait_texte, '') != ''"
        " AND NOT EXISTS (SELECT 1 FROM articles_corpus a WHERE a.ref_id = r.ref_id)")
        if r["ref_id"] not in refs_avant]
    noter("aucune référence nouvelle avec un extrait non indexé", not orphelines, ", ".join(orphelines))

    entrees = (json.load(open(journal, encoding="utf-8")) if os.path.isfile(journal) else {"integrations": {}})
    absents, ecarts_compte = [], []
    for cle, entree in entrees["integrations"].items():
        nombre = conn.execute("SELECT count(*) FROM articles_corpus WHERE doc_id = ?", (entree["doc_id"],)).fetchone()[0]
        if nombre != entree["articles_indexes"]:
            ecarts_compte.append("%s : base %d / journal %d" % (cle, nombre, entree["articles_indexes"]))
        extrait = conn.execute("SELECT extrait_texte FROM references_juridiques WHERE ref_id = ?",
                               (entree["ref_id"],)).fetchone()[0] or ""
        for numero, texte in conn.execute("SELECT numero, texte FROM articles_corpus WHERE doc_id = ?",
                                          (entree["doc_id"],)):
            if texte not in extrait:
                absents.append("%s art. %s" % (cle, numero))
    noter("articles indexés = journal d'intégration", not ecarts_compte, "; ".join(ecarts_compte))
    noter("chaque article intégré figure dans l'extrait de sa référence", not absents,
          "%d absent(s) %s" % (len(absents), absents[:5]))
    conn.close()

    # Contrôles du moteur, dans un processus qui ne voit QUE la copie.
    script = (
        "import json, sys; sys.path.insert(0, %r)\n"
        "from core import corpus, catalogue, clarification\n"
        "r = corpus.verifier_integrite()\n"
        "fiches = catalogue.charger()\n"
        "guide = clarification.charger(fiches)\n"
        "print(json.dumps({'alteres': len(r['alteres']), 'absents': len(r['absents']), 'documents': r['nb_documents'],"
        " 'fiches': len(fiches), 'questions': len(guide['questions'])}))\n") % RACINE
    env = dict(os.environ, MONRECOURS_CHEMIN_DB=base, MONRECOURS_PDF_NON_DISTRIBUES="1")
    sortie = subprocess.run([sys.executable, "-c", script], env=env, capture_output=True, text=True, cwd=RACINE)
    if sortie.returncode != 0:
        noter("moteur : intégrité, catalogue, guide", False, sortie.stderr.strip().splitlines()[-1][:400])
    else:
        mesure = json.loads(sortie.stdout.strip().splitlines()[-1])
        noter("intégrité des documents (verifier_integrite)", mesure["alteres"] == 0 and mesure["absents"] == 0,
              json.dumps(mesure, ensure_ascii=False))
        noter("catalogue et guide revalidés contre la copie", mesure["fiches"] > 0,
              "%d fiches, %d questions" % (mesure["fiches"], mesure["questions"]))
    return controles


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--depart", required=True, help="révision git de la base de départ")
    analyseur.add_argument("--cle", action="append", required=True)
    analyseur.add_argument("--remplacer", action="store_true")
    arguments = analyseur.parse_args(argv)

    dossier = tempfile.mkdtemp(prefix="reconstruction_")
    depart = os.path.join(dossier, "depart.sqlite3")
    base = os.path.join(dossier, "corpus.sqlite3")
    journal = os.path.join(dossier, "integrations_ocr.json")
    base_de_depart(arguments.depart, depart)
    shutil.copyfile(depart, base)
    bilan = integrer(arguments.cle, base, journal)
    controles = controler(base, journal, depart)
    tout_ok = all(c["ok"] for c in controles)
    rapport = {
        "objet": "Reconstruction contrôlée de la base (bin/reconstruire_base.py)",
        "date": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
        "depart": {"revision": arguments.depart, "sha256": sha256(depart)},
        "base_active_avant": {"sha256": sha256(BASE_ACTIVE)},
        "integrations_demandees": arguments.cle,
        "bilan_integration": bilan,
        "controles": controles,
        "resultat": "CONTROLES_REUSSIS" if tout_ok else "CONTROLES_EN_ECHEC",
        "base_reconstruite": {"sha256": sha256(base)},
        "remplacement": None,
    }
    for c in controles:
        print("%-4s %-58s %s" % ("OK" if c["ok"] else "ÉCHEC", c["controle"], c["detail"][:120]))
    if tout_ok and arguments.remplacer:
        os.makedirs(SAUVEGARDES, exist_ok=True)
        horodatage = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        sauvegarde = os.path.join(SAUVEGARDES, "corpus_%s_%s.sqlite3" % (horodatage, sha256(BASE_ACTIVE)[:12]))
        shutil.copyfile(BASE_ACTIVE, sauvegarde)
        if os.path.isfile(JOURNAL_ACTIF):
            shutil.copyfile(JOURNAL_ACTIF, sauvegarde.replace(".sqlite3", "_integrations_ocr.json"))
        if sha256(sauvegarde) != rapport["base_active_avant"]["sha256"]:
            raise SystemExit("sauvegarde non conforme : remplacement annulé")
        os.replace(base, BASE_ACTIVE)
        shutil.copyfile(journal, JOURNAL_ACTIF)
        rapport["remplacement"] = {"sauvegarde": os.path.relpath(sauvegarde, RACINE),
                                   "base_active_apres": sha256(BASE_ACTIVE)}
        print("Base active remplacée ; sauvegarde : %s" % rapport["remplacement"]["sauvegarde"])
    elif not tout_ok:
        print("Contrôles en échec : base active INCHANGÉE (copie conservée dans %s)" % dossier)
    else:
        print("Simulation : base active inchangée (copie dans %s)" % dossier)
    with open(RAPPORT, "w", encoding="utf-8") as flux:
        json.dump(rapport, flux, ensure_ascii=False, indent=1)
        flux.write("\n")
    return 0 if tout_ok else 1


if __name__ == "__main__":
    sys.exit(main())
