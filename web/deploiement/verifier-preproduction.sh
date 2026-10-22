#!/usr/bin/env bash
# Contrôle d'une PRÉPRODUCTION de Mon Recours CI — lecture seule, aucun secret affiché.
#
#   sudo bash web/deploiement/verifier-preproduction.sh https://preprod.votre-domaine.ci
#
# Vérifie : configuration systemd de l'interface, droits du répertoire d'audit
# et du fichier de comptes, absence de mode démo et de fournisseur LLM, HTTPS,
# attributs du cookie de session, redirection de /admin, refus d'une connexion
# avec des identifiants synthétiques, refus d'une origine étrangère.
# Ne modifie rien. N'affiche jamais la valeur d'une variable.
#
# Code de sortie : 0 si tout est conforme, 1 sinon.

set -u
BASE="${1:-}"
FICHIER_ENV="${MONRECOURS_FICHIER_ENV:-/etc/mon-recours-ci/env}"
UNITE="${MONRECOURS_UNITE_WEB:-monrecours-web.service}"
ECHECS=0

ok()     { printf 'OK      %s\n' "$1"; }
echec()  { printf 'ÉCHEC   %s\n' "$1"; ECHECS=$((ECHECS + 1)); }
info()   { printf 'INFO    %s\n' "$1"; }

if [ -z "$BASE" ] || [[ "$BASE" != https://* ]]; then
  echo "Usage : $0 https://<adresse de la préproduction>   (HTTPS obligatoire)" >&2
  exit 2
fi
BASE="${BASE%/}"

# Lit le NOM des variables présentes, jamais leur valeur.
variable_definie() { [ -r "$FICHIER_ENV" ] && grep -qE "^[[:space:]]*$1=" "$FICHIER_ENV"; }
valeur_egale()     { [ -r "$FICHIER_ENV" ] && grep -qE "^[[:space:]]*$1=['\"]?$2['\"]?[[:space:]]*$" "$FICHIER_ENV"; }
valeur_de()        { grep -E "^[[:space:]]*$1=" "$FICHIER_ENV" | tail -1 | cut -d= -f2- | sed -E "s/^['\"]//; s/['\"]$//"; }

echo "== Configuration du serveur =="
if [ ! -r "$FICHIER_ENV" ]; then
  echec "fichier d'environnement illisible : $FICHIER_ENV (lancer avec sudo)"
else
  droits=$(stat -c '%a' "$FICHIER_ENV")
  [ "$droits" = "600" ] || [ "$droits" = "400" ] && ok "fichier d'environnement en $droits" || echec "fichier d'environnement en $droits (attendu 600)"
  valeur_egale MONRECOURS_MODE demo && echec "MONRECOURS_MODE=demo : l'administration serait fermée" || ok "mode démonstration désactivé"
  variable_definie MONRECOURS_LLM_FOURNISSEUR && echec "un fournisseur LLM est configuré (interdit en préproduction)" || ok "aucun fournisseur LLM configuré"
  variable_definie MONRECOURS_SESSION_SECRET && ok "secret de session présent (valeur non lue)" || echec "MONRECOURS_SESSION_SECRET absent"
  if variable_definie MONRECOURS_COMPTES && variable_definie MONRECOURS_COMPTES_FICHIER; then
    echec "MONRECOURS_COMPTES et MONRECOURS_COMPTES_FICHIER définies toutes deux (configuration ambiguë)"
  elif variable_definie MONRECOURS_COMPTES_FICHIER; then
    comptes=$(valeur_de MONRECOURS_COMPTES_FICHIER)
    if [ -L "$comptes" ]; then echec "fichier de comptes : lien symbolique refusé"
    elif [ ! -f "$comptes" ]; then echec "fichier de comptes introuvable"
    else
      d=$(stat -c '%a %U' "$comptes")
      case "$d" in "600 monrecours"|"400 monrecours") ok "fichier de comptes : $d";; *) echec "fichier de comptes : $d (attendu 600 monrecours)";; esac
      if grep -qiE '"motDePasse"[[:space:]]*:[[:space:]]*"[^s]' "$comptes" || ! grep -q 'scrypt\$' "$comptes"; then
        echec "fichier de comptes : une entrée ne contient pas d'empreinte scrypt"
      else
        ok "fichier de comptes : uniquement des empreintes scrypt (contenu non affiché)"
      fi
    fi
  elif variable_definie MONRECOURS_COMPTES; then
    info "comptes dans la variable MONRECOURS_COMPTES (préférer MONRECOURS_COMPTES_FICHIER)"
  else
    echec "aucun compte configuré : la connexion restera fermée"
  fi
  if variable_definie MONRECOURS_AUDIT_FICHIER; then
    audit=$(valeur_de MONRECOURS_AUDIT_FICHIER)
    dossier=$(dirname "$audit")
    [ -d "$dossier" ] && d=$(stat -c '%a %U' "$dossier") || d="absent"
    [ "$d" = "700 monrecours" ] && ok "répertoire d'audit : $d" || echec "répertoire d'audit : $d (attendu 700 monrecours)"
    if [ -f "$audit" ]; then
      f=$(stat -c '%a %U' "$audit")
      [ "$f" = "600 monrecours" ] && ok "fichier d'audit : $f" || echec "fichier d'audit : $f (attendu 600 monrecours)"
    else
      info "fichier d'audit pas encore créé (il le sera au premier événement)"
    fi
  else
    info "MONRECOURS_AUDIT_FICHIER non défini : journal d'audit seulement dans journald"
  fi
