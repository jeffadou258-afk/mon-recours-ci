/**
 * Gestionnaires des routes /api/* de l'interface.
 *
 * Ils n'utilisent que les API Web standard (Request / Response) : les fichiers
 * `src/app/api/<route>/route.ts` de Next.js se contentent de les ré-exporter,
 * et les tests les appellent directement, sans démarrer Next.js.
 *
 * Rôle : contrôler l'entrée, joindre le moteur avec la clé serveur, assainir la
 * sortie, traduire les erreurs. Aucune logique juridique ici.
 */

import { readFile } from "node:fs/promises";
import { PDF_DEMONSTRATION } from "./demo";
import type { CodeErreur, ErreurApi, ResultatApi } from "../types";
import { validerDemande, validerInformationsCourrier, validerReponses } from "../validation";
import {
  assainirCourrier,
  assainirOuverture,
  assainirSuite,
  assainirSante,
  ReponseInattendue,
  reponseAnalyseRefusee,
} from "./assainir";
import { ConfigurationInvalide, lireConfig, type ConfigServeur } from "./config";
import { ConsultationExpiree, CourrierIntrouvable, dernierCourrierPdf } from "./dossiers";
import { appelerMoteur, type Recuperateur, type ReponseMoteur } from "./moteur";
import { identifiantVisiteur, limiteurParDefaut, type LimiteurVisiteurs } from "./limiteur";
import { deballer, emballer, enteteCookie, enteteCookieEfface, lireCookie, nouvelIdentifiant } from "./session";

export const TAILLE_MAX_CORPS = 16 * 1024;

export interface Dependances {
  config?: () => ConfigServeur;
  recuperer?: Recuperateur;
  journal?: (ligne: Record<string, unknown>) => void;
  limiteur?: LimiteurVisiteurs;
}

/** Applique la limite par visiteur ; renvoie une réponse 429 si elle est atteinte. */
function verifierDebitVisiteur(requete: Request, config: ConfigServeur, dep: Dependances): Response | null {
  const attente = (dep.limiteur ?? limiteurParDefaut).consommer(identifiantVisiteur(requete), config.debitVisiteur);
  return attente > 0 ? erreur("DEBIT_DEPASSE", { reessayerDans: attente }) : null;
}

const MESSAGES: Record<CodeErreur, string> = {
  ENTREE_INVALIDE: "La demande envoyée n'est pas valide.",
  TYPE_NON_SUPPORTE: "Format d'envoi non pris en charge.",
  CORPS_TROP_GRAND: "Le message envoyé est trop long.",
  ORIGINE_REFUSEE: "Requête refusée : elle ne provient pas de cette application.",
  SESSION_ABSENTE:
    "Votre consultation a expiré ou n'a pas été trouvée. Recommencez en décrivant votre situation.",
  DOSSIER_INCONNU:
    "Le service ne retrouve pas votre consultation. Recommencez en décrivant votre situation.",
  CONSULTATION_EXPIREE:
    "Cette consultation a dépassé sa durée de conservation (24 heures) : elle a été ou va être supprimée du serveur. Recommencez en décrivant votre situation.",
  DEBIT_DEPASSE: "Le service reçoit trop de demandes en ce moment. Réessayez dans un instant.",
  SERVICE_INDISPONIBLE:
    "Le moteur juridique ne répond pas. Réessayez dans quelques minutes.",
  CONFIGURATION:
    "Le service est mal configuré et ne peut pas joindre le moteur juridique. L'équipe doit intervenir.",
  CATALOGUE_INVALIDE:
    "Le moteur a détecté une incohérence dans ses fiches et refuse de répondre. L'équipe doit intervenir.",
  REPONSE_INVALIDE: "Le moteur a renvoyé une réponse illisible. Aucune information n'est affichée.",
  COURRIER_ABSENT:
    "Aucun courrier n'est disponible pour cette consultation. Rédigez-le d'abord, puis téléchargez-le.",
  RESEAU: "Connexion impossible. Vérifiez votre accès à Internet puis réessayez.",
  INTERNE: "Le moteur a rencontré une erreur interne. Aucune réponse n'a été produite.",
};

