# -*- coding: utf-8 -*-
"""Serveur HTTP local — enveloppe `core/service.py`, sans logique juridique.

    export MONRECOURS_API_KEY="une-cle-longue-et-aleatoire"
    python3 bin/serveur_api.py                 # 127.0.0.1:8765

    curl -H "X-API-Key: $MONRECOURS_API_KEY" -H "Content-Type: application/json" \
         -d '{"dossier_id":"D1","demande":"Mon bailleur garde ma caution."}' \
         http://127.0.0.1:8765/ouvrir

CE QUE CE SERVEUR EST : une couche de transport locale, testée, qui n'expose que
cinq routes (`/sante`, `/ouvrir`, `/repondre`, `/courrier`, `/supprimer`) et
réutilise intégralement `core/service.py`.

CE QU'IL N'EST PAS : un service public. Il n'y a **aucune** protection contre une
attaque distribuée, aucune terminaison TLS, aucune gestion d'utilisateurs. Il
écoute sur 127.0.0.1 uniquement et refuse de démarrer sans clé.

GARDE-FOUS
----------
* **Aucune clé dans le code** : `MONRECOURS_API_KEY` doit être fournie par
  l'environnement ; sans elle, le serveur refuse de démarrer.
* **Écoute locale seulement** : l'hôte est forcé à 127.0.0.1, aucune option CLI ne
  permet d'écouter ailleurs (une exposition publique exigerait TLS, un pare-feu et
  une revue de sécurité qui n'ont pas eu lieu).
* **Comparaison à temps constant** de la clé (`hmac.compare_digest`).
* **Limitation de débit** par clé, fenêtre glissante, `429` + `Retry-After`.
* **Taille de corps limitée** (`413`), **JSON invalide** (`400`), méthode inconnue
  (`405`), route inconnue (`404`).
* **Journalisation sans données personnelles** : méthode, route, statut, durée et
  empreinte tronquée du dossier — jamais la demande ni une réponse.
"""

import argparse
import hashlib
import hmac
import json
import os
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if RACINE not in sys.path:
    sys.path.insert(0, RACINE)

from core import service  # noqa: E402

TAILLE_MAX_CORPS = 64 * 1024
NOM_VARIABLE_CLE = "MONRECOURS_API_KEY"
ROUTES_POST = {"/ouvrir": service.ouvrir, "/repondre": service.repondre,
               "/llm/verifier-solde": lambda charge: service.verifier_solde_llm(),
               "/supprimer": service.supprimer, "/courrier": service.rediger_courrier}
ROUTES_GET = {"/sante": lambda: service.sante()}


class LimiteurDebit(object):
    """Fenêtre glissante en mémoire, par clé. Suffisant pour un usage local."""

    def __init__(self, maximum=30, fenetre=60.0, horloge=time.monotonic):
        self.maximum = maximum
        self.fenetre = fenetre
        self.horloge = horloge
        self._historique = {}
        self._verrou = threading.Lock()

    def autoriser(self, cle):
        maintenant = self.horloge()
        with self._verrou:
            horodatages = [t for t in self._historique.get(cle, []) if maintenant - t < self.fenetre]
            if len(horodatages) >= self.maximum:
                self._historique[cle] = horodatages
                return False, self.fenetre - (maintenant - horodatages[0])
            horodatages.append(maintenant)
            self._historique[cle] = horodatages
            return True, 0.0


def empreinte_dossier(dossier_id):
    """Empreinte tronquée : corréler des requêtes sans écrire l'identifiant en clair.

    Une requête sans dossier (ex. `/sante`) journalise « - » : une empreinte
    constante ressemblerait à un vrai dossier et fausserait la lecture du journal.
    """
    if not isinstance(dossier_id, str) or not dossier_id:
        return "-"
    return hashlib.sha256(dossier_id.encode("utf-8")).hexdigest()[:12]


