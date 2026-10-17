import { readFileSync } from "node:fs";
import { join } from "node:path";
import type { ConfigServeur } from "../src/lib/server/config";
import type { Recuperateur } from "../src/lib/server/moteur";

export function fixture(nom: string): any {
  return JSON.parse(readFileSync(join(__dirname, "fixtures", `${nom}.json`), "utf8"));
}

export const CONFIG_TEST: ConfigServeur = {
  urlMoteur: "http://127.0.0.1:8765",
  cleMoteur: "cle-de-test-tres-secrete-0123456789",
  secretSession: "secret-de-session-de-test-0123456789-abcdef",
  delaiMs: 2000,
  production: false,
  debitVisiteur: 1000,
};

export interface AppelEnregistre {
  url: string;
  init: RequestInit;
}

/** Faux transport : renvoie une réponse prédéfinie et mémorise l'appel. */
export function fauxMoteur(
  statut: number,
  corps: unknown,
  entetes: Record<string, string> = {},
): { recuperer: Recuperateur; appels: AppelEnregistre[] } {
  const appels: AppelEnregistre[] = [];
  const recuperer: Recuperateur = async (url, init) => {
    appels.push({ url, init });
    return new Response(JSON.stringify(corps), {
      status: statut,
      headers: { "Content-Type": "application/json", ...entetes },
    });
  };
  return { recuperer, appels };
}

export function requeteJson(
  chemin: string,
  corps: unknown,
  entetes: Record<string, string> = {},
): Request {
  return new Request(`http://localhost:3000${chemin}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Host: "localhost:3000", ...entetes },
    body: typeof corps === "string" ? corps : JSON.stringify(corps),
  });
}

export const journalMuet = () => undefined;
