#!/usr/bin/env bash
# Démarrer Mon Recours CI en local (Mac ou Linux), moteur ET interface.
#
#   bash scripts/demarrer-local.sh            # démarre tout
#   bash scripts/demarrer-local.sh --tests    # lance d'abord tous les contrôles
#
# Ce que fait ce script, et rien d'autre :
#   1. vérifie Python (3.9+) et Node (20.9+) ;
#   2. crée web/.env.local avec des clés TIRÉES AU HASARD s'il n'existe pas
#      (fichier ignoré par Git, droits 600) ; ne touche jamais un fichier existant ;
#   3. installe les dépendances web si besoin (sans exécuter de scripts d'installation) ;
#   4. démarre le moteur sur 127.0.0.1:8765 et l'interface sur http://localhost:3000 ;
#   5. arrête les deux proprement avec Ctrl-C.
# Rien n'est exposé sur le réseau : tout écoute sur la machine locale.

set -euo pipefail
RACINE="$(cd "$(dirname "$0")/.." && pwd)"
cd "$RACINE"

rouge() { printf '\033[31m%s\033[0m\n' "$*"; }
vert() { printf '\033[32m%s\033[0m\n' "$*"; }

# 1. Outils
command -v python3 >/dev/null || { rouge "Python 3 introuvable."; exit 1; }
python3 -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' \
  || { rouge "Python 3.9 ou plus récent est requis."; exit 1; }
command -v node >/dev/null || { rouge "Node.js introuvable (version 20.9 ou plus)."; exit 1; }
node -e 'const [a,b]=process.versions.node.split(".").map(Number); process.exit(a>20||(a===20&&b>=9)?0:1)' \
  || { rouge "Node.js 20.9 ou plus récent est requis."; exit 1; }

# PDF officiels : non versionnés. S'ils sont absents (copie fraîche du dépôt),
# le moteur vérifie les empreintes des textes extraits à la place.
if ! find KNOWLEDGE/CORPUS -name '*.pdf' -print -quit 2>/dev/null | grep -q .; then
  export MONRECOURS_PDF_NON_DISTRIBUES=1
  echo "PDF officiels absents : contrôle d'intégrité sur les textes extraits (mode déclaré)."
fi

# 2. Clés locales
ENV_WEB="web/.env.local"
if [ ! -f "$ENV_WEB" ]; then
  CLE=$(python3 -c 'import secrets; print(secrets.token_urlsafe(24))')
  SECRET=$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')
  umask 077
  cat > "$ENV_WEB" <<EOF
MONRECOURS_API_URL=http://127.0.0.1:8765
MONRECOURS_API_KEY=$CLE
MONRECOURS_SESSION_SECRET=$SECRET
EOF
  vert "Clés locales créées dans $ENV_WEB (ignoré par Git)."
fi
MONRECOURS_API_KEY=$(grep '^MONRECOURS_API_KEY=' "$ENV_WEB" | cut -d= -f2-)
export MONRECOURS_API_KEY

# 3. Dépendances web
if [ ! -d web/node_modules/next ]; then
  echo "Installation des dépendances web (scripts d'installation désactivés)…"
  (cd web && if [ -f package-lock.json ]; then npm ci --ignore-scripts --no-fund; else npm install --ignore-scripts --no-fund; fi)
fi

if [ "${1:-}" = "--tests" ]; then
  echo "== Tests du moteur"; python3 tests/run_all.py | tail -4
  echo "== Contrôles de l'interface"; (cd web && bash scripts/controle-complet.sh)
fi

# 4. Démarrage
python3 bin/serveur_api.py --port 8765 &
PID_MOTEUR=$!
trap 'kill $PID_MOTEUR 2>/dev/null || true; echo; echo "Arrêté."' EXIT INT TERM

for _ in $(seq 1 30); do
  python3 - <<'EOF' 2>/dev/null && break || sleep 0.5
import os, urllib.request
r = urllib.request.Request("http://127.0.0.1:8765/sante", headers={"X-API-Key": os.environ["MONRECOURS_API_KEY"]})
urllib.request.urlopen(r, timeout=2)
EOF
done
vert "Moteur prêt sur 127.0.0.1:8765."
vert "Interface : http://localhost:3000  (Ctrl-C pour tout arrêter)"
cd web && npm run dev
