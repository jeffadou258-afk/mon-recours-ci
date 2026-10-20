# -*- coding: utf-8 -*-
"""Enregistre chaque exécution de la suite dans un historique comparable.

    python3 bin/enregistrer_tests.py                  # lance la suite et enregistre
    python3 bin/enregistrer_tests.py --etiquette ci   # étiquette libre
    python3 bin/enregistrer_tests.py --historique     # relit l'historique (10 derniers)
    python3 bin/enregistrer_tests.py --analyser /tmp/log.txt   # analyse un log existant

POURQUOI CET OUTIL
------------------
`tests/run_all.py` est la référence : il imprime `TESTS=… FAIL=… ERR=… SKIP=…` et
sort en code non nul en cas d'échec. Mais son résultat n'était conservé nulle part :
`KNOWLEDGE/collecte/derniers_tests.log` était écrasé à chaque exécution, et l'artefact
de CI ne contenait pas la sortie du moteur. Impossible, dans ces conditions, de dire
« ce nombre a baissé » ou « ce test échouait déjà hier ».

Cet outil **n'exécute pas les tests lui-même** : il appelle `tests/run_all.py` tel quel,
lit sa sortie, et ajoute UNE ligne à `KNOWLEDGE/qualite/historique_tests.jsonl`.
Il ne modifie ni les tests, ni la base, ni le corpus.

CODE DE SORTIE
--------------
Il vaut celui de la suite. Un enregistreur qui rendrait `0` après un échec
transformerait une CI rouge en CI verte — c'est exactement ce qu'il ne doit pas faire.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORIQUE = os.path.join(RACINE, "KNOWLEDGE", "qualite", "historique_tests.jsonl")
JOURNAL_BRUT = os.path.join(RACINE, "KNOWLEDGE", "qualite", "derniere_execution.log")
RESUME = re.compile(r"^TESTS=(\d+)\s+FAIL=(\d+)\s+ERR=(\d+)\s+SKIP=(\d+)\s+SUCCES=(\d+)", re.M)
VERDICT = re.compile(r"^VERDICT=(\S+)", re.M)
ECHEC = re.compile(r"^(FAIL|ERROR): (\S+)", re.M)
IGNORE = re.compile(r"^(\S+) \(\S+\) \.\.\. skipped", re.M)


def _git(*arguments):
    try:
        return subprocess.run(["git", "-C", RACINE] + list(arguments),
                              capture_output=True, text=True, check=True).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def etat_git():
    sale = _git("status", "--porcelain")
    return {"commit": _git("rev-parse", "HEAD")[:40],
            "branche": _git("rev-parse", "--abbrev-ref", "HEAD"),
            "arbre_sale": bool(sale),
            "fichiers_modifies": len([l for l in sale.splitlines() if l.strip()])}


def analyser(sortie):
    """Extrait les chiffres, les noms d'échecs et les tests ignorés d'une sortie de suite."""
    resume = RESUME.search(sortie or "")
    verdict = VERDICT.search(sortie or "")
    echecs = ["%s %s" % (m.group(1), m.group(2)) for m in ECHEC.finditer(sortie or "")]
    ignores = [m.group(1) for m in IGNORE.finditer(sortie or "")]
    resultat = {"verdict": verdict.group(1) if verdict else None,
                "tests_en_echec": echecs, "tests_ignores": ignores}
    if resume:
        resultat.update({"tests": int(resume.group(1)), "echecs": int(resume.group(2)),
                         "erreurs": int(resume.group(3)), "ignores": int(resume.group(4)),
                         "succes": int(resume.group(5))})
    else:
        resultat.update({"tests": None, "echecs": None, "erreurs": None,
                         "ignores": None, "succes": None})
    return resultat


def comparer(entree, precedente):
    """Écarts avec l'exécution précédente. Ne conclut pas à une régression sans preuve."""
    if not precedente:
        return {"comparaison": ["premiere_execution"]}
    constats = []
    if entree.get("tests") and precedente.get("tests"):
        if entree["tests"] < precedente["tests"]:
            constats.append("BAISSE du nombre de tests : %d < %d"
                            % (entree["tests"], precedente["tests"]))
        elif entree["tests"] > precedente["tests"]:
            constats.append("hausse du nombre de tests : %d > %d"
                            % (entree["tests"], precedente["tests"]))
    avant = (precedente.get("echecs") or 0) + (precedente.get("erreurs") or 0)
    apres = (entree.get("echecs") or 0) + (entree.get("erreurs") or 0)
    if apres > avant:
        constats.append("NOUVELLE REGRESSION : %d echec(s) contre %d" % (apres, avant))
    elif apres == 0 and avant > 0:
        constats.append("regression corrigee : %d -> 0" % avant)
    return {"comparaison": constats or ["aucun ecart"], "execution_precedente": {
        "date": precedente.get("date"), "commit": (precedente.get("commit") or "")[:8]}}


def dernier():
    if not os.path.isfile(HISTORIQUE):
        return None
    derniere = None
    with open(HISTORIQUE, encoding="utf-8") as flux:
        for ligne in flux:
            ligne = ligne.strip()
            if ligne:
                try:
                    derniere = json.loads(ligne)
                except ValueError:
                    continue
    return derniere


