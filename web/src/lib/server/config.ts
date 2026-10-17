/**
 * Configuration SERVEUR. Ce module ne doit jamais être importé par un composant
 * client : il lit des secrets. `scripts/verifier-secrets.mjs` vérifie après
 * `next build` qu'aucune de ces valeurs ni aucun de ces noms ne figure dans le
 * bundle envoyé au navigateur.
 */

export interface ConfigServeur {
  urlMoteur: string;
  cleMoteur: string;
  secretSession: string;
  delaiMs: number;
  production: boolean;
  /** Demandes autorisées par visiteur et par minute (ouvrir + répondre). */
  debitVisiteur: number;
}

export class ConfigurationInvalide extends Error {}

const HOTES_LOCAUX = new Set(["127.0.0.1", "localhost", "[::1]"]);

export function lireConfig(env: Record<string, string | undefined> = process.env): ConfigServeur {
  const urlMoteur = (env.MONRECOURS_API_URL || "http://127.0.0.1:8765").replace(/\/+$/, "");
  const cleMoteur = env.MONRECOURS_API_KEY || "";
  const secretSession = env.MONRECOURS_SESSION_SECRET || "";
  const delaiBrut = Number(env.MONRECOURS_API_TIMEOUT_MS || "15000");
  const debitBrut = Number(env.MONRECOURS_DEBIT_VISITEUR || "12");

  let url: URL;
  try {
    url = new URL(urlMoteur);
  } catch {
    throw new ConfigurationInvalide("MONRECOURS_API_URL n'est pas une URL valide.");
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    throw new ConfigurationInvalide("MONRECOURS_API_URL doit utiliser http ou https.");
  }
  // Le moteur ne propose ni TLS ni comptes : on refuse de lui envoyer la clé en
  // clair vers un hôte distant (CLAUDE_HANDOFF.md §6 ter).
  if (url.protocol === "http:" && !HOTES_LOCAUX.has(url.hostname)) {
    throw new ConfigurationInvalide(
      "MONRECOURS_API_URL en http doit viser la machine locale ; un hôte distant exige https.",
    );
  }
  if (cleMoteur.length < 16) {
    throw new ConfigurationInvalide("MONRECOURS_API_KEY est absente ou trop courte (16 caractères minimum).");
  }
  if (secretSession.length < 32) {
    throw new ConfigurationInvalide(
      "MONRECOURS_SESSION_SECRET est absent ou trop court (32 caractères minimum).",
    );
  }
  return {
    urlMoteur,
    cleMoteur,
    secretSession,
    delaiMs: Number.isFinite(delaiBrut) && delaiBrut > 0 ? Math.min(delaiBrut, 60000) : 15000,
    production: env.NODE_ENV === "production",
    debitVisiteur: Number.isFinite(debitBrut) && debitBrut >= 1 ? Math.min(Math.floor(debitBrut), 600) : 12,
  };
}
