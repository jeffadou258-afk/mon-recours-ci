/**
 * Empreintes de mots de passe — scrypt (node:crypto), jamais de mot de passe en clair.
 *
 * Format stocké (une seule chaîne, sans espace) :
 *   scrypt$<N>$<r>$<p>$<sel base64url>$<empreinte base64url>
 *
 * Les empreintes sont produites hors ligne par `scripts/creer-compte.mjs`, qui
 * utilise exactement les mêmes paramètres. Aucun mot de passe par défaut
 * n'existe : sans compte configuré, personne ne peut se connecter.
 */

import { randomBytes, scrypt, timingSafeEqual } from "node:crypto";

export const PARAMETRES_SCRYPT = { N: 16384, r: 8, p: 1, longueurCle: 32, longueurSel: 16 } as const;

/** Bornes acceptées à la lecture : on refuse une empreinte trop faible ou trop coûteuse. */
const N_MIN = 16384;
const N_MAX = 131072;

/** Longueur maximale d'un mot de passe soumis (évite d'occuper scrypt avec des mégaoctets). */
export const LONGUEUR_MAX_MOT_DE_PASSE = 1024;
/** Longueur minimale imposée à la création d'un compte. */
export const LONGUEUR_MIN_MOT_DE_PASSE = 12;

interface EmpreinteLue {
  N: number;
  r: number;
  p: number;
  sel: Buffer;
  empreinte: Buffer;
}

function deriver(motDePasse: string, sel: Buffer, N: number, r: number, p: number, longueur: number): Promise<Buffer> {
  return new Promise((resoudre, rejeter) => {
    // maxmem : 128 * N * r * p octets suffisent ; on laisse une marge.
    scrypt(motDePasse.normalize("NFC"), sel, longueur, { N, r, p, maxmem: 256 * N * r * p }, (err, cle) =>
      err ? rejeter(err) : resoudre(cle),
    );
  });
}

export function lireEmpreinte(texte: string): EmpreinteLue | null {
  const morceaux = texte.split("$");
  if (morceaux.length !== 6 || morceaux[0] !== "scrypt") return null;
  const [N, r, p] = morceaux.slice(1, 4).map((v) => Number(v));
  if (![N, r, p].every((v) => Number.isInteger(v) && v! > 0)) return null;
  if (N! < N_MIN || N! > N_MAX || (N! & (N! - 1)) !== 0 || r! < 8 || r! > 32 || p! < 1 || p! > 4) return null;
  const sel = Buffer.from(morceaux[4]!, "base64url");
  const empreinte = Buffer.from(morceaux[5]!, "base64url");
  if (sel.length < 16 || empreinte.length < 32) return null;
  return { N: N!, r: r!, p: p!, sel, empreinte };
}

export async function hacherMotDePasse(motDePasse: string): Promise<string> {
  const { N, r, p, longueurCle, longueurSel } = PARAMETRES_SCRYPT;
  const sel = randomBytes(longueurSel);
  const cle = await deriver(motDePasse, sel, N, r, p, longueurCle);
  return `scrypt$${N}$${r}$${p}$${sel.toString("base64url")}$${cle.toString("base64url")}`;
}

/**
 * Empreinte factice : quand l'adresse ne correspond à aucun compte, on vérifie
 * quand même un mot de passe contre elle, pour que la durée de la réponse ne
 * révèle pas l'existence du compte.
 *
 * Elle est calculée DÈS LE CHARGEMENT du module (et, au démarrage du serveur,
 * par `src/instrumentation.ts`), jamais pendant une tentative de connexion.
 * Ses paramètres sont ceux d'une vraie empreinte : la vérification d'un compte
 * inconnu coûte exactement un calcul scrypt, comme celle d'un compte existant.
 */
const empreinteFactice: Promise<string> = hacherMotDePasse(randomBytes(24).toString("base64url"));
// Évite un avertissement « rejet non géré » ; l'erreur éventuelle ressort à l'`await`.
empreinteFactice.catch(() => {});

/** Attend que l'empreinte factice soit prête (appelé au démarrage du serveur). */
export async function preparerEmpreinteFactice(): Promise<void> {
  await empreinteFactice;
}

/**
 * Compare en temps constant. Une empreinte illisible ne valide jamais rien.
 * Les deux chemins (compte existant / inconnu) font les mêmes étapes : attente
 * de l'empreinte factice, une dérivation scrypt, une comparaison.
 */
export async function verifierMotDePasse(motDePasse: string, empreinteStockee: string | null): Promise<boolean> {
  const factice = await empreinteFactice;
  const stockee = empreinteStockee === null ? null : lireEmpreinte(empreinteStockee);
  const lue = stockee ?? lireEmpreinte(factice);
  if (!lue) return false;
  const calculee = await deriver(motDePasse, lue.sel, lue.N, lue.r, lue.p, lue.empreinte.length);
  const egal = calculee.length === lue.empreinte.length && timingSafeEqual(calculee, lue.empreinte);
  return egal && stockee !== null;
}
