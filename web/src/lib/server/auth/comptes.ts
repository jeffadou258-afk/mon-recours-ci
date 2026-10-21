/**
 * Comptes d'accès à l'administration — définis par la configuration du serveur.
 *
 * Il n'existe aucune base d'utilisateurs dans Mon Recours CI. Les comptes sont
 * déclarés côté serveur, par UNE seule des deux sources suivantes :
 *
 *   - `MONRECOURS_COMPTES_FICHIER` (recommandé) : chemin ABSOLU d'un fichier JSON,
 *     fichier ordinaire (pas un lien symbolique), propriété de l'utilisateur du
 *     service, droits 0600 ou 0400, 64 Kio au plus. Relu à chaque requête :
 *     retirer un compte du fichier ferme ses sessions sans redémarrage ;
 *   - `MONRECOURS_COMPTES` (compatibilité) : le même tableau JSON, en variable.
 *
 * PRIORITÉ : il n'y en a pas. Si les deux sont définies, la configuration est
 * jugée AMBIGUË et l'administration reste fermée, pour qu'on ne croie jamais
 * avoir retiré un compte d'une source alors que l'autre l'accorde encore.
 *
 * Format (dans les deux cas) :
 *
 *   [{"email":"…","role":"administrateur","motDePasse":"scrypt$16384$8$1$…$…"}]
 *
 * - `motDePasse` est une EMPREINTE scrypt produite par `scripts/creer-compte.mjs`,
 *   jamais un mot de passe en clair ;
 * - `role` vaut `administrateur` ou `lecteur` ; seul `administrateur` ouvre `/admin`.
 *   Le rôle est relu ici à chaque requête : il ne vient jamais du navigateur.
 *
 * L'administration est FERMÉE dans trois cas, sans jamais simuler une réussite :
 *   - mode démonstration (`MONRECOURS_MODE=demo`) ;
 *   - aucun compte valide configuré ;
 *   - secret de session absent ou trop court.
 */

import { lstatSync, readFileSync } from "node:fs";
import { isAbsolute } from "node:path";
import { lireEmpreinte } from "./motdepasse";

export const ROLES = ["administrateur", "lecteur"] as const;
export type Role = (typeof ROLES)[number];

export interface Compte {
  email: string;
  role: Role;
  empreinte: string;
}

export type EtatAuth =
  | { etat: "actif"; comptes: Compte[]; secret: string; ignores: number }
  | { etat: "desactive_demo" }
  | { etat: "non_configure"; raison: string };

const MOTIF_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
export const LONGUEUR_MAX_EMAIL = 254;

export function normaliserEmail(email: string): string {
  return email.trim().toLowerCase();
}

export function emailValide(email: string): boolean {
  return email.length <= LONGUEUR_MAX_EMAIL && MOTIF_EMAIL.test(email);
}

/** Taille maximale du fichier de comptes. */
export const TAILLE_MAX_FICHIER_COMPTES = 64 * 1024;

type Lecture = { ok: true; texte: string } | { ok: false; raison: string };

/**
 * Lit le fichier de comptes en refusant toute situation douteuse. Les messages
 * d'erreur ne contiennent JAMAIS le contenu du fichier (adresses, empreintes).
 */
export function lireFichierComptes(chemin: string): Lecture {
  if (!isAbsolute(chemin)) return { ok: false, raison: "chemin du fichier de comptes non absolu" };
  let infos;
  try {
    infos = lstatSync(chemin);
  } catch {
    return { ok: false, raison: "fichier de comptes introuvable ou inaccessible" };
  }
  if (infos.isSymbolicLink()) return { ok: false, raison: "le fichier de comptes ne doit pas être un lien symbolique" };
  if (!infos.isFile()) return { ok: false, raison: "le fichier de comptes n'est pas un fichier ordinaire" };
  if ((infos.mode & 0o077) !== 0) {
    return { ok: false, raison: "permissions du fichier de comptes trop larges (attendu : 0600 ou 0400)" };
  }
  const uid = typeof process.getuid === "function" ? process.getuid() : null;
  if (uid !== null && infos.uid !== uid) {
    return { ok: false, raison: "le fichier de comptes doit appartenir à l'utilisateur du service" };
  }
  if (infos.size > TAILLE_MAX_FICHIER_COMPTES) return { ok: false, raison: "fichier de comptes trop volumineux" };
  try {
    return { ok: true, texte: readFileSync(chemin, "utf8") };
  } catch {
    return { ok: false, raison: "fichier de comptes illisible" };
  }
}

function analyserComptes(brut: string): { ok: true; comptes: Compte[]; ignores: number } | { ok: false; raison: string } {
  let donnees: unknown;
  try {
    donnees = JSON.parse(brut);
  } catch {
    return { ok: false, raison: "liste de comptes illisible (JSON invalide)" };
  }
  if (!Array.isArray(donnees)) return { ok: false, raison: "la liste de comptes doit être un tableau" };

  const comptes: Compte[] = [];
  const vus = new Set<string>();
  let ignores = 0;
  for (const entree of donnees) {
    if (typeof entree !== "object" || entree === null) {
      ignores++;
      continue;
    }
    const e = entree as Record<string, unknown>;
    const email = typeof e.email === "string" ? normaliserEmail(e.email) : "";
    const role = e.role;
    const empreinte = typeof e.motDePasse === "string" ? e.motDePasse.trim() : "";
    if (
      !emailValide(email) ||
      !ROLES.includes(role as Role) ||
      lireEmpreinte(empreinte) === null ||
      vus.has(email)
    ) {
      // Entrée incomplète, rôle inconnu, empreinte faible ou doublon : écartée, jamais devinée.
      ignores++;
      continue;
    }
    vus.add(email);
    comptes.push({ email, role: role as Role, empreinte });
  }
  return { ok: true, comptes, ignores };
}

export function lireEtatAuth(env: Record<string, string | undefined> = process.env): EtatAuth {
  if (env.MONRECOURS_MODE === "demo") return { etat: "desactive_demo" };

  const secret = env.MONRECOURS_SESSION_SECRET || "";
  if (secret.length < 32) {
    return { etat: "non_configure", raison: "secret de session absent ou trop court" };
  }

  const fichier = env.MONRECOURS_COMPTES_FICHIER?.trim();
  const variable = env.MONRECOURS_COMPTES?.trim();
  if (fichier && variable) {
    return {
      etat: "non_configure",
      raison: "configuration ambiguë : MONRECOURS_COMPTES et MONRECOURS_COMPTES_FICHIER sont toutes deux définies",
    };
  }

  let brut: string;
  if (fichier) {
    const lecture = lireFichierComptes(fichier);
    if (!lecture.ok) return { etat: "non_configure", raison: lecture.raison };
    brut = lecture.texte;
  } else if (variable) {
    brut = variable;
  } else {
    return { etat: "non_configure", raison: "aucun compte configuré" };
  }

  const analyse = analyserComptes(brut);
  if (!analyse.ok) return { etat: "non_configure", raison: analyse.raison };
  if (analyse.comptes.length === 0) return { etat: "non_configure", raison: "aucun compte valide configuré" };
  return { etat: "actif", comptes: analyse.comptes, secret, ignores: analyse.ignores };
}

export function trouverCompte(comptes: Compte[], email: string): Compte | null {
  const cible = normaliserEmail(email);
  return comptes.find((c) => c.email === cible) ?? null;
}
