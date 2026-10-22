import { executerVerificationSolde } from "@/lib/server/solde-route";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Vérification du solde DeepSeek et réactivation contrôlée.
 *
 * Toute la logique vit dans `solde-route.ts`, testable sans contexte Next ;
 * cette route ne fait que transmettre la requête.
 */
export function POST(requete: Request): Promise<Response> {
  return executerVerificationSolde(requete);
}
