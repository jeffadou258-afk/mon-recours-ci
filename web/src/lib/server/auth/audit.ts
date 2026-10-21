/**
 * Journal d'audit des actions d'administration.
 *
 * Chaque événement est TOUJOURS écrit sur la sortie du serveur (une ligne JSON,
 * comme le reste de l'application). S'il est configuré, il est AUSSI ajouté au
 * fichier `MONRECOURS_AUDIT_FICHIER` (JSON Lines, chemin absolu), qui est alors
 * consultable depuis /admin. Sans ce fichier — par exemple sur un hébergement
 * sans disque persistant —, l'espace d'administration affiche « Non connecté ».
 *
 * Ce qui n'est JAMAIS écrit : mot de passe (même faux), cookie, adresse IP,
 * contenu d'une consultation. Une tentative refusée est journalisée avec une
 * empreinte courte de l'adresse saisie, pas l'adresse elle-même.
 */

import { appendFile, open, stat } from "node:fs/promises";
import { isAbsolute } from "node:path";
import { createHmac } from "node:crypto";

export type EvenementAudit =
  | "connexion_reussie"
  | "connexion_refusee"
  | "connexion_limitee"
  | "deconnexion"
  | "acces_administration"
  | "acces_administration_refuse";

export interface LigneAudit {
  horodatage: string;
  evenement: EvenementAudit;
  compte?: string;
  empreinteSaisie?: string;
  detail?: string;
}

export type Ecrivain = (ligne: LigneAudit) => Promise<void>;

export function fichierAudit(env: Record<string, string | undefined> = process.env): string | null {
  const chemin = env.MONRECOURS_AUDIT_FICHIER?.trim();
  return chemin && isAbsolute(chemin) ? chemin : null;
}

/** Empreinte courte et stable d'une adresse saisie (pour corréler sans la conserver). */
export function empreinteSaisie(email: string, secret: string): string {
  return createHmac("sha256", secret).update(`audit:${email}`).digest("base64url").slice(0, 12);
}

export function creerEcrivain(env: Record<string, string | undefined> = process.env): Ecrivain {
  const chemin = fichierAudit(env);
  return async (ligne) => {
    console.warn(JSON.stringify({ journal: "audit", ...ligne }));
    if (!chemin) return;
    try {
      await appendFile(chemin, `${JSON.stringify(ligne)}\n`, { encoding: "utf8", mode: 0o600 });
    } catch {
      console.warn(JSON.stringify({ journal: "audit", evenement: "ecriture_impossible" }));
    }
  };
}

const LECTURE_MAX_OCTETS = 64 * 1024;

/** Dernières lignes du fichier d'audit, la plus récente d'abord ; `null` si aucun fichier n'est configuré. */
export async function lireAudit(
  nombre = 50,
  env: Record<string, string | undefined> = process.env,
): Promise<LigneAudit[] | null> {
  const chemin = fichierAudit(env);
  if (!chemin) return null;
  let taille: number;
  try {
    taille = (await stat(chemin)).size;
  } catch {
    return [];
  }
  const debut = Math.max(0, taille - LECTURE_MAX_OCTETS);
  const fichier = await open(chemin, "r");
  try {
    const tampon = Buffer.alloc(taille - debut);
    await fichier.read(tampon, 0, tampon.length, debut);
    const lignes = tampon.toString("utf8").split("\n");
    if (debut > 0) lignes.shift(); // première ligne probablement tronquée
    const lues: LigneAudit[] = [];
    for (const l of lignes) {
      if (!l.trim()) continue;
      try {
        const o = JSON.parse(l) as Record<string, unknown>;
        if (typeof o.horodatage === "string" && typeof o.evenement === "string") {
          lues.push({
            horodatage: o.horodatage,
            evenement: o.evenement as EvenementAudit,
            ...(typeof o.compte === "string" ? { compte: o.compte } : {}),
            ...(typeof o.empreinteSaisie === "string" ? { empreinteSaisie: o.empreinteSaisie } : {}),
            ...(typeof o.detail === "string" ? { detail: o.detail } : {}),
          });
        }
      } catch {
        // ligne illisible : ignorée
      }
    }
    return lues.slice(-nombre).reverse();
  } finally {
    await fichier.close();
  }
}
