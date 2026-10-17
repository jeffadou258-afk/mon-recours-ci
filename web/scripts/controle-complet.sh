#!/usr/bin/env bash
# Contrôle complet de l'interface web, à lancer depuis le dossier web/ :
#
#   bash scripts/controle-complet.sh
#
# Chaque étape est exécutée même si la précédente échoue ; le résultat de chacune
# est noté dans rapport-controle.txt (aucun secret n'y est écrit).

set -u
cd "$(dirname "$0")/.."
RAPPORT="rapport-controle.txt"
: > "$RAPPORT"

etape() {
  local titre="$1"; shift
  {
    echo
    echo "=================================================================="
    echo "== $titre"
    echo "== commande : $*"
    echo "=================================================================="
  } | tee -a "$RAPPORT"
  "$@" 2>&1 | tee -a "$RAPPORT"
  local code=${PIPESTATUS[0]}
  echo "-> code de sortie : $code" | tee -a "$RAPPORT"
  echo "$titre : $code" >> "$RAPPORT.resume"
}

: > "$RAPPORT.resume"
{
  echo "Contrôle Mon Recours CI — $(date '+%Y-%m-%d %H:%M:%S')"
  echo "node $(node --version)  npm $(npm --version)  $(python3 --version 2>&1)"
  echo "branche : $(git rev-parse --abbrev-ref HEAD 2>/dev/null)  commit : $(git rev-parse --short HEAD 2>/dev/null)"
} | tee -a "$RAPPORT"

etape "1. Installation propre" npm install
etape "2. Audit de sécurité" npm audit
etape "3. Versions installées" npm ls next react react-dom sharp esbuild playwright
etape "4. Scripts d'installation en attente" npm approve-scripts --allow-scripts-pending
etape "5. Vérification TypeScript" npm run typecheck
etape "6. Tests unitaires et composants" npm test
etape "7. Construction Next.js" npm run build
etape "8. Secrets dans le code client" npm run verifier:secrets
etape "9. Intégration avec le moteur Python réel" npm run test:integration
etape "10. Navigateur Chromium (installation)" npx playwright install chromium
etape "11. Bout en bout (Chromium mobile, moteur réel)" npm run test:e2e

{
  echo
  echo "==================== RÉSUMÉ (0 = réussi) ===================="
  cat "$RAPPORT.resume"
} | tee -a "$RAPPORT"
rm -f "$RAPPORT.resume"
echo
echo "Rapport complet : web/$RAPPORT"
