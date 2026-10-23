#!/bin/bash
# Déploiement contrôlé de Mon Recours CI : sauvegarde, mise à jour, contrôles,
# retour arrière automatique.
#
#   sudo bash deployer.sh [COMMIT_ATTENDU]
#
# Sans COMMIT_ATTENDU, déploie la tête de origin/feature/admin-authentification.
# Avec, refuse de continuer si la tête distante n'est pas exactement ce commit
# (on déploie ce qui a été validé par la CI, rien d'autre).
#
# Ce que fait le script, dans l'ordre :
#   1. constate l'état : commit en service, branche, modifications locales ;
#   2. SAUVEGARDE avant tout changement (DOSSIERS, RUNTIME, base SQLite par
#      l'API de sauvegarde, configuration, unités systemd), puis VÉRIFIE
#      l'archive ; s'arrête si la sauvegarde échoue ;
#   3. passe sur la branche validée en avance rapide UNIQUEMENT (aucune fusion,
#      aucune réécriture) ; s'arrête si l'historique a divergé ;
#   4. lance maj.sh (dépendances, build, RUNTIME, unité du moteur, redémarrage) ;
#   5. tests de fumée : interface, moteur, intégrité du corpus, protection de la
#      route d'administration ;
#   6. en cas d'échec après le changement de code : retour au commit précédent,
#      restauration des unités, reconstruction, redémarrage, contrôle.
#
# Il n'affiche AUCUN secret : la clé du moteur est lue dans le fichier
# d'environnement par le sous-processus qui l'utilise, jamais imprimée.
# Il n'appelle jamais DeepSeek.
set -Eeuo pipefail

RACINE=/opt/mon-recours-ci
UTIL=monrecours
BRANCHE=feature/admin-authentification
ENV_FICHIER=/etc/mon-recours-ci/env
SAUVEGARDES=/var/backups/mon-recours-ci
ATTENDU="${1:-}"

[ "$(id -u)" -eq 0 ] || { echo "À lancer en root (sudo)." >&2; exit 2; }
[ -d "$RACINE/.git" ] || { echo "Dépôt absent : $RACINE" >&2; exit 2; }
g() { sudo -u "$UTIL" git -C "$RACINE" "$@"; }

echo "== 1. État actuel =="
AVANT=$(g rev-parse HEAD)
BRANCHE_ACTUELLE=$(g rev-parse --abbrev-ref HEAD)
echo "   en service : ${AVANT:0:7} (branche : $BRANCHE_ACTUELLE)"
if [ -n "$(g status --porcelain --untracked-files=no)" ]; then
  echo "ARRÊT : modifications locales non commitées sur le serveur :" >&2
  g status --short --untracked-files=no >&2
  exit 3
fi
g fetch -q origin "$BRANCHE"
CIBLE=$(g rev-parse "origin/$BRANCHE")
echo "   à déployer : ${CIBLE:0:7} (origin/$BRANCHE)"
if [ -n "$ATTENDU" ] && [ "${CIBLE:0:${#ATTENDU}}" != "$ATTENDU" ]; then
  echo "ARRÊT : la tête distante (${CIBLE:0:7}) n'est pas le commit validé ($ATTENDU)." >&2
  exit 3
fi
if [ "$AVANT" = "$CIBLE" ]; then
  echo "   déjà à jour : rien à déployer."
fi
if ! g merge-base --is-ancestor "$AVANT" "$CIBLE"; then
  echo "ARRÊT : ${AVANT:0:7} n'est pas un ancêtre de ${CIBLE:0:7}." >&2
  echo "        L'historique a divergé : une décision humaine est nécessaire." >&2
  exit 3
fi

