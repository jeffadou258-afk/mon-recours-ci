/**
 * MODE DÉMONSTRATION — réponses figées, aucune dépendance au moteur Python.
 *
 * À quoi il sert : produire une Preview publique (Vercel) qui montre le parcours
 * réel de l'interface sans moteur juridique, sans base, sans accès disque. Les
 * charges sont des **captures datées** du moteur sur une demande synthétique
 * (« Mon bailleur refuse de me rendre la caution »), enregistrées une fois.
 *
 * Ce que le mode démonstration N'EST PAS :
 *   - il ne répond à aucune question libre : quelle que soit la demande, il
 *     rejoue la même capture ;
 *   - il n'écrit rien, ne lit aucun dossier, ne signe aucun document ;
 *   - il n'est activé que par `MONRECOURS_MODE=demo`, jamais par défaut.
 *
 * Le bandeau visible (`BandeauDemonstration`) est obligatoire : une réponse
 * figée présentée comme une réponse juridique serait un mensonge.
 */

import sante from "./demo/sante.json";
import ouverture from "./demo/ouverture.json";
import conclusion from "./demo/conclusion.json";
import courrier from "./demo/courrier.json";
import type { ReponseMoteur, RouteMoteur } from "./moteur";

/** Nom du fichier PDF synthétique servi par `/api/courrier/telecharger` en démo. */
export const PDF_DEMONSTRATION = "demo/courrier-demonstration.pdf";

export function estModeDemo(env: Record<string, string | undefined> = process.env): boolean {
  return env.MONRECOURS_MODE === "demo";
}

/** Remplace le marqueur de dossier par l'identifiant réellement demandé. */
function avecDossier(valeur: unknown, dossierId: string): unknown {
  if (typeof valeur === "string") return valeur.replace("__DOSSIER__", dossierId);
  if (Array.isArray(valeur)) return valeur.map((v) => avecDossier(v, dossierId));
  if (valeur && typeof valeur === "object") {
    const sortie: Record<string, unknown> = {};
    for (const [cle, v] of Object.entries(valeur as Record<string, unknown>)) {
      sortie[cle] = avecDossier(v, dossierId);
    }
    return sortie;
  }
  return valeur;
}

/**
 * Réponse figée pour une route du moteur. Même forme que le vrai client HTTP :
 * les gestionnaires de `handlers.ts` ne voient aucune différence.
 */
export function reponseDemo(route: RouteMoteur, corps?: Record<string, unknown>): ReponseMoteur {
  const dossierId =
    typeof corps?.dossier_id === "string" && corps.dossier_id ? corps.dossier_id : "DEMO";
  let data: unknown;
  switch (route) {
    case "/sante":
      data = sante;
      break;
    case "/ouvrir":
      data = avecDossier(ouverture, dossierId);
      break;
    case "/repondre":
      // Pas d'état : la première réponse déroule directement la conclusion.
      data = avecDossier(conclusion, dossierId);
      break;
    case "/courrier":
      data = avecDossier(courrier, dossierId);
      break;
    case "/supprimer":
      data = { supprime: true, deja_absent: false };
      break;
  }
  return { joignable: true, statut: 200, corps: { ok: true, data }, retryAfter: null };
}
