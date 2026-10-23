#!/bin/bash
# Mise à jour de Mon Recours CI sur le serveur.
#
#   sudo bash /opt/mon-recours-ci/web/deploiement/maj.sh
#
# Ce script récupère le code par `git pull --ff-only` (aucune fusion implicite,
# aucune réécriture d'historique), réinstalle les dépendances si nécessaire,
# reconstruit l'interface, redémarre les services et vérifie que le moteur
# répond. Si le contrôle final échoue, il sort en erreur : une mise à jour
# silencieusement cassée est pire qu'une mise à jour refusée.
#
# La clé de déploiement est en LECTURE SEULE : ce script ne peut pas pousser.
set -euo pipefail

RACINE=/opt/mon-recours-ci
UTIL=monrecours
SERVICE_MOTEUR=monrecours-moteur
SERVICE_WEB=monrecours-web

if [ "$(id -u)" -ne 0 ]; then
  echo "Ce script doit être lancé en root (il redémarre des services)." >&2
  exit 2
fi

echo "== 1. Code =="
AVANT=$(sudo -u "$UTIL" git -C "$RACINE" rev-parse --short HEAD)
sudo -u "$UTIL" git -C "$RACINE" pull --ff-only
APRES=$(sudo -u "$UTIL" git -C "$RACINE" rev-parse --short HEAD)
echo "   $AVANT -> $APRES"

if [ "$AVANT" = "$APRES" ]; then
  echo "   déjà à jour"
fi

echo "== 2. Dépendances Python =="
cd "$RACINE"
if ! sudo -u "$UTIL" .venv/bin/python -c 'import fpdf' 2>/dev/null; then
  sudo -u "$UTIL" .venv/bin/pip install -q -r requirements.txt
  echo "   requirements.txt installé"
else
  echo "   fpdf2 déjà présent"
fi

echo "== 3. Dépendances et build de l'interface =="
cd "$RACINE/web"
sudo -u "$UTIL" npm ci --silent
sudo -u "$UTIL" npm run build > /tmp/build-maj.log 2>&1 || { tail -25 /tmp/build-maj.log; exit 1; }
echo "   build réussi"

echo "== 4. Dossiers d'état du moteur =="
# RUNTIME doit exister AVANT le redémarrage : l'unité systemd le déclare en
# ReadWritePaths et refuse de démarrer s'il manque.
install -d -o "$UTIL" -g "$UTIL" -m 700 "$RACINE/RUNTIME"
echo "   RUNTIME prêt (700, $UTIL)"
if ! cmp -s "$RACINE/web/deploiement/monrecours-moteur.service" /etc/systemd/system/monrecours-moteur.service; then
  install -m 644 "$RACINE/web/deploiement/monrecours-moteur.service" /etc/systemd/system/monrecours-moteur.service
  systemctl daemon-reload
  echo "   unité du moteur mise à jour"
fi

echo "== 5. Redémarrage =="
systemctl restart "$SERVICE_MOTEUR" "$SERVICE_WEB"
sleep 4
for service in "$SERVICE_MOTEUR" "$SERVICE_WEB"; do
  etat=$(systemctl is-active "$service" || true)
  echo "   $service : $etat"
  [ "$etat" = "active" ] || { echo "ECHEC : $service inactif" >&2; exit 1; }
done

echo "== 6. Contrôle =="
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/api/sante || echo 000)
echo "   /api/sante : $CODE"
[ "$CODE" = "200" ] || { echo "ECHEC : le service ne répond pas" >&2; exit 1; }
if ! sudo -u "$UTIL" test -w "$RACINE/RUNTIME"; then
  echo "ECHEC : RUNTIME n'est pas inscriptible par $UTIL" >&2; exit 1
fi

echo "== TERMINÉ : $APRES en service =="