echo "== 2. Sauvegarde avant changement =="
install -d -m 700 "$SAUVEGARDES"
HORO=$(date -u +%Y%m%d-%H%M%S)
TRAVAIL=$(mktemp -d "$SAUVEGARDES/.travail-XXXXXX")
chmod 700 "$TRAVAIL"
# Base SQLite : copie cohérente par l'API de sauvegarde (pas un cp à chaud).
python3 - "$RACINE/KNOWLEDGE/corpus_juridique.sqlite3" "$TRAVAIL/corpus_juridique.sqlite3" <<'PY'
import sqlite3, sys
source, cible = sys.argv[1], sys.argv[2]
with sqlite3.connect(source) as s, sqlite3.connect(cible) as c:
    s.backup(c)
with sqlite3.connect(cible) as c:
    assert c.execute("pragma integrity_check").fetchone()[0] == "ok"
PY
echo "$AVANT" > "$TRAVAIL/COMMIT_AVANT"
ARCHIVE="$SAUVEGARDES/avant-deploiement-$HORO-${AVANT:0:7}.tar.gz"
ELEMENTS=()
for chemin in opt/mon-recours-ci/DOSSIERS opt/mon-recours-ci/RUNTIME etc/mon-recours-ci \
              etc/systemd/system/monrecours-moteur.service etc/systemd/system/monrecours-web.service \
              etc/systemd/system/monrecours-purge.service etc/systemd/system/monrecours-purge.timer \
              var/lib/monrecours; do
  [ -e "/$chemin" ] && ELEMENTS+=("$chemin")
done
tar czf "$ARCHIVE" -C / "${ELEMENTS[@]}" -C "$TRAVAIL" corpus_juridique.sqlite3 COMMIT_AVANT
chmod 600 "$ARCHIVE"
rm -rf "$TRAVAIL"
NB=$(tar tzf "$ARCHIVE" | wc -l)
tar tzf "$ARCHIVE" | grep -qx "COMMIT_AVANT" || { echo "ARRÊT : archive incomplète." >&2; exit 4; }
echo "   $ARCHIVE ($NB entrées, $(du -h "$ARCHIVE" | cut -f1), lisible)"
# Build de l'interface en service : si la reconstruction échoue pendant un retour
# arrière, on remet celui-ci tel quel plutôt que de laisser un build cassé.
BUILD_SAUVE=""
if [ -d "$RACINE/web/.next" ]; then
  BUILD_SAUVE="$SAUVEGARDES/next-$HORO"
  cp -a "$RACINE/web/.next" "$BUILD_SAUVE"
  echo "   build en service copié : $BUILD_SAUVE"
fi
DOSSIERS_AVANT=$(find "$RACINE/DOSSIERS" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
echo "   dossiers de consultation présents : $DOSSIERS_AVANT"

retour_arriere() {
  # Désarmer le piège AVANT tout : sinon un échec pendant le retour arrière
  # relancerait retour_arriere en boucle (constaté en répétition).
  trap - ERR
  set +e
  echo "!! RETOUR ARRIÈRE vers ${AVANT:0:7}" >&2
  if [ "$BRANCHE_ACTUELLE" = "HEAD" ]; then g checkout -q --detach "$AVANT"; else g checkout -q "$BRANCHE_ACTUELLE" && g reset -q --keep "$AVANT"; fi
  tar xzf "$ARCHIVE" -C / etc/systemd/system 2>/dev/null
  systemctl daemon-reload
  if ! (cd "$RACINE/web" && sudo -u "$UTIL" npm ci --silent && sudo -u "$UTIL" npm run build >/tmp/build-retour.log 2>&1); then
    echo "   reconstruction en échec (/tmp/build-retour.log) : remise du build précédent" >&2
    if [ -n "$BUILD_SAUVE" ]; then
      rm -rf "$RACINE/web/.next" && cp -a "$BUILD_SAUVE" "$RACINE/web/.next"
    fi
  fi
  systemctl restart monrecours-moteur monrecours-web
  sleep 5
  CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/api/sante || echo 000)
  echo "   après retour arrière : commit $(g rev-parse --short HEAD), /api/sante = $CODE" >&2
  echo "   sauvegarde conservée : $ARCHIVE" >&2
  exit 5
}