def enregistrer(entree):
    os.makedirs(os.path.dirname(HISTORIQUE), exist_ok=True)
    with open(HISTORIQUE, "a", encoding="utf-8") as flux:
        flux.write(json.dumps(entree, ensure_ascii=False) + "\n")


def afficher(entree):
    print("Tests        : %s" % (entree.get("tests") if entree.get("tests") is not None
                                else "INDISPONIBLE"))
    print("Succes/Echecs: %s / %s (erreurs %s, ignores %s)"
          % (entree.get("succes"), entree.get("echecs"), entree.get("erreurs"),
             entree.get("ignores")))
    print("Verdict      : %s | code de sortie : %s"
          % (entree.get("verdict"), entree.get("code_sortie")
             if entree.get("code_sortie") is not None else "non mesuré"))
    print("Duree        : %s" % ("%ss" % entree["duree_s"] if entree.get("duree_s") is not None
                                else "non mesurée"))
    print("Contexte     : %s @ %s%s" % (entree.get("branche"), (entree.get("commit") or "")[:8],
                                      " (arbre SALE)" if entree.get("arbre_sale") else ""))
    for echec in entree.get("tests_en_echec") or []:
        print("  ECHEC      : %s" % echec)
    for ignore in entree.get("tests_ignores") or []:
        print("  IGNORE     : %s" % ignore)
    for constat in (entree.get("regression") or {}).get("comparaison") or []:
        print("  COMPARAISON: %s" % constat)


def main(argv=None):
    analyseur = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    analyseur.add_argument("--etiquette", default="local",
                           help="origine de l'exécution (local, ci, avant-lot…)")
    analyseur.add_argument("--historique", action="store_true",
                           help="affiche les dernières exécutions enregistrées")
    analyseur.add_argument("--analyser", metavar="FICHIER",
                           help="analyse une sortie de suite déjà capturée, sans relancer")
    analyseur.add_argument("--sans-enregistrer", action="store_true")
    arguments = analyseur.parse_args(argv)

    if arguments.historique:
        if not os.path.isfile(HISTORIQUE):
            print("Aucun historique : %s" % os.path.relpath(HISTORIQUE, RACINE))
            return 1
        with open(HISTORIQUE, encoding="utf-8") as flux:
            lignes = [json.loads(l) for l in flux if l.strip()]
        for entree in lignes[-10:]:
            print("%s  %-8s tests=%-4s echecs=%-2s err=%-2s ign=%-2s %6ss  %s"
                  % (entree.get("date"), entree.get("etiquette"), entree.get("tests"),
                     entree.get("echecs"), entree.get("erreurs"), entree.get("ignores"),
                     entree.get("duree_s"), entree.get("verdict")))
        print("\n%d execution(s) enregistree(s) : %s"
              % (len(lignes), os.path.relpath(HISTORIQUE, RACINE)))
        return 0

    if arguments.analyser:
        with open(arguments.analyser, encoding="utf-8", errors="replace") as flux:
            sortie = flux.read()
        resultat = analyser(sortie)
        entree = dict(resultat, date=datetime.datetime.now(datetime.timezone.utc)
                      .replace(microsecond=0).isoformat(), etiquette=arguments.etiquette,
                      code_sortie=None, duree_s=None, **etat_git())
        entree["regression"] = comparer(entree, dernier())
        if not arguments.sans_enregistrer:
            enregistrer(entree)
        afficher(entree)
        return 0 if resultat.get("verdict") == "SUCCES" else 1

    env = dict(os.environ)
    env.setdefault("MONRECOURS_PDF_NON_DISTRIBUES", "1")
    debut = datetime.datetime.now(datetime.timezone.utc)
    try:
        processus = subprocess.run([sys.executable, "tests/run_all.py"], cwd=RACINE,
                                   capture_output=True, text=True, timeout=3600, env=env)
        sortie = (processus.stdout or "") + (processus.stderr or "")
        code = processus.returncode
    except subprocess.TimeoutExpired as expiration:
        sortie = (expiration.stdout or "") if isinstance(expiration.stdout, str) else ""
        code = 124
    duree = (datetime.datetime.now(datetime.timezone.utc) - debut).total_seconds()

    resultat = analyser(sortie)
    try:
        os.makedirs(os.path.dirname(JOURNAL_BRUT), exist_ok=True)
        with open(JOURNAL_BRUT, "w", encoding="utf-8") as flux:
            flux.write(sortie)
    except OSError:
        pass
    entree = dict(resultat, date=debut.replace(microsecond=0).isoformat(),
                  etiquette=arguments.etiquette, code_sortie=code,
                  duree_s=round(duree, 1), mode_pdf_non_distribues=env["MONRECOURS_PDF_NON_DISTRIBUES"],
                  **etat_git())
    entree["regression"] = comparer(entree, dernier())
    enregistrer(entree)
    afficher(entree)
    print("\nEnregistre : %s" % os.path.relpath(HISTORIQUE, RACINE))

    # Le code de sortie est celui de la suite : un echec ne doit jamais devenir un succes.
    if resultat.get("verdict") != "SUCCES" and code == 0:
        return 1
    return code


if __name__ == "__main__":
    sys.exit(main())
