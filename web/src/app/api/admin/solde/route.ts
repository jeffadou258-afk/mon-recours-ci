import { cookies } from "next/headers";
import { decisionVerificationSolde } from "@/lib/server/solde";
import { creerEcrivain } from "@/lib/server/auth/audit";
import { lireConfig } from "@/lib/server/config";
import { appelerMoteur } from "@/lib/server/moteur";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Vérification du solde DeepSeek et réactivation contrôlée.
 *
 * Trois refus possibles, tous explicites : pas de session administrateur, pas
 * d'origine légitime, moteur injoignable. Aucun succès n'est jamais supposé —
 * la décision vient du moteur, qui a interrogé le fournisseur pour de vrai.
 */
export async function POST(requete: Request): Promise<Response> {
  const magasin = await cookies();
  const entete = magasin
    .getAll()
    .map((c) => `${c.name}=${encodeURIComponent(c.value)}`)
    .join("; ");
  const decision = decisionVerificationSolde(entete || null);

  if (!decision.autorise) {
    return Response.json(
      { ok: false, erreur: { code: "ACCES_REFUSE", message: "Action réservée à l'administration." } },
      { status: 403, headers: { "Cache-Control": "no-store" } },
    );
  }

  // Même contrôle d'origine que les autres écritures : un formulaire étranger ne
  // doit pas pouvoir déclencher un appel au fournisseur.
  const origine = requete.headers.get("origin");
  const site = requete.headers.get("sec-fetch-site");
  const hote = requete.headers.get("host");
  if (origine && hote) {
    let accepte = false;
    try {
      accepte = new URL(origine).host === hote;
    } catch {
      accepte = false;
    }
    if (!accepte && !(origine === "null" && site === "same-origin")) {
      return Response.json(
        { ok: false, erreur: { code: "ORIGINE_REFUSEE", message: "Origine non autorisée." } },
        { status: 403, headers: { "Cache-Control": "no-store" } },
      );
    }
  }

  const audit = creerEcrivain();
  await audit({
    horodatage: new Date().toISOString(),
    evenement: "verification_solde_llm_demandee",
    compte: decision.compte,
  });

  let config;
  try {
    config = lireConfig();
  } catch {
    return Response.json(
      { ok: false, erreur: { code: "CONFIGURATION", message: "Configuration du serveur incomplète." } },
      { status: 500, headers: { "Cache-Control": "no-store" } },
    );
  }

  const reponse = await appelerMoteur(config, "/llm/verifier-solde", { verification: true });
  if (!reponse.joignable) {
    return Response.json(
      {
        ok: false,
        erreur: {
          code: "MOTEUR_INJOIGNABLE",
          message: "Le moteur ne répond pas : l'incident reste ouvert.",
        },
      },
      { status: 503, headers: { "Cache-Control": "no-store" } },
    );
  }
  if (reponse.statut !== 200) {
    return Response.json(
      {
        ok: false,
        erreur: {
          code: "MOTEUR_ERREUR",
          message: "Le moteur a refusé la vérification : l'incident reste ouvert.",
        },
      },
      { status: 502, headers: { "Cache-Control": "no-store" } },
    );
  }

  // On ne renvoie que des champs connus : une clé ne peut pas fuir par ici.
  const corps = (reponse.corps ?? {}) as { ok?: boolean; data?: Record<string, unknown> };
  const donnees = corps.data ?? {};
  const autorise = (champ: unknown) =>
    typeof champ === "string" || typeof champ === "number" || typeof champ === "boolean"
      ? champ
      : null;

  await audit({
    horodatage: new Date().toISOString(),
    evenement: donnees.reactive === true ? "solde_llm_verifie_reactif" : "solde_llm_verifie_sans_reactivation",
    compte: decision.compte,
  });

  return Response.json(
    {
      ok: true,
      data: {
        reactive: donnees.reactive === true,
        etat: autorise(donnees.etat),
        mode: autorise(donnees.mode),
        devise: autorise(donnees.devise),
        solde: autorise(donnees.solde),
        message: autorise(donnees.message),
        manques: Array.isArray(donnees.manques) ? donnees.manques.filter((m) => typeof m === "string") : [],
        incident: donnees.incident ?? null,
      },
    },
    { status: 200, headers: { "Cache-Control": "no-store" } },
  );
}
