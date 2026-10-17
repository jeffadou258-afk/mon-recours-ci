import { gererOuvrir } from "@/lib/server/handlers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function POST(requete: Request): Promise<Response> {
  return gererOuvrir(requete);
}
