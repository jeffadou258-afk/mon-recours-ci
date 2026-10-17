/**
 * Cloisonnement des dossiers.
 *
 * Le moteur identifie un dossier par une simple chaîne : quiconque la connaît
 * peut y répondre (aucune notion d'utilisateur côté moteur). L'interface ne
 * laisse donc JAMAIS le navigateur choisir ou lire l'identifiant :
 *  - il est tiré au hasard côté serveur (`web-` + UUID v4) ;
 *  - il est stocké dans un cookie HttpOnly, SameSite=Strict, signé par HMAC ;
 *  - un cookie altéré ou forgé est rejeté avant tout appel au moteur.
 *
 * Aucun stockage serveur supplémentaire : pas de base, pas d'historique.
 */

import { createHmac, randomUUID, timingSafeEqual } from "node:crypto";

export const NOM_COOKIE = "mrci_dossier";
export const DUREE_SESSION_SECONDES = 2 * 60 * 60;
const MOTIF_ID = /^web-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

export function nouvelIdentifiant(): string {
  return `web-${randomUUID()}`;
}

function signer(valeur: string, secret: string): string {
  return createHmac("sha256", secret).update(valeur).digest("base64url");
}

export function emballer(dossierId: string, secret: string): string {
  return `${dossierId}.${signer(dossierId, secret)}`;
}

/** Retourne l'identifiant si le cookie est intact, sinon `null`. */
export function deballer(valeurCookie: string | null | undefined, secret: string): string | null {
  if (!valeurCookie) return null;
  const point = valeurCookie.lastIndexOf(".");
  if (point <= 0) return null;
  const id = valeurCookie.slice(0, point);
  const signature = valeurCookie.slice(point + 1);
  if (!MOTIF_ID.test(id)) return null;
  const attendue = Buffer.from(signer(id, secret));
  const recue = Buffer.from(signature);
  if (attendue.length !== recue.length || !timingSafeEqual(attendue, recue)) return null;
  return id;
}

export function lireCookie(entete: string | null, nom: string = NOM_COOKIE): string | null {
  if (!entete) return null;
  for (const morceau of entete.split(";")) {
    const egal = morceau.indexOf("=");
    if (egal < 0) continue;
    if (morceau.slice(0, egal).trim() === nom) {
      return decodeURIComponent(morceau.slice(egal + 1).trim());
    }
  }
  return null;
}

export function enteteCookie(valeur: string, securise: boolean): string {
  return [
    `${NOM_COOKIE}=${encodeURIComponent(valeur)}`,
    "Path=/api",
    `Max-Age=${DUREE_SESSION_SECONDES}`,
    "HttpOnly",
    "SameSite=Strict",
    securise ? "Secure" : "",
  ]
    .filter(Boolean)
    .join("; ");
}
