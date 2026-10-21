/**
 * Décision d'accès à l'administration — appelée CÔTÉ SERVEUR à chaque requête.
 *
 * Elle ne fait confiance qu'au cookie signé et à la configuration du serveur :
 * aucun paramètre d'URL, aucun champ de formulaire, aucun en-tête fourni par le
 * navigateur n'intervient dans le rôle accordé.
 */

import { lireEtatAuth, type Compte, type EtatAuth } from "./comptes";
import { NOM_COOKIE_ADMIN, verifierJeton } from "./jeton";
import { lireCookie } from "../session";

export type DecisionAcces =
  | { acces: "ferme"; etat: Exclude<EtatAuth, { etat: "actif" }> }
  | { acces: "anonyme" }
  | { acces: "refuse"; compte: Compte }
  | { acces: "autorise"; compte: Compte };

export function evaluerAccesAdmin(
  enteteCookie: string | null,
  env: Record<string, string | undefined> = process.env,
  maintenantS?: number,
): DecisionAcces {
  const etat = lireEtatAuth(env);
  if (etat.etat !== "actif") return { acces: "ferme", etat };
  const compte = verifierJeton(lireCookie(enteteCookie, NOM_COOKIE_ADMIN), etat.comptes, etat.secret, maintenantS);
  if (!compte) return { acces: "anonyme" };
  return compte.role === "administrateur" ? { acces: "autorise", compte } : { acces: "refuse", compte };
}
