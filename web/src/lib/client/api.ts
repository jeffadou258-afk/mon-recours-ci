/**
 * Appels du navigateur vers la couche serveur de l'interface (même origine).
 * Le navigateur ne connaît ni l'URL du moteur, ni sa clé, ni l'identifiant de
 * dossier (cookie HttpOnly).
 */

import type { ResultatApi, VueOuverture, VueSuite } from "../types";

async function appeler<T>(chemin: string, corps: unknown): Promise<ResultatApi<T>> {
  let reponse: Response;
  try {
    reponse = await fetch(chemin, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(corps),
      credentials: "same-origin",
      cache: "no-store",
    });
  } catch {
    return {
      ok: false,
      erreur: {
        code: "RESEAU",
        message: "Connexion impossible. Vérifiez votre accès à Internet puis réessayez.",
        reessayable: true,
      },
    };
  }
  try {
    const charge = (await reponse.json()) as ResultatApi<T>;
    if (charge && typeof charge === "object" && "ok" in charge) return charge;
  } catch {
    // corps illisible : traité ci-dessous
  }
  return {
    ok: false,
    erreur: {
      code: reponse.status >= 500 ? "SERVICE_INDISPONIBLE" : "REPONSE_INVALIDE",
      message:
        reponse.status >= 500
          ? "Le service ne répond pas correctement. Réessayez dans quelques minutes."
          : "La réponse reçue est illisible. Aucune information n'est affichée.",
      reessayable: reponse.status >= 500,
    },
  };
}

export function ouvrirDossier(demande: string): Promise<ResultatApi<VueOuverture>> {
  return appeler<VueOuverture>("/api/ouvrir", { demande });
}

export function envoyerReponses(reponses: Record<string, string | null>): Promise<ResultatApi<VueSuite>> {
  return appeler<VueSuite>("/api/repondre", { reponses });
}
