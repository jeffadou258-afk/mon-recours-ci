/**
 * Accès aux courriers PDF produits par le moteur.
 *
 * POURQUOI CE MODULE EXISTE
 * -------------------------
 * Le moteur écrit `DOSSIERS/<dossier_id>/BROUILLONS/<horodatage>_reclamation.pdf`.
 * L'interface tourne sur la même machine (imposé par `bin/serveur_api.py`, qui
 * n'écoute que sur 127.0.0.1), donc elle peut lire ce fichier. Encore faut-il
 * que ce soit SÛR.
 *
 * LES QUATRE PROTECTIONS, DANS L'ORDRE
 * ------------------------------------
 * 1. **L'identifiant vient du cookie signé**, jamais d'un paramètre d'URL ni du
 *    corps de la requête. `deballer()` vérifie une signature HMAC en temps
 *    constant : on ne peut pas demander le dossier d'un autre.
 * 2. **Le format de l'identifiant est verrouillé** (`MOTIF_ID` : `web-<uuid v4>`).
 *    Aucun `/`, aucun `.`, donc aucune traversée possible par construction.
 * 3. **Le nom du fichier n'est pas choisi par l'utilisateur** : on liste le
 *    dossier et on ne retient que `^\d{8}-\d{6}_reclamation\.pdf$`, motif produit
 *    par `core/documents.py`. Aucune entrée arbitraire n'est lue.
 * 4. **Confinement vérifié** : le chemin réel du fichier doit avoir pour parent
 *    réel le dossier BROUILLONS attendu. Une lien symbolique sortant du dossier
 *    est donc refusée.
 *
 * Ce module ne liste jamais un dossier à l'utilisateur et ne renvoie jamais un
 * chemin : il renvoie des octets, sous un nom fixé par nous.
 */

import { readFile, readdir, realpath, stat } from "node:fs/promises";
import { dirname, join, resolve } from "node:path";

const MOTIF_COURRIER = /^\d{8}-\d{6}_reclamation\.pdf$/;

export class CourrierIntrouvable extends Error {}

/** La durée de conservation de la consultation est écoulée : plus rien n'est servi. */
export class ConsultationExpiree extends Error {}

const HEURE_MS = 3600 * 1000;

/** Durée de conservation en heures (MONRECOURS_CONSERVATION_HEURES, 24 par défaut). */
export function dureeConservationHeures(env: Record<string, string | undefined> = process.env): number {
  const brut = env.MONRECOURS_CONSERVATION_HEURES ?? "";
  if (brut === "") return 24;
  const valeur = Number(brut);
  if (!Number.isInteger(valeur) || valeur < 1) throw new Error("MONRECOURS_CONSERVATION_HEURES invalide");
  return valeur;
}

/**
 * Échéance d'une consultation, même règle que le moteur (core/conservation.py) :
 * `CONSERVATION.json` ; à défaut `ouvert_le` + durée ; à défaut date de
 * modification + durée. `null` si le dossier n'existe pas.
 */
export async function echeanceConsultation(dossierId: string, heures = dureeConservationHeures()): Promise<number | null> {
  const dossier = join(racineDossiers(), dossierId);
  let infos;
  try {
    infos = await stat(dossier);
  } catch {
    return null;
  }
  if (!infos.isDirectory()) return null;
  try {
    const t = Date.parse(JSON.parse(await readFile(join(dossier, "CONSERVATION.json"), "utf8")).expire_le);
    if (Number.isFinite(t)) return t;
  } catch {
    /* repli */
  }
  try {
    const brut = String(JSON.parse(await readFile(join(dossier, "DOSSIER_EN_COURS.json"), "utf8")).ouvert_le ?? "");
    const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(brut) ? brut : `${brut}Z`);
    if (Number.isFinite(t)) return t + heures * HEURE_MS;
  } catch {
    /* repli */
  }
  return infos.mtimeMs + heures * HEURE_MS;
}

export function racineDossiers(): string {
  return resolve(process.env.MONRECOURS_DOSSIERS ?? join(process.cwd(), "..", "DOSSIERS"));
}

export interface CourrierPdf {
  chemin: string;
  octets: number;
  /** Nom proposé au téléchargement — fixé par nous, jamais dérivé d'une saisie. */
  nom: string;
}

/** Dernier courrier PDF du dossier, confiné à `DOSSIERS/<id>/BROUILLONS`. */
export async function dernierCourrierPdf(dossierId: string): Promise<CourrierPdf> {
  // Ceinture et bretelles : même si un appelant oubliait la validation du cookie.
  if (!/^web-[0-9a-f-]{36}$/.test(dossierId)) {
    throw new CourrierIntrouvable("identifiant de dossier refusé");
  }
  const echeance = await echeanceConsultation(dossierId);
  if (echeance !== null && Date.now() >= echeance) throw new ConsultationExpiree("consultation expirée");
  const dossier = join(racineDossiers(), dossierId, "BROUILLONS");
  let noms: string[];
  try {
    noms = await readdir(dossier);
  } catch {
    throw new CourrierIntrouvable("aucun courrier pour ce dossier");
  }

  const candidats = noms.filter((nom) => MOTIF_COURRIER.test(nom)).sort();
  if (candidats.length === 0) throw new CourrierIntrouvable("aucun courrier pour ce dossier");
  const retenu = candidats[candidats.length - 1]!;

  const chemin = join(dossier, retenu);
  let reel: string;
  let attendu: string;
  try {
    [reel, attendu] = await Promise.all([realpath(chemin), realpath(dossier)]);
  } catch {
    throw new CourrierIntrouvable("aucun courrier pour ce dossier");
  }
  if (dirname(reel) !== attendu) throw new CourrierIntrouvable("courrier hors du dossier");

  const infos = await stat(reel);
  if (!infos.isFile() || infos.size <= 0) throw new CourrierIntrouvable("courrier illisible");

  return { chemin: reel, octets: infos.size, nom: "courrier-mon-recours-ci.pdf" };
}
