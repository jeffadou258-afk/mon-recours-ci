/**
 * Démarre le VRAI serveur du moteur (bin/serveur_api.py) sur un port libre,
 * sans modifier son code : on appelle sa fabrique `creer_serveur(port=0)`.
 * Utilisé par les tests d'intégration et de bout en bout.
 */

import { spawn, type ChildProcess } from "node:child_process";
import { randomBytes } from "node:crypto";
import { join } from "node:path";

export const RACINE_MOTEUR = process.env.MONRECOURS_RACINE_MOTEUR ?? join(__dirname, "..", "..");

export interface MoteurLance {
  url: string;
  cle: string;
  arreter: () => Promise<void>;
}

const SCRIPT = `
import os, sys
sys.path.insert(0, os.path.join(os.getcwd(), "bin"))
sys.path.insert(0, os.getcwd())
import serveur_api
s = serveur_api.creer_serveur(port=0, limiteur=serveur_api.LimiteurDebit(maximum=int(os.environ.get("DEBIT", "1000"))))
print("PORT=%d" % s.server_address[1], flush=True)
s.serve_forever()
`;

export function lancerMoteur(options: { debit?: number } = {}): Promise<MoteurLance> {
  const cle = `cle-integration-${randomBytes(12).toString("hex")}`;
  return new Promise((resoudre, rejeter) => {
    const processus: ChildProcess = spawn(process.env.PYTHON ?? "python3", ["-c", SCRIPT], {
      cwd: RACINE_MOTEUR,
      env: { ...process.env, MONRECOURS_API_KEY: cle, DEBIT: String(options.debit ?? 1000) },
      stdio: ["ignore", "pipe", "pipe"],
    });
    let sortie = "";
    let erreurs = "";
    const delai = setTimeout(() => {
      processus.kill();
      rejeter(new Error(`le moteur n'a pas démarré : ${erreurs}`));
    }, 20000);
    processus.stderr?.on("data", (d) => (erreurs += String(d)));
    processus.stdout?.on("data", (d) => {
      sortie += String(d);
      const m = /PORT=(\d+)/.exec(sortie);
      if (m) {
        clearTimeout(delai);
        resoudre({
          url: `http://127.0.0.1:${m[1]}`,
          cle,
          arreter: () =>
            new Promise((fin) => {
              if (processus.exitCode !== null) return fin();
              processus.once("exit", () => fin());
              processus.kill("SIGTERM");
            }),
        });
      }
    });
    processus.once("exit", (code) => {
      clearTimeout(delai);
      if (!/PORT=/.test(sortie)) rejeter(new Error(`moteur arrêté (code ${code}) : ${erreurs}`));
    });
  });
}
