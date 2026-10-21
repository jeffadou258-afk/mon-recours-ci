/**
 * Routes d'authentification : POST /api/connexion et POST /api/deconnexion.
 *
 * Mêmes principes que les autres routes /api/* : API Web standard, aucune
 * dépendance à Next.js, protection CSRF par l'origine, corps JSON borné.
 *
 * Protections propres à la connexion :
 *  - réponse IDENTIQUE (message, statut) que l'adresse existe ou non, et
 *    vérification scrypt effectuée dans les deux cas (durée comparable) ;
 *  - limite de tentatives par visiteur ET par adresse saisie ;
 *  - aucun succès simulé : sans configuration valide, la route répond 503.
 */

import { lireEtatAuth, emailValide, LONGUEUR_MAX_EMAIL, normaliserEmail, trouverCompte } from "./comptes";
import { LONGUEUR_MAX_MOT_DE_PASSE, verifierMotDePasse } from "./motdepasse";
import { creerJeton, enteteCookieAdmin, enteteCookieAdminEfface, NOM_COOKIE_ADMIN, verifierJeton } from "./jeton";
import { creerEcrivain, empreinteSaisie, type Ecrivain } from "./audit";
import { identifiantVisiteur, LimiteurVisiteurs } from "../limiteur";
import { lireCookie } from "../session";
import { lireCorpsJson, origineAutorisee } from "../handlers";

export type CodeErreurAuth =
  | "ENTREE_INVALIDE"
  | "ORIGINE_REFUSEE"
  | "IDENTIFIANTS_INVALIDES"
  | "TROP_DE_TENTATIVES"
  | "AUTH_NON_CONFIGUREE"
  | "AUTH_DESACTIVEE_DEMO";

const MESSAGES: Record<CodeErreurAuth, string> = {
  ENTREE_INVALIDE: "Saisissez une adresse e-mail valide et votre mot de passe.",
  ORIGINE_REFUSEE: "Requête refusée : elle ne provient pas de cette application.",
  IDENTIFIANTS_INVALIDES: "Adresse e-mail ou mot de passe incorrect.",
  TROP_DE_TENTATIVES: "Trop de tentatives de connexion. Patientez avant de réessayer.",
  AUTH_NON_CONFIGUREE: "La connexion n'est pas disponible sur cette instance : aucun compte n'est configuré.",
  AUTH_DESACTIVEE_DEMO: "L'espace d'administration est désactivé dans la démonstration publique.",
};

const STATUTS: Record<CodeErreurAuth, number> = {
  ENTREE_INVALIDE: 400,
  ORIGINE_REFUSEE: 403,
  IDENTIFIANTS_INVALIDES: 401,
  TROP_DE_TENTATIVES: 429,
  AUTH_NON_CONFIGUREE: 503,
  AUTH_DESACTIVEE_DEMO: 503,
};

/** Tentatives autorisées par minute. */
export const TENTATIVES_PAR_VISITEUR = 5;
export const TENTATIVES_PAR_ADRESSE = 5;

export interface DependancesAuth {
  env?: Record<string, string | undefined>;
  audit?: Ecrivain;
  limiteurVisiteurs?: LimiteurVisiteurs;
  limiteurAdresses?: LimiteurVisiteurs;
  maintenantS?: () => number;
}

const limiteurVisiteursParDefaut = new LimiteurVisiteurs();
const limiteurAdressesParDefaut = new LimiteurVisiteurs();

function json(statut: number, charge: unknown, entetes: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(charge), {
    status: statut,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Cache-Control": "no-store",
      "X-Content-Type-Options": "nosniff",
      ...entetes,
    },
  });
}

function echec(code: CodeErreurAuth, reessayerDans?: number): Response {
  return json(
    STATUTS[code],
    {
      ok: false,
      erreur: {
        code,
        message: MESSAGES[code],
        reessayable: code === "TROP_DE_TENTATIVES",
        ...(reessayerDans ? { reessayerDansSecondes: reessayerDans } : {}),
      },
    },
    reessayerDans ? { "Retry-After": String(reessayerDans) } : {},
  );
}

function securise(requete: Request, env: Record<string, string | undefined>): boolean {
  if (env.NODE_ENV === "production") return true;
  const proto = requete.headers.get("x-forwarded-proto");
  return proto === "https" || new URL(requete.url).protocol === "https:";
}

function maintenant(dep: DependancesAuth): string {
  return new Date((dep.maintenantS?.() ?? Date.now() / 1000) * 1000).toISOString();
}

