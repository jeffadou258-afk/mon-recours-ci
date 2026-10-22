import { evaluerAccesAdmin } from "@/lib/server/auth/acces";

/**
 * Qui a le droit de demander une vérification de solde.
 *
 * Extrait de la route pour être testable sans requête HTTP : la route ne fait
 * ensuite que traduire cette décision en réponse.
 */
export type DecisionSolde =
  | { autorise: true; compte: string }
  | { autorise: false; motif: "anonyme" | "refuse" | "ferme" };

export function decisionVerificationSolde(
  enteteCookie: string | null,
  env: Record<string, string | undefined> = process.env,
): DecisionSolde {
  const decision = evaluerAccesAdmin(enteteCookie, env);
  if (decision.acces === "autorise") {
    return { autorise: true, compte: decision.compte.email };
  }
  return { autorise: false, motif: decision.acces };
}
