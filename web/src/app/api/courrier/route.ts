import { gererCourrier } from "@/lib/server/handlers";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export function POST(requete: Request): Promise<Response> {
  return gererCourrier(requete);
}
