/**
 * Client HTTP du moteur — côté serveur uniquement.
 *
 * Il n'appelle que les trois routes réellement implémentées par
 * `bin/serveur_api.py` : GET /sante, POST /ouvrir, POST /repondre.
 * La clé d'API est ajoutée ici et ne quitte jamais le serveur.
 */

import type { ConfigServeur } from "./config";

export type RouteMoteur = "/sante" | "/ouvrir" | "/repondre" | "/supprimer" | "/courrier";

export type ReponseMoteur =
  | { joignable: true; statut: number; corps: unknown; retryAfter: string | null }
  | { joignable: false; raison: "delai" | "reseau" };

export type Recuperateur = (entree: string, init: RequestInit) => Promise<Response>;

export async function appelerMoteur(
  config: ConfigServeur,
  route: RouteMoteur,
  corps?: Record<string, unknown>,
  recuperer: Recuperateur = fetch,
): Promise<ReponseMoteur> {
  const controleur = new AbortController();
  const minuteur = setTimeout(() => controleur.abort(), config.delaiMs);
  try {
    const reponse = await recuperer(`${config.urlMoteur}${route}`, {
      method: corps ? "POST" : "GET",
      headers: {
        "X-API-Key": config.cleMoteur,
        Accept: "application/json",
        ...(corps ? { "Content-Type": "application/json" } : {}),
      },
      body: corps ? JSON.stringify(corps) : undefined,
      signal: controleur.signal,
      cache: "no-store",
      redirect: "error",
    });
    let charge: unknown = null;
    const texte = await reponse.text();
    if (texte) {
      try {
        charge = JSON.parse(texte);
      } catch {
        charge = null;
      }
    }
    return {
      joignable: true,
      statut: reponse.status,
      corps: charge,
      retryAfter: reponse.headers.get("Retry-After"),
    };
  } catch (erreur) {
    const delai = erreur instanceof Error && erreur.name === "AbortError";
    return { joignable: false, raison: delai ? "delai" : "reseau" };
  } finally {
    clearTimeout(minuteur);
  }
}