def _fabrique(cle_api, limiteur, journal=None):
    class Gestionnaire(BaseHTTPRequestHandler):
        server_version = "MonRecoursCI/0.5"
        sys_version = ""
        protocol_version = "HTTP/1.1"

        # -- utilitaires -------------------------------------------------
        def log_message(self, format, *args):  # silence du log par défaut
            return

        def _journaliser(self, statut, duree, dossier):
            ligne = {
                "horodatage": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "methode": self.command,
                "route": self.path.split("?")[0],
                "statut": statut,
                "duree_ms": round(duree * 1000, 1),
                "dossier": empreinte_dossier(dossier),
            }
            if journal is not None:
                journal.append(ligne)
            else:
                sys.stderr.write(json.dumps(ligne, ensure_ascii=False) + "\n")

        def _envoyer(self, statut, charge, duree=0.0, dossier="-", entetes=None):
            corps = json.dumps(charge, ensure_ascii=False).encode("utf-8")
            self.send_response(statut)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            for nom, valeur in (entetes or {}).items():
                self.send_header(nom, valeur)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(corps)
            self._journaliser(statut, duree, dossier)

        def _erreur(self, statut, code, message, duree=0.0, dossier="-", entetes=None):
            self._envoyer(statut, {"ok": False,
                                   "erreur": {"code": code, "message": message}},
                          duree, dossier, entetes)

        def _autorise(self, debut):
            fournie = self.headers.get("X-API-Key") or ""
            if not hmac.compare_digest(fournie, cle_api):
                self._erreur(401, "NON_AUTHENTIFIE", "clé d'API absente ou invalide",
                             time.monotonic() - debut)
                return False
            return True

        def _lire_corps(self):
            longueur = int(self.headers.get("Content-Length") or 0)
            if longueur > TAILLE_MAX_CORPS:
                return None, "corps trop volumineux (max %d octets)" % TAILLE_MAX_CORPS
            brut = self.rfile.read(longueur) if longueur else b""
            if not brut:
                return {}, None
            try:
                charge = json.loads(brut.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return None, "JSON invalide"
            if not isinstance(charge, dict):
                return None, "le corps doit être un objet JSON"
            return charge, None

        # -- routes ------------------------------------------------------
        def do_GET(self):
            debut = time.monotonic()
            route = self.path.split("?")[0]
            if not self._autorise(debut):
                return
            if route not in ROUTES_GET:
                self._erreur(404, "ROUTE_INCONNUE", "route inconnue : %s" % route,
                             time.monotonic() - debut)
                return
            autorise, attente = self._verifie_debit()
            if not autorise:
                self._erreur(429, "DEBIT_DEPASSE", "trop de requêtes ; réessayez dans %.0f s"
                             % attente, time.monotonic() - debut,
                             entetes={"Retry-After": str(int(attente) + 1)})
                return
            self._envoyer(200, ROUTES_GET[route](), time.monotonic() - debut)

        def do_POST(self):
            debut = time.monotonic()
            route = self.path.split("?")[0]
            if not self._autorise(debut):
                return
            if route not in ROUTES_POST:
                self._erreur(404, "ROUTE_INCONNUE", "route inconnue : %s" % route,
                             time.monotonic() - debut)
                return
            autorise, attente = self._verifie_debit()
            if not autorise:
                self._erreur(429, "DEBIT_DEPASSE", "trop de requêtes ; réessayez dans %.0f s"
                             % attente, time.monotonic() - debut,
                             entetes={"Retry-After": str(int(attente) + 1)})
                return
            type_contenu = (self.headers.get("Content-Type") or "").split(";")[0].strip().lower()
            if type_contenu != "application/json":
                self._erreur(415, "TYPE_NON_SUPPORTE",
                             "Content-Type attendu : application/json (reçu : %r)"
                             % (type_contenu or "absent"), time.monotonic() - debut)
                return
            charge, erreur = self._lire_corps()
            if erreur:
                statut = 413 if "volumineux" in erreur else 400
                self._erreur(statut, "CORPS_INVALIDE" if statut == 400 else "CORPS_TROP_GRAND",
                             erreur, time.monotonic() - debut)
                return
            dossier = charge.get("dossier_id")
            try:
                if route == "/ouvrir":
                    resultat = service.ouvrir(charge.get("dossier_id"), charge.get("demande"))
                elif route == "/supprimer":
                    resultat = service.supprimer(charge.get("dossier_id"))
                elif route == "/courrier":
                    resultat = service.rediger_courrier(charge.get("dossier_id"),
                                                        charge.get("informations"))
                else:
                    resultat = service.repondre(charge.get("dossier_id"),
                                                charge.get("reponses"))
            except TypeError as manque:
                self._erreur(400, "CHAMP_MANQUANT", str(manque),
                             time.monotonic() - debut, dossier)
                return
            statut = 200 if resultat.get("ok") else 422
            self._envoyer(statut, resultat, time.monotonic() - debut, dossier)

        def _verifie_debit(self):
            return limiteur.autoriser(cle_api)

        def do_PUT(self):
            debut = time.monotonic()
            self._erreur(405, "METHODE_NON_AUTORISEE", "méthode non autorisée",
                         time.monotonic() - debut)

        do_DELETE = do_PUT
        do_PATCH = do_PUT

    return Gestionnaire


def creer_serveur(port=0, hote="127.0.0.1", cle_api=None, limiteur=None, journal=None):
    """Fabrique utilisée par les tests : port 0 = port éphémère."""
    cle = cle_api if cle_api is not None else os.environ.get(NOM_VARIABLE_CLE, "")
    if not cle:
        raise RuntimeError(
            "refus de démarrer : la variable %s n'est pas définie. Aucune clé par défaut "
            "n'est fournie par le code." % NOM_VARIABLE_CLE)
    if len(cle) < 16:
        raise RuntimeError("refus de démarrer : clé trop courte (16 caractères minimum)")
    if hote != "127.0.0.1":
        raise RuntimeError("refus de démarrer : écoute locale uniquement (127.0.0.1)")
    serveur = ThreadingHTTPServer((hote, port),
                                  _fabrique(cle, limiteur or LimiteurDebit(), journal))
    serveur.daemon_threads = True
    return serveur


def main(argv=None):
    analyseur = argparse.ArgumentParser(description="Serveur local Mon Recours CI")
    analyseur.add_argument("--port", type=int, default=8765)
    analyseur.add_argument("--debit", type=int, default=30,
                           help="requêtes autorisées par fenêtre de 60 s")
    arguments = analyseur.parse_args(argv)
    try:
        serveur = creer_serveur(port=arguments.port,
                                limiteur=LimiteurDebit(maximum=arguments.debit))
    except RuntimeError as erreur:
        print("ERREUR : %s" % erreur)
        return 2
    print("Serveur local sur http://127.0.0.1:%d  (Ctrl-C pour arrêter)" % arguments.port)
    print("Clé lue depuis %s. Aucune exposition publique." % NOM_VARIABLE_CLE)
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\narrêt")
    finally:
        serveur.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
