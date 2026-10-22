#!/usr/bin/env bash
# État d'un poste de travail Mon Recours CI — LECTURE SEULE.
#
#   bash scripts/etat-poste.sh            # depuis la racine du dépôt (ex. /Users/mac/mon_recours_ci)
#
# Ne modifie rien, ne supprime rien, ne contacte aucun serveur (pas de git fetch).
# N'affiche AUCUN contenu de consultation : pour DOSSIERS/, seulement des
# compteurs, des tailles et des dates. Aucun secret n'est lu ni affiché :
# pour les fichiers .env, seule leur présence est signalée.
#
# Copier toute la sortie et la transmettre telle quelle.

set -u
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE" || exit 1
titre() { printf '\n== %s ==\n' "$1"; }
# Droits d'un fichier, sous Linux (GNU) comme sous macOS (BSD).
droits() { stat -c '%a' "$1" 2>/dev/null || stat -f '%Lp' "$1" 2>/dev/null; }

titre "Poste"
echo "date        : $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "système     : $(uname -sr)"
echo "racine      : $RACINE"

titre "Git (état local, sans réseau)"
echo "branche     : $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
echo "commit      : $(git log -1 --format='%h %ci %s' 2>/dev/null)"
echo "modifiés    : $(git status --porcelain 2>/dev/null | grep -vc '^??') fichier(s) suivis"
echo "non suivis  : $(git status --porcelain 2>/dev/null | grep -c '^??') fichier(s) (hors .gitignore)"
git status --porcelain 2>/dev/null | head -40 | sed 's/^/   /'
echo "remises (stash) : $(git stash list 2>/dev/null | wc -l | tr -d ' ')"
echo "branches locales et avance sur leur branche distante :"
git for-each-ref --format='%(refname:short)|%(upstream:short)|%(upstream:track)' refs/heads 2>/dev/null \
  | while IFS='|' read -r b u t; do printf '   %-40s %-48s %s\n' "$b" "${u:-(aucune branche distante)}" "${t:-à jour ou inconnu}"; done
echo "commits locaux absents de toute branche distante connue :"
git log --branches --not --remotes --format='   %h %ci %s' 2>/dev/null | head -30

titre "Outils"
echo "python3     : $(python3 --version 2>&1)"
python3 -c 'import fpdf; print("fpdf2       :", fpdf.__version__)' 2>/dev/null || echo "fpdf2       : ABSENT (python3 -m pip install -r requirements.txt)"
for v in .venv .venv-corpus; do [ -x "$v/bin/python" ] && echo "venv $v : présent ($("$v/bin/python" --version 2>&1)), fpdf2 : $("$v/bin/python" -c 'import fpdf;print(fpdf.__version__)' 2>/dev/null || echo absent)"; done
echo "node        : $(node --version 2>&1)"
echo "npm         : $(npm --version 2>&1)"
for o in tesseract pdftotext swiftc openssl; do printf '%-11s : %s\n' "$o" "$(command -v "$o" >/dev/null && echo présent || echo absent)"; done
[ -d web/node_modules ] && echo "web/node_modules : présent" || echo "web/node_modules : absent"

titre "Configuration locale (présence seulement, aucune valeur lue)"
for f in web/.env.local web/.env .env; do [ -e "$f" ] && echo "$f : présent (droits $(droits "$f"))"; done
echo "(fin de la liste)"

titre "Corpus"
echo "PDF dans KNOWLEDGE/CORPUS : $(find KNOWLEDGE/CORPUS -name '*.pdf' 2>/dev/null | wc -l | tr -d ' ')"
python3 - <<'PY' 2>/dev/null || echo "base : lecture impossible"
import hashlib, sqlite3
chemin = "KNOWLEDGE/corpus_juridique.sqlite3"
c = sqlite3.connect("file:%s?mode=ro" % chemin, uri=True)
print("base        : %s documents, %s articles, intégrité %s" % (
    c.execute("select count(*) from documents").fetchone()[0],
    c.execute("select count(*) from articles_corpus").fetchone()[0],
    c.execute("pragma integrity_check").fetchone()[0]))
print("sha256 base : %s…" % hashlib.sha256(open(chemin, "rb").read()).hexdigest()[:16])
PY
echo "sauvegardes de base (KNOWLEDGE/.sauvegardes) : $(ls KNOWLEDGE/.sauvegardes 2>/dev/null | wc -l | tr -d ' ')"

titre "DOSSIERS/ (compteurs seulement, aucun contenu)"
if [ -d DOSSIERS ]; then
  echo "dossiers au total : $(find DOSSIERS -mindepth 1 -maxdepth 1 -type d | wc -l | tr -d ' ')"
  echo "  dont web-* (interface)   : $(find DOSSIERS -mindepth 1 -maxdepth 1 -type d -name 'web-*' | wc -l | tr -d ' ')"
  echo "  dont autres (tests, CLI) : $(find DOSSIERS -mindepth 1 -maxdepth 1 -type d ! -name 'web-*' | wc -l | tr -d ' ')"
  echo "fichiers          : $(find DOSSIERS -type f | wc -l | tr -d ' ')"
  echo "taille            : $(du -sh DOSSIERS 2>/dev/null | cut -f1)"
  python3 - <<'PY'
import os, time
dates = [os.path.getmtime(os.path.join(r, f)) for r, _, fs in os.walk("DOSSIERS") for f in fs]
if dates:
    print("plus ancienne modification : " + time.strftime("%Y-%m-%d", time.gmtime(min(dates))))
    print("plus récente modification  : " + time.strftime("%Y-%m-%d", time.gmtime(max(dates))))
PY
  echo "droits de DOSSIERS : $(droits DOSSIERS) (attendu 700)"
else
  echo "DOSSIERS/ absent"
fi

titre "Fin — rien n'a été modifié"