fi

echo "== systemd =="
if command -v systemctl >/dev/null && systemctl cat "$UNITE" >/dev/null 2>&1; then
  for attendu in "ProtectSystem=strict" "NoNewPrivileges=yes" "StateDirectory=monrecours" "UMask=0077" "User=monrecours"; do
    cle=${attendu%%=*}; val=${attendu#*=}
    reel=$(systemctl show "$UNITE" -p "$cle" --value 2>/dev/null)
    [ "$reel" = "$val" ] && ok "$cle=$reel" || echec "$cle=$reel (attendu $val)"
  done
  systemctl is-active --quiet "$UNITE" && ok "$UNITE actif" || echec "$UNITE inactif"
else
  echec "unité $UNITE introuvable (systemd absent ou unité non installée)"
fi

echo "== Moteur, sauvegarde, purge =="
VENV_PY="${MONRECOURS_VENV_PYTHON:-/opt/mon-recours-ci/.venv/bin/python}"
if [ -x "$VENV_PY" ] && "$VENV_PY" -c 'import fpdf' 2>/dev/null; then
  ok "fpdf2 présent dans l'environnement du moteur (courriers PDF)"
else
  echec "fpdf2 absent de $VENV_PY : aucun courrier PDF ne sera produit"
fi
if command -v systemctl >/dev/null; then
  for minuteur in monrecours-sauvegarde.timer monrecours-purge.timer; do
    systemctl is-active --quiet "$minuteur" && ok "$minuteur actif" || echec "$minuteur inactif"
  done
  [ -r /etc/mon-recours-ci/cle-sauvegarde ] && d=$(stat -c '%a %U' /etc/mon-recours-ci/cle-sauvegarde) || d="absente"
  [ "$d" = "600 monrecours" ] && ok "clé de sauvegarde : $d (valeur non lue)" || echec "clé de sauvegarde : $d (attendu 600 monrecours)"
  recente=$(find /var/lib/monrecours-sauvegardes -maxdepth 1 -name '*.enc' -mmin -1500 2>/dev/null | head -1)
  [ -n "$recente" ] && ok "archive chiffrée de moins de 25 h présente" || echec "aucune archive de moins de 25 h dans /var/lib/monrecours-sauvegardes"
fi

echo "== HTTPS et réponses publiques =="
code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "$BASE/" 2>/dev/null) || code="000"
[ "$code" = "200" ] && ok "page d'accueil en HTTPS ($code)" || echec "page d'accueil : $code"
hsts=$(curl -sSI --max-time 15 "$BASE/" 2>/dev/null | grep -i '^strict-transport-security' || true)
[ -n "$hsts" ] && ok "en-tête HSTS présent" || echec "en-tête HSTS absent"
http_code=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 "http://${BASE#https://}/" 2>/dev/null) || http_code="000"
case "$http_code" in 301|308) ok "HTTP redirigé vers HTTPS ($http_code)";; *) echec "HTTP non redirigé ($http_code)";; esac

admin=$(curl -sS -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 15 "$BASE/admin" 2>/dev/null) || admin="000"
case "$admin" in 307*connexion*|308*connexion*|303*connexion*) ok "/admin sans session → redirection vers /connexion";; *) echec "/admin sans session : $admin";; esac

hote="${BASE#https://}"; hote="${hote%%/*}"
corps='{"email":"essai-preproduction@exemple.invalid","motDePasse":"identifiant-synthetique-incorrect"}'
reponse=$(curl -sS -D - -o /dev/null --max-time 20 -X POST "$BASE/api/connexion" \
  -H 'Content-Type: application/json' -H "Origin: https://$hote" --data "$corps" 2>/dev/null || true)
statut=$(printf '%s' "$reponse" | head -1 | awk '{print $2}')
[ "$statut" = "401" ] && ok "identifiants synthétiques refusés (401)" || echec "connexion synthétique : statut $statut (attendu 401 ; 503 = comptes non configurés)"
if [ -z "$statut" ]; then
  echec "contrôle du cookie impossible : aucune réponse du serveur"
elif printf '%s' "$reponse" | grep -qi '^set-cookie: mrci_admin'; then
  echec "un cookie de session a été posé pour des identifiants faux"
else
  ok "aucun cookie posé après un refus"
fi

etranger=$(curl -sS -o /dev/null -w '%{http_code}' --max-time 15 -X POST "$BASE/api/connexion" \
  -H 'Content-Type: application/json' -H 'Origin: https://site-etranger.invalid' --data "$corps" 2>/dev/null) || etranger="000"
[ "$etranger" = "403" ] && ok "origine étrangère refusée (403)" || echec "origine étrangère : $etranger (attendu 403)"

echo
if [ "$ECHECS" -eq 0 ]; then
  echo "CONFORME — reste à faire à la main : connexion réelle avec le compte de test, rôle lecteur refusé, déconnexion."
  exit 0
fi
echo "NON CONFORME — $ECHECS contrôle(s) en échec. Ne pas ouvrir l'administration."
exit 1
