import { gererTelechargementCourrier } from "@/lib/server/handlers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function GET(requete: Request): Promise<Response> {
  return gererTelechargementCourrier(requete);
}
