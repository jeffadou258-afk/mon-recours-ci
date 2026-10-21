/**
 * Comptes d'accès à l'administration — définis par la configuration du serveur.
 *
 * Il n'existe aucune base d'utilisateurs dans Mon Recours CI. Les comptes sont
 * donc déclarés dans une variable d'environnement serveur, `MONRECOURS_COMPTES`,
 * qui contient un tableau JSON :
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

export function lireEtatAuth(env: Record<string, string | undefined> = process.env): EtatAuth {
  if (env.MONRECOURS_MODE === "demo") return { etat: "desactive_demo" };

  const secret = env.MONRECOURS_SESSION_SECRET || "";
  if (secret.length < 32) {
    return { etat: "non_configure", raison: "secret de session absent ou trop court" };
  }

  const brut = env.MONRECOURS_COMPTES;
  if (!brut || !brut.trim()) return { etat: "non_configure", raison: "aucun compte configuré" };

  let donnees: unknown;
  try {
    donnees = JSON.parse(brut);
  } catch {
    return { etat: "non_configure", raison: "liste de comptes illisible (JSON invalide)" };
  }
  if (!Array.isArray(donnees)) return { etat: "non_configure", raison: "la liste de comptes doit être un tableau" };

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

  if (comptes.length === 0) return { etat: "non_configure", raison: "aucun compte valide configuré" };
  return { etat: "actif", comptes, secret, ignores };
}

export function trouverCompte(comptes: Compte[], email: string): Compte | null {
  const cible = normaliserEmail(email);
  return comptes.find((c) => c.email === cible) ?? null;
}
