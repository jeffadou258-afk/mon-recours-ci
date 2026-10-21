/**
 * Session d'administration : cookie signé, sans état côté serveur.
 *
 * Contenu du cookie : <charge base64url>.<signature HMAC-SHA256 base64url>
 * Charge : { v, e (adresse), iat, exp, f (empreinte du compte) }
 *
 * - La clé de signature est DÉRIVÉE de MONRECOURS_SESSION_SECRET avec une
 *   étiquette propre à l'administration : un cookie de consultation ne peut
 *   jamais servir de cookie d'administration, et inversement.
 * - Le RÔLE n'est pas dans le cookie : il est relu dans la configuration à
 *   chaque requête. Modifier le cookie ne peut donc pas élever les droits, et
 *   retirer un compte de la configuration ferme immédiatement ses sessions.
 * - `f` lie la session à l'empreinte du mot de passe : changer le mot de passe
 *   d'un compte invalide toutes ses sessions ouvertes.
 * - Expiration absolue : 2 heures, contrôlée côté serveur (`exp` signé) ET par
 *   l'attribut Max-Age du cookie. La déconnexion efface le cookie ; pour
 *   révoquer toutes les sessions d'un coup, changer MONRECOURS_SESSION_SECRET.
 */

import { createHmac, timingSafeEqual } from "node:crypto";
import { trouverCompte, type Compte } from "./comptes";

export const NOM_COOKIE_ADMIN = "mrci_admin";
export const DUREE_SESSION_ADMIN_SECONDES = 2 * 60 * 60;
const VERSION = 1;
const TOLERANCE_HORLOGE_S = 60;

function cleSession(secret: string): Buffer {
  return createHmac("sha256", secret).update("mon-recours-ci:session-administration:v1").digest();
}

function signer(cle: Buffer, texte: string): string {
  return createHmac("sha256", cle).update(texte).digest("base64url");
}

function empreinteCompte(cle: Buffer, compte: Compte): string {
  return createHmac("sha256", cle).update(`compte:${compte.email}:${compte.empreinte}`).digest("base64url").slice(0, 22);
}

export function creerJeton(compte: Compte, secret: string, maintenantS: number = Math.floor(Date.now() / 1000)): string {
  const cle = cleSession(secret);
  const charge = {
    v: VERSION,
    e: compte.email,
    iat: maintenantS,
    exp: maintenantS + DUREE_SESSION_ADMIN_SECONDES,
    f: empreinteCompte(cle, compte),
  };
  const texte = Buffer.from(JSON.stringify(charge)).toString("base64url");
  return `${texte}.${signer(cle, texte)}`;
}

/** Renvoie le compte (avec son rôle ACTUEL) si le jeton est intact, valide et rattaché à un compte existant. */
export function verifierJeton(
  jeton: string | null | undefined,
  comptes: Compte[],
  secret: string,
  maintenantS: number = Math.floor(Date.now() / 1000),
): Compte | null {
  if (!jeton || jeton.length > 1024) return null;
  const point = jeton.indexOf(".");
  if (point <= 0 || point !== jeton.lastIndexOf(".")) return null;
  const texte = jeton.slice(0, point);
  const signature = jeton.slice(point + 1);
  const cle = cleSession(secret);
  const attendue = Buffer.from(signer(cle, texte));
  const recue = Buffer.from(signature);
  if (attendue.length !== recue.length || !timingSafeEqual(attendue, recue)) return null;

  let charge: Record<string, unknown>;
  try {
    charge = JSON.parse(Buffer.from(texte, "base64url").toString("utf8")) as Record<string, unknown>;
  } catch {
    return null;
  }
  if (charge.v !== VERSION || typeof charge.e !== "string" || typeof charge.f !== "string") return null;
  if (typeof charge.iat !== "number" || typeof charge.exp !== "number") return null;
  if (charge.exp <= maintenantS || charge.iat > maintenantS + TOLERANCE_HORLOGE_S) return null;
  if (charge.exp - charge.iat > DUREE_SESSION_ADMIN_SECONDES) return null;

  const compte = trouverCompte(comptes, charge.e);
  if (!compte) return null;
  const attenduF = Buffer.from(empreinteCompte(cle, compte));
  const recuF = Buffer.from(charge.f);
  if (attenduF.length !== recuF.length || !timingSafeEqual(attenduF, recuF)) return null;
  return compte;
}

export function enteteCookieAdmin(valeur: string, securise: boolean): string {
  return [
    `${NOM_COOKIE_ADMIN}=${encodeURIComponent(valeur)}`,
    "Path=/",
    `Max-Age=${DUREE_SESSION_ADMIN_SECONDES}`,
    "HttpOnly",
    "SameSite=Strict",
    securise ? "Secure" : "",
  ]
    .filter(Boolean)
    .join("; ");
}

export function enteteCookieAdminEfface(securise: boolean): string {
  return [`${NOM_COOKIE_ADMIN}=`, "Path=/", "Max-Age=0", "HttpOnly", "SameSite=Strict", securise ? "Secure" : ""]
    .filter(Boolean)
    .join("; ");
}
