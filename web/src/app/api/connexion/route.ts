import { gererConnexion } from "@/lib/server/auth/handlers-auth";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function POST(requete: Request): Promise<Response> {
  return gererConnexion(requete);
}
