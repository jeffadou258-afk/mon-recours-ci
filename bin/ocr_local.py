#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OCR dans l'espace de travail, avec le modèle français « tessdata_best ».

Le runner GitHub Actions lit les scans avec le paquet Ubuntu tesseract-ocr-fra
(modèle rapide, 200 dpi par défaut). Pour les scans médiocres du Journal
officiel, ce script produit une SECONDE lecture, indépendante par le modèle et la
résolution, à partir du PDF rapatrié de corpus/archives-pdf (empreinte
recalculée avant lecture : aucun fichier non vérifié n'est lu).

Il écrit :
  * KNOWLEDGE/collecte/textes/<clé>.ocr_best.txt (mêmes marqueurs de page) ;
  * un bloc `extraction_locale` dans resultats/<clé>.json : modèle et son
    empreinte, résolution, confiance par page, pages faibles.
Il ne modifie ni le PDF, ni la lecture distante, ni la base du corpus.

    TESSDATA_BEST=/chemin/vers/tessdata_best python3 bin/ocr_local.py --cle <clé> [--dpi 300]
"""

import argparse
import concurrent.futures
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOSSIER = os.path.join(RACINE, "KNOWLEDGE", "collecte")
RESULTATS = os.path.join(DOSSIER, "resultats")
TEXTES = os.path.join(DOSSIER, "textes")
PDF = os.path.join(DOSSIER, "pdf")
TESSDATA_MODELES = {"best": os.environ.get("TESSDATA_BEST", "/home/claude/tessdata/best"),
                    "fast": os.environ.get("TESSDATA_FAST", "/home/claude/tessdata/fast")}
TESSDATA = TESSDATA_MODELES["best"]


def sha256_fichier(chemin):
    h = hashlib.sha256()
    with open(chemin, "rb") as flux:
        for bloc in iter(lambda: flux.read(1 << 20), b""):
            h.update(bloc)
    return "sha256:" + h.hexdigest()


def ocr_page(chemin, numero, dossier, dpi, psm, tessdata=None):
    base = os.path.join(dossier, "p%04d" % numero)
    subprocess.run(["pdftoppm", "-f", str(numero), "-l", str(numero), "-r", str(dpi), "-gray", "-png",
                    "-singlefile", chemin, base], check=True, capture_output=True)
    image = base + ".png"
    env = dict(os.environ, TESSDATA_PREFIX=tessdata or TESSDATA, OMP_THREAD_LIMIT="1")
    sortie = subprocess.run(["tesseract", image, "-", "-l", "fra", "--psm", str(psm),
                             "-c", "tessedit_create_tsv=1"], capture_output=True, env=env, timeout=900).stdout
    os.remove(image)
    lignes, confiances, cle, courant = [], [], None, []
    for rang, brut in enumerate(sortie.decode("utf-8", "replace").splitlines()):
        champs = brut.split("\t")
        if rang == 0 or len(champs) < 12 or champs[0] != "5":
            continue
        identifiant = (champs[2], champs[3], champs[4])
        if identifiant != cle and courant:
            lignes.append(" ".join(courant))
            courant = []
        cle = identifiant
        if champs[11].strip():
            courant.append(champs[11])
            try:
                if float(champs[10]) >= 0:
                    confiances.append(float(champs[10]))
            except ValueError:
                pass
    if courant:
        lignes.append(" ".join(courant))
    return "\n".join(lignes), (round(sum(confiances) / len(confiances), 1) if confiances else None)


def traiter(cle, dpi=300, psm=3, travailleurs=None, modele="best"):
    chemin_resultat = os.path.join(RESULTATS, cle + ".json")
    resultat = json.load(open(chemin_resultat, encoding="utf-8"))
    chemin_pdf = os.path.join(PDF, resultat["fichier_pdf"])
    if sha256_fichier(chemin_pdf) != resultat["sha256"]:
        raise SystemExit("%s : empreinte du PDF différente de celle du téléchargement — lecture refusée" % cle)
    pages = int(resultat["extraction"]["pages"])
    tessdata = TESSDATA_MODELES[modele]
    suffixe = "" if modele == "best" else "_" + modele
    chemin_modele = os.path.join(tessdata, "fra.traineddata")
    version = subprocess.run(["tesseract", "--version"], capture_output=True, text=True).stdout.splitlines()[0]
    dossier = tempfile.mkdtemp(prefix="ocr_" + cle[:20])
    lectures = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=travailleurs or os.cpu_count() or 2) as executeur:
        futurs = {executeur.submit(ocr_page, chemin_pdf, n, dossier, dpi, psm, tessdata): n for n in range(1, pages + 1)}
        for futur in concurrent.futures.as_completed(futurs):
            lectures[futurs[futur]] = futur.result()
    shutil.rmtree(dossier, ignore_errors=True)
    morceaux = ["--- PAGE %d --- [OCR conf=%s]\n%s" % (n, lectures[n][1], lectures[n][0]) for n in range(1, pages + 1)]
    os.makedirs(TEXTES, exist_ok=True)
    chemin_texte = os.path.join(TEXTES, cle + ".ocr_%s.txt" % modele)
    with open(chemin_texte, "w", encoding="utf-8") as flux:
        flux.write("\n".join(morceaux))
    confiances = [c for _, c in lectures.values() if c is not None]
    resultat["extraction_locale" + suffixe] = {
        "lieu": "espace de travail Claude (session du %s)" % datetime.date.today().isoformat(),
        "outil": version, "modele": "tessdata_%s fra.traineddata" % modele,
        "sha256_modele": sha256_fichier(chemin_modele), "dpi": dpi, "psm": psm,
        "pdf_verifie": resultat["sha256"], "pages": pages,
        "fichier_ocr": os.path.relpath(chemin_texte, RACINE),
        "sha256_ocr": sha256_fichier(chemin_texte),
        "confiance_ocr_moyenne": round(sum(confiances) / len(confiances), 1) if confiances else None,
        "confiance_par_page": {str(n): lectures[n][1] for n in sorted(lectures)},
        "pages_ocr_faibles": sorted(n for n, (_, c) in lectures.items() if c is None or c < 70),
        "date": datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat(),
    }
    with open(chemin_resultat, "w", encoding="utf-8") as flux:
        json.dump(resultat, flux, ensure_ascii=False, indent=1, sort_keys=True)
    print("%s [%s] : %d pages, confiance %s (distante : %s)" % (
        cle, modele, pages, resultat["extraction_locale" + suffixe]["confiance_ocr_moyenne"],
        resultat["extraction"].get("confiance_ocr_moyenne")))


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    analyseur.add_argument("--cle", action="append", required=True)
    analyseur.add_argument("--dpi", type=int, default=300)
    analyseur.add_argument("--psm", type=int, default=3)
    analyseur.add_argument("--modele", choices=sorted(TESSDATA_MODELES), default="best")
    arguments = analyseur.parse_args(argv)
    for cle in arguments.cle:
        traiter(cle, arguments.dpi, arguments.psm, modele=arguments.modele)
    return 0


if __name__ == "__main__":
    sys.exit(main())