// ---------------------------------------------------------------------------
// POST /api/connexion   { email, motDePasse }
// ---------------------------------------------------------------------------

export async function gererConnexion(requete: Request, dep: DependancesAuth = {}): Promise<Response> {
  const env = dep.env ?? process.env;
  const audit = dep.audit ?? creerEcrivain(env);
  if (!origineAutorisee(requete)) return echec("ORIGINE_REFUSEE");

  const etat = lireEtatAuth(env);
  if (etat.etat === "desactive_demo") return echec("AUTH_DESACTIVEE_DEMO");
  if (etat.etat !== "actif") {
    // La raison (phrase fixe, sans contenu de configuration) aide l'exploitant ; le visiteur
    // ne reçoit qu'un message générique.
    await audit({ horodatage: maintenant(dep), evenement: "authentification_fermee", detail: etat.raison });
    return echec("AUTH_NON_CONFIGUREE");
  }

  const lu = await lireCorpsJson(requete);
  if (lu instanceof Response) return echec("ENTREE_INVALIDE");
  const emailBrut = lu.corps.email;
  const motDePasse = lu.corps.motDePasse;
  if (
    typeof emailBrut !== "string" ||
    typeof motDePasse !== "string" ||
    emailBrut.length > LONGUEUR_MAX_EMAIL ||
    motDePasse.length === 0 ||
    motDePasse.length > LONGUEUR_MAX_MOT_DE_PASSE
  ) {
    return echec("ENTREE_INVALIDE");
  }
  const email = normaliserEmail(emailBrut);
  if (!emailValide(email)) return echec("ENTREE_INVALIDE");

  const attenteVisiteur = (dep.limiteurVisiteurs ?? limiteurVisiteursParDefaut).consommer(
    `connexion:${identifiantVisiteur(requete)}`,
    TENTATIVES_PAR_VISITEUR,
  );
  const attenteAdresse = (dep.limiteurAdresses ?? limiteurAdressesParDefaut).consommer(
    `connexion:${email}`,
    TENTATIVES_PAR_ADRESSE,
  );
  const attente = Math.max(attenteVisiteur, attenteAdresse);
  if (attente > 0) {
    await audit({
      horodatage: maintenant(dep),
      evenement: "connexion_limitee",
      empreinteSaisie: empreinteSaisie(email, etat.secret),
    });
    return echec("TROP_DE_TENTATIVES", attente);
  }

  const compte = trouverCompte(etat.comptes, email);
  const valide = await verifierMotDePasse(motDePasse, compte?.empreinte ?? null);
  if (!compte || !valide) {
    await audit({
      horodatage: maintenant(dep),
      evenement: "connexion_refusee",
      empreinteSaisie: empreinteSaisie(email, etat.secret),
    });
    return echec("IDENTIFIANTS_INVALIDES");
  }

  const jeton = creerJeton(compte, etat.secret, dep.maintenantS?.());
  await audit({ horodatage: maintenant(dep), evenement: "connexion_reussie", compte: compte.email });
  // La destination est fixée par le serveur : aucun paramètre de redirection n'est accepté.
  return json(200, { ok: true, data: { redirection: "/admin" } }, { "Set-Cookie": enteteCookieAdmin(jeton, securise(requete, env)) });
}

// ---------------------------------------------------------------------------
// POST /api/deconnexion   (formulaire HTML ou fetch)
// ---------------------------------------------------------------------------

export async function gererDeconnexion(requete: Request, dep: DependancesAuth = {}): Promise<Response> {
  const env = dep.env ?? process.env;
  const audit = dep.audit ?? creerEcrivain(env);
  if (!origineAutorisee(requete)) return echec("ORIGINE_REFUSEE");

  const etat = lireEtatAuth(env);
  if (etat.etat === "actif") {
    const compte = verifierJeton(
      lireCookie(requete.headers.get("cookie"), NOM_COOKIE_ADMIN),
      etat.comptes,
      etat.secret,
      dep.maintenantS?.(),
    );
    if (compte) await audit({ horodatage: maintenant(dep), evenement: "deconnexion", compte: compte.email });
  }
  // Le cookie est effacé dans tous les cas, même si la session était déjà invalide.
  return new Response(null, {
    status: 303,
    headers: {
      Location: "/connexion?deconnecte=1",
      "Set-Cookie": enteteCookieAdminEfface(securise(requete, env)),
      "Cache-Control": "no-store",
    },
  });
}