const STATUT_HTTP: Record<CodeErreur, number> = {
  ENTREE_INVALIDE: 400,
  TYPE_NON_SUPPORTE: 415,
  CORPS_TROP_GRAND: 413,
  ORIGINE_REFUSEE: 403,
  SESSION_ABSENTE: 409,
  DOSSIER_INCONNU: 409,
  CONSULTATION_EXPIREE: 410,
  DEBIT_DEPASSE: 429,
  SERVICE_INDISPONIBLE: 503,
  CONFIGURATION: 500,
  CATALOGUE_INVALIDE: 503,
  REPONSE_INVALIDE: 502,
  COURRIER_ABSENT: 404,
  RESEAU: 503,
  INTERNE: 502,
};

const REESSAYABLE = new Set<CodeErreur>(["DEBIT_DEPASSE", "SERVICE_INDISPONIBLE", "RESEAU", "INTERNE"]);

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

function erreur(
  code: CodeErreur,
  options: { message?: string; reessayerDans?: number; entetes?: Record<string, string> } = {},
): Response {
  const corps: ErreurApi = {
    code,
    message: options.message ?? MESSAGES[code],
    reessayable: REESSAYABLE.has(code),
    ...(options.reessayerDans !== undefined ? { reessayerDansSecondes: options.reessayerDans } : {}),
  };
  const charge: ResultatApi<never> = { ok: false, erreur: corps };
  const entetes = { ...(options.entetes ?? {}) };
  if (options.reessayerDans !== undefined) entetes["Retry-After"] = String(options.reessayerDans);
  return json(STATUT_HTTP[code], charge, entetes);
}

function succes<T>(data: T, entetes: Record<string, string> = {}): Response {
  const charge: ResultatApi<T> = { ok: true, data };
  return json(200, charge, entetes);
}

function obtenirConfig(dep: Dependances): ConfigServeur | Response {
  try {
    return (dep.config ?? lireConfig)();
  } catch (e) {
    if (e instanceof ConfigurationInvalide) {
      (dep.journal ?? journalParDefaut)({ evenement: "configuration_invalide", detail: e.message });
      return erreur("CONFIGURATION");
    }
    throw e;
  }
}

function journalParDefaut(ligne: Record<string, unknown>): void {
  // Jamais de demande, de réponse ni d'identifiant de dossier dans le journal.
  console.warn(JSON.stringify({ horodatage: new Date().toISOString(), ...ligne }));
}

/** Refuse les requêtes envoyées depuis un autre site (protection CSRF). */
export function origineAutorisee(requete: Request): boolean {
  const site = requete.headers.get("sec-fetch-site");
  if (site && site !== "same-origin" && site !== "none") return false;
  const origine = requete.headers.get("origin");
  if (!origine) return true;
  const hote = requete.headers.get("x-forwarded-host") ?? requete.headers.get("host");
  try {
    return new URL(origine).host === hote;
  } catch {
    return false;
  }
}

export async function lireCorpsJson(requete: Request): Promise<{ corps: Record<string, unknown> } | Response> {
  const type = (requete.headers.get("content-type") ?? "").split(";")[0]?.trim().toLowerCase();
  if (type !== "application/json") return erreur("TYPE_NON_SUPPORTE");
  const longueurAnnoncee = Number(requete.headers.get("content-length") ?? "0");
  if (longueurAnnoncee > TAILLE_MAX_CORPS) return erreur("CORPS_TROP_GRAND");
  const brut = await requete.text();
  if (Buffer.byteLength(brut, "utf8") > TAILLE_MAX_CORPS) return erreur("CORPS_TROP_GRAND");
  let charge: unknown;
  try {
    charge = JSON.parse(brut);
  } catch {
    return erreur("ENTREE_INVALIDE", { message: "Le message envoyé n'est pas un JSON valide." });
  }
  if (typeof charge !== "object" || charge === null || Array.isArray(charge)) {
    return erreur("ENTREE_INVALIDE", { message: "Le message envoyé doit être un objet." });
  }
  return { corps: charge as Record<string, unknown> };
}

