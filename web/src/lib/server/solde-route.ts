import { creerEcrivain, type LigneAudit } from "@/lib/server/auth/audit";
import { lireConfig, type ConfigServeur } from "@/lib/server/config";
import { appelerMoteur, type Recuperateur } from "@/lib/server/moteur";
import { decisionVerificationSolde } from "@/lib/server/solde";
import { origineAutorisee } from "@/lib/server/handlers";

/**
 * Cœur de la route POST /api/admin/solde, isolé du contexte Next pour être
 * testable : la route ne fait que l'appeler avec la requête brute.
 *
 * La session est lue dans l'en-tête `cookie` de la requête — pas dans le
 * magasin de cookies de Next, qui n'existe qu'en cours de requête.
 */
export interface OptionsSolde {
  env?: Record<string, string | undefined>;
  recuperer?: Recuperateur;
  audit?: (ligne: LigneAudit) => Promise<void>;
  config?: ConfigServeur;
}

const ENTETES = { "Cache-Control": "no-store" };

function refus(statut: number, code: string, message: string): Response {
  return Response.json({ ok: false, erreur: { code, message } }, { status: statut, headers: ENTETES });
}

/**
 * Seuls les champs connus de l'incident sortent du serveur : un champ ajouté
 * plus tard côté moteur ne fuit pas sans décision explicite.
 */
function incidentPublic(brut: unknown): Record<string, string | boolean | null> | null {
  if (!brut || typeof brut !== "object") return null;
  const source = brut as Record<string, unknown>;
  const sortie: Record<string, string | boolean | null> = {};
  for (const champ of ["statut", "fournisseur", "detecte_le", "resolu_le", "consequence", "action_attendue"]) {
    const valeur = source[champ];
    sortie[champ] = typeof valeur === "string" ? valeur.slice(0, 300) : null;
  }
  sortie.ouvert = source.ouvert === true;
  sortie.persistant = source.persistant !== false;
  return sortie;
}

export async function executerVerificationSolde(
  requete: Request,
  options: OptionsSolde = {},
): Promise<Response> {
  const env = options.env ?? process.env;
  const audit = options.audit ?? creerEcrivain();

  const cookie = requete.headers.get("cookie");
  const decision = decisionVerificationSolde(cookie, env);
  if (!decision.autorise) {
    return refus(403, "ACCES_REFUSE", "Action réservée à l'administration.");
  }

  // Contrôle d'origine (CSRF) : la règle commune des écritures
  // (`origineAutorisee`, qui tient compte de `Sec-Fetch-Site` et de
  // `X-Forwarded-Host` derrière nginx), plus une exigence propre à cette action
  // d'administration : la requête doit PROUVER sa provenance (en-tête `Origin`
  // ou `Sec-Fetch-Site`). Une requête qui n'en porte aucun est refusée.
  const preuve = requete.headers.get("origin") !== null || requete.headers.get("sec-fetch-site") !== null;
  if (!preuve || !origineAutorisee(requete)) {
    return refus(403, "ORIGINE_REFUSEE", "Origine non autorisée.");
  }

  await audit({
    horodatage: new Date().toISOString(),
    evenement: "verification_solde_llm_demandee",
    compte: decision.compte,
  });

  let config: ConfigServeur;
  try {
    config = options.config ?? lireConfig(env);
  } catch {
    return refus(500, "CONFIGURATION", "Configuration du serveur incomplète.");
  }

  const reponse = await appelerMoteur(
    config,
    "/llm/verifier-solde",
    { verification: true },
    options.recuperer ?? fetch,
  );

  if (!reponse.joignable) {
    return refus(503, "MOTEUR_INJOIGNABLE", "Le moteur ne répond pas : l'incident reste ouvert.");
  }
  if (reponse.statut !== 200) {
    return refus(502, "MOTEUR_ERREUR", "Le moteur a refusé la vérification : l'incident reste ouvert.");
  }

  const corps = (reponse.corps ?? {}) as { ok?: boolean; data?: Record<string, unknown> };
  if (corps.ok === false) {
    return refus(502, "MOTEUR_ERREUR", "Le moteur a refusé la vérification : l'incident reste ouvert.");
  }
  const donnees = corps.data ?? {};

  const simple = (champ: unknown): string | number | boolean | null =>
    typeof champ === "string" || typeof champ === "number" || typeof champ === "boolean" ? champ : null;

  await audit({
    horodatage: new Date().toISOString(),
    evenement:
      donnees.reactive === true ? "solde_llm_verifie_reactif" : "solde_llm_verifie_sans_reactivation",
    compte: decision.compte,
  });

  return Response.json(
    {
      ok: true,
      data: {
        reactive: donnees.reactive === true,
        etat: simple(donnees.etat),
        mode: simple(donnees.mode),
        devise: simple(donnees.devise),
        solde: simple(donnees.solde),
        message: simple(donnees.message),
        manques: Array.isArray(donnees.manques)
          ? donnees.manques.filter((m): m is string => typeof m === "string")
          : [],
        incident: incidentPublic(donnees.incident),
      },
    },
    { status: 200, headers: ENTETES },
  );
}