echo "== 3. Passage sur la branche validée (avance rapide uniquement) =="
trap retour_arriere ERR
if [ "$BRANCHE_ACTUELLE" != "$BRANCHE" ]; then
  if g rev-parse -q --verify "refs/heads/$BRANCHE" >/dev/null; then
    g checkout -q "$BRANCHE"
  else
    g checkout -q -b "$BRANCHE" --track "origin/$BRANCHE"
  fi
fi
g branch -q --set-upstream-to="origin/$BRANCHE" "$BRANCHE"
# Le code est avancé ICI, avant maj.sh : sinon `git pull` réécrirait maj.sh
# pendant que bash l'exécute (bash lit un script au fil de l'eau) et ce serait
# l'ANCIENNE version qui s'exécuterait — constaté en répétition : RUNTIME n'était
# pas créé. maj.sh trouve ensuite le code déjà à jour.
g merge -q --ff-only "origin/$BRANCHE"
echo "   code : $(g rev-parse --short HEAD)"

echo "== 4. Mise à jour (maj.sh) =="
bash "$RACINE/web/deploiement/maj.sh"
APRES=$(g rev-parse HEAD)
[ "$APRES" = "$CIBLE" ] || { echo "ÉCHEC : en service ${APRES:0:7}, attendu ${CIBLE:0:7}" >&2; false; }

echo "== 5. Tests de fumée =="
CODE=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/api/sante)
echo "   interface /api/sante : $CODE"; [ "$CODE" = "200" ]
# Moteur : la clé est lue par ce sous-processus seulement, jamais affichée.
RAPPORT=$(sudo -u "$UTIL" bash -c "set -a; . '$ENV_FICHIER'; set +a; curl -s -H \"X-API-Key: \$MONRECOURS_API_KEY\" http://127.0.0.1:8765/sante")
python3 - "$RAPPORT" <<'PY'
import json, sys
d = json.loads(sys.argv[1])["data"]
c, l = d["corpus"], d["langage"]
print("   moteur : %s fiches, corpus %s (%d altérés, %d absents), %s articles"
      % (d["catalogue"]["fiches"], c["verdict_integrite"], c["alteres"], c["absents"], c["articles"]))
print("   langage : actif=%s, incident ouvert=%s, état enregistré=%s"
      % (l["actif"], l["incident"].get("ouvert"), l["incident"].get("persistant", True)))
assert c["verdict_integrite"] == "INTEGRE", "intégrité du corpus non conforme"
assert l["incident"].get("persistant", True) is not False, "RUNTIME non inscriptible"
PY
CODE=$(curl -s -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
       -H 'Origin: http://127.0.0.1:3000' -d '{}' http://127.0.0.1:3000/api/admin/solde)
echo "   /api/admin/solde sans session : $CODE (403 attendu)"; [ "$CODE" = "403" ]
sudo -u "$UTIL" test -w "$RACINE/RUNTIME" || { echo "ÉCHEC : RUNTIME absent ou non inscriptible par $UTIL" >&2; false; }
echo "   RUNTIME inscriptible par $UTIL : oui"
DOSSIERS_APRES=$(find "$RACINE/DOSSIERS" -mindepth 1 -maxdepth 1 -type d 2>/dev/null | wc -l)
echo "   dossiers de consultation : $DOSSIERS_AVANT avant, $DOSSIERS_APRES après"
[ "$DOSSIERS_APRES" -ge "$DOSSIERS_AVANT" ] || { echo "ÉCHEC : des dossiers ont disparu" >&2; false; }
for service in monrecours-moteur monrecours-web; do
  journalctl -u "$service" --since "-3 min" --no-pager -q -p err | tail -5
done
trap - ERR

[ -n "$BUILD_SAUVE" ] && rm -rf "$BUILD_SAUVE"
echo "== DÉPLOYÉ : ${AVANT:0:7} -> ${APRES:0:7} =="
echo "   sauvegarde : $ARCHIVE"
echo "   retour arrière manuel : sudo -u $UTIL git -C $RACINE reset --keep ${AVANT:0:7} && sudo bash $RACINE/web/deploiement/maj.sh"