function securise(requete: Request, config: ConfigServeur): boolean {
  if (config.production) return true;
  const proto = requete.headers.get("x-forwarded-proto");
  return proto === "https" || new URL(requete.url).protocol === "https:";
}

/** Traduit une réponse du moteur qui n'est pas un succès. */
function traduireEchec(reponse: ReponseMoteur, dep: Dependances, route: string): Response {
  const journal = dep.journal ?? journalParDefaut;
  if (!reponse.joignable) {
    journal({ evenement: "moteur_injoignable", route, raison: reponse.raison });
    return erreur("SERVICE_INDISPONIBLE");
  }
  const corps = (reponse.corps ?? {}) as { erreur?: { code?: unknown; message?: unknown } };
  const code = typeof corps.erreur?.code === "string" ? corps.erreur.code : null;
  journal({ evenement: "moteur_refus", route, statut: reponse.statut, code });

  if (reponse.statut === 401) return erreur("CONFIGURATION");
  if (reponse.statut === 429) {
    const attente = Math.max(1, Math.min(300, Number(reponse.retryAfter) || 30));
    return erreur("DEBIT_DEPASSE", { reessayerDans: attente });
  }
  if (reponse.statut === 422) {
    switch (code) {
      case "ENTREE_INVALIDE": {
        // Les messages ENTREE_INVALIDE du moteur sont des phrases fixes, sans donnée
        // personnelle ni chemin (core/service.py) : on les transmet pour guider.
        const message = typeof corps.erreur?.message === "string" ? corps.erreur.message : undefined;
        return erreur("ENTREE_INVALIDE", message ? { message: `Le moteur refuse l'entrée : ${message}` } : {});
      }
      case "DOSSIER_INCONNU":
      case "AUCUNE_FICHE":
        return erreur("DOSSIER_INCONNU");
      case "DOSSIER_EXPIRE":
        return erreur("CONSULTATION_EXPIREE");
      case "DOSSIER_INVALIDE":
        return erreur("SESSION_ABSENTE");
      case "CATALOGUE_INVALIDE":
        return erreur("CATALOGUE_INVALIDE");
      default:
        return erreur("INTERNE");
    }
  }
  if (reponse.statut >= 500) return erreur("SERVICE_INDISPONIBLE");
  // 400 / 404 / 405 / 413 / 415 du moteur : la couche web a mal construit sa requête.
  return erreur("INTERNE");
}

function estSucces(reponse: ReponseMoteur): reponse is Extract<ReponseMoteur, { joignable: true }> {
  return (
    reponse.joignable &&
    reponse.statut === 200 &&
    typeof reponse.corps === "object" &&
    reponse.corps !== null &&
    (reponse.corps as { ok?: unknown }).ok === true
  );
}

// ---------------------------------------------------------------------------
// GET /api/sante
// ---------------------------------------------------------------------------

export async function gererSante(_requete: Request, dep: Dependances = {}): Promise<Response> {
  const config = obtenirConfig(dep);
  if (config instanceof Response) return config;
  const reponse = await appelerMoteur(config, "/sante", undefined, dep.recuperer);
  if (!estSucces(reponse)) return traduireEchec(reponse, dep, "/sante");
  return succes(assainirSante((reponse.corps as { data?: unknown }).data));
}

/** Variante pour les composants serveur : renvoie `null` si le moteur est indisponible. */
export async function obtenirSante(dep: Dependances = {}) {
  let config: ConfigServeur;
  try {
    config = (dep.config ?? lireConfig)();
  } catch {
    return null;
  }
  const reponse = await appelerMoteur(config, "/sante", undefined, dep.recuperer);
  if (!estSucces(reponse)) return null;
  try {
    return assainirSante((reponse.corps as { data?: unknown }).data);
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// POST /api/ouvrir   { demande }
// ---------------------------------------------------------------------------

export async function gererOuvrir(requete: Request, dep: Dependances = {}): Promise<Response> {
  if (!origineAutorisee(requete)) return erreur("ORIGINE_REFUSEE");
  const config = obtenirConfig(dep);
  if (config instanceof Response) return config;
  const trop = verifierDebitVisiteur(requete, config, dep);
  if (trop) return trop;
  const lu = await lireCorpsJson(requete);
  if (lu instanceof Response) return lu;

  const demande = validerDemande(lu.corps.demande);
  if (!demande.ok) return erreur("ENTREE_INVALIDE", { message: demande.message });

  // Nouvel identifiant à chaque ouverture : une nouvelle demande ne peut jamais
  // rouvrir ou lire un dossier précédent.
  const dossierId = nouvelIdentifiant();
  const reponse = await appelerMoteur(
    config,
    "/ouvrir",
    { dossier_id: dossierId, demande: demande.valeur },
    dep.recuperer,
  );
  if (!estSucces(reponse)) return traduireEchec(reponse, dep, "/ouvrir");

  try {
    const vue = assainirOuverture((reponse.corps as { data?: unknown }).data);
    const entetes: Record<string, string> = {};
    // Le cookie relie le navigateur à SA consultation : il sert à répondre aux
    // questions, et à supprimer la consultation (le dossier existe dans tous les cas).
    entetes["Set-Cookie"] = enteteCookie(emballer(dossierId, config.secretSession), securise(requete, config));
    return succes(vue, entetes);
  } catch (e) {
    if (e instanceof ReponseInattendue) return erreur("REPONSE_INVALIDE");
    throw e;
  }
}

// ---------------------------------------------------------------------------
// POST /api/repondre   { reponses }
// ---------------------------------------------------------------------------

export async function gererRepondre(requete: Request, dep: Dependances = {}): Promise<Response> {
  if (!origineAutorisee(requete)) return erreur("ORIGINE_REFUSEE");
  const config = obtenirConfig(dep);
  if (config instanceof Response) return config;

  const dossierId = deballer(lireCookie(requete.headers.get("cookie")), config.secretSession);
  if (!dossierId) return erreur("SESSION_ABSENTE");
  const trop = verifierDebitVisiteur(requete, config, dep);
  if (trop) return trop;

  const lu = await lireCorpsJson(requete);
  if (lu instanceof Response) return lu;
  const reponses = validerReponses(lu.corps.reponses);
  if (!reponses.ok) return erreur("ENTREE_INVALIDE", { message: reponses.message });

  const reponse = await appelerMoteur(
    config,
    "/repondre",
    { dossier_id: dossierId, reponses: reponses.valeur },
    dep.recuperer,
  );

  if (
    reponse.joignable &&
    reponse.statut === 422 &&
    (reponse.corps as { erreur?: { code?: unknown } } | null)?.erreur?.code === "ANALYSE_REFUSEE"
  ) {
    return succes(reponseAnalyseRefusee());
  }
  if (!estSucces(reponse)) return traduireEchec(reponse, dep, "/repondre");

  try {
    return succes(assainirSuite((reponse.corps as { data?: unknown }).data));
  } catch (e) {
    if (e instanceof ReponseInattendue) return erreur("REPONSE_INVALIDE");
    throw e;
  }
}

// ---------------------------------------------------------------------------
// POST /api/courrier   { informations }   — régénère le courrier du dossier
// ---------------------------------------------------------------------------

export async function gererCourrier(requete: Request, dep: Dependances = {}): Promise<Response> {
  if (!origineAutorisee(requete)) return erreur("ORIGINE_REFUSEE");
  const config = obtenirConfig(dep);
  if (config instanceof Response) return config;

  const dossierId = deballer(lireCookie(requete.headers.get("cookie")), config.secretSession);
  if (!dossierId) return erreur("SESSION_ABSENTE");
  const trop = verifierDebitVisiteur(requete, config, dep);
  if (trop) return trop;

  const lu = await lireCorpsJson(requete);
  if (lu instanceof Response) return lu;
  const informations = validerInformationsCourrier(lu.corps.informations);
  if (!informations.ok) return erreur("ENTREE_INVALIDE", { message: informations.message });

  const reponse = await appelerMoteur(
    config,
    "/courrier",
    { dossier_id: dossierId, informations: informations.valeur },
    dep.recuperer,
  );
  if (!estSucces(reponse)) return traduireEchec(reponse, dep, "/courrier");

  try {
    return succes(assainirCourrier((reponse.corps as { data?: unknown }).data));
  } catch (e) {
    if (e instanceof ReponseInattendue) return erreur("REPONSE_INVALIDE");
    throw e;
  }
}

// ---------------------------------------------------------------------------
// GET /api/courrier/telecharger   — le PDF du dossier, et lui seul
// ---------------------------------------------------------------------------

export async function gererTelechargementCourrier(
  requete: Request,
  dep: Dependances = {},
): Promise<Response> {
  const config = obtenirConfig(dep);
  if (config instanceof Response) return config;

  // L'identifiant vient du cookie signé : on ne peut pas demander le dossier d'autrui.
  const dossierId = deballer(lireCookie(requete.headers.get("cookie")), config.secretSession);
  if (!dossierId) return erreur("SESSION_ABSENTE");
  const trop = verifierDebitVisiteur(requete, config, dep);
  if (trop) return trop;

  // Mode démonstration : le PDF est un fichier statique livré avec l'application.
  // Aucune lecture de `DOSSIERS/`, aucune écriture : rien ne dépend d'un disque
  // persistant, ce qui est exactement la contrainte de Vercel.
  if (config.demo) {
    const origine = new URL(requete.url).origin;
    const statique = await fetch(`${origine}/${PDF_DEMONSTRATION}`, { cache: "no-store" });
    if (!statique.ok) return erreur("COURRIER_ABSENT");
    const octetsDemo = new Uint8Array(await statique.arrayBuffer());
    const nomDemo = PDF_DEMONSTRATION.split("/").pop() as string;
    return new Response(octetsDemo, {
      status: 200,
      headers: {
        "Content-Type": "application/pdf",
        "Content-Length": String(octetsDemo.length),
        "Content-Disposition": `attachment; filename="${nomDemo}"`,
        "Cache-Control": "no-store, max-age=0",
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; object-src 'none'",
        "X-Mode": "demonstration",
      },
    });
  }

  let courrier;
  try {
    courrier = await dernierCourrierPdf(dossierId);
  } catch (e) {
    if (e instanceof ConsultationExpiree) return erreur("CONSULTATION_EXPIREE");
    if (e instanceof CourrierIntrouvable) return erreur("COURRIER_ABSENT");
    throw e;
  }

  const octets = await readFile(courrier.chemin);
  return new Response(new Uint8Array(octets), {
    status: 200,
    headers: {
      "Content-Type": "application/pdf",
      "Content-Length": String(courrier.octets),
      // Nom fixé par le serveur : rien de ce que l'utilisateur a saisi n'y entre.
      "Content-Disposition": `attachment; filename="${courrier.nom}"`,
      "Cache-Control": "no-store, max-age=0",
      "X-Content-Type-Options": "nosniff",
      "Content-Security-Policy": "default-src 'none'; object-src 'none'",
    },
  });
}

// ---------------------------------------------------------------------------
// POST /api/supprimer   {}   — la personne supprime sa consultation
// ---------------------------------------------------------------------------

export async function gererSupprimer(requete: Request, dep: Dependances = {}): Promise<Response> {
  if (!origineAutorisee(requete)) return erreur("ORIGINE_REFUSEE");
  const config = obtenirConfig(dep);
  if (config instanceof Response) return config;
  const dossierId = deballer(lireCookie(requete.headers.get("cookie")), config.secretSession);
  if (!dossierId) return erreur("SESSION_ABSENTE");
  const trop = verifierDebitVisiteur(requete, config, dep);
  if (trop) return trop;

  const reponse = await appelerMoteur(config, "/supprimer", { dossier_id: dossierId }, dep.recuperer);
  if (!estSucces(reponse)) return traduireEchec(reponse, dep, "/supprimer");
  const data = (reponse.corps as { data?: { supprime?: unknown; deja_absent?: unknown } }).data ?? {};
  return succes(
    { supprime: data.supprime === true, dejaAbsent: data.deja_absent === true },
    { "Set-Cookie": enteteCookieEfface(securise(requete, config)) },
  );
}
