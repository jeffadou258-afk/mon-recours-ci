#!/usr/bin/env node
/**
 * Purge des consultations web expirées (DOSSIERS/web-*), lancée côté serveur
 * par un minuteur systemd — jamais par le navigateur, jamais par le moteur.
 *
 * POLITIQUE DE CONSERVATION (décision produit du 22/10/2026 : 24 heures)
 *   Une consultation expire à `expire_le`, inscrit UNE FOIS à sa création dans
 *   `DOSSIERS/<id>/CONSERVATION.json` (core/conservation.py). Pour un dossier
 *   créé avant ce fichier, l'échéance vaut `ouvert_le` (DOSSIER_EN_COURS.json)
 *   + N heures, et en dernier recours la date de DERNIÈRE MODIFICATION du
 *   répertoire + N heures. Chaque repli ne peut que retarder l'échéance.
 *   Un dossier est éligible quand l'échéance est atteinte (échéance comprise).
 *
 *   Périmètre : uniquement les dossiers `web-<uuid v4>` créés par l'interface,
 *   et les restes `.purge-web-<uuid v4>` d'une suppression interrompue. Les
 *   autres (corpus, tests, démonstrations, CLI) ne sont jamais touchés : le
 *   script ne lit que la racine des consultations.
 *
 *   Suppression en deux temps : le dossier est d'abord RENOMMÉ en
 *   `.purge-web-…` (il devient aussitôt introuvable par son identifiant, donc
 *   inaccessible), puis effacé. Si l'effacement échoue, le reste est repris au
 *   passage suivant. Le script est idempotent : le relancer ne fait rien de plus.
 *
 *   Mode par défaut : simulation. Toute suppression exige `--confirmer`.
 *
 * SAUVEGARDES — À LIRE
 *   Ce script ne touche jamais aux archives. Avec la politique de 24 heures, les
 *   consultations sont EXCLUES des sauvegardes (voir
 *   docs/CONSERVATION_24H.md) ; une archive ancienne peut encore en contenir.
 *
 *   node scripts/purger-consultations.mjs --heures 24              # simulation
 *   node scripts/purger-consultations.mjs --heures 24 --confirmer  # suppression
 *   (--jours N reste accepté : N jours = 24 × N heures)
 *
 * Variables : MONRECOURS_DOSSIERS (défaut : ../DOSSIERS),
 *             MONRECOURS_JOURNAL_PURGE (défaut : ../KNOWLEDGE/qualite/purge.jsonl).
 */

import { appendFileSync, existsSync, lstatSync, readFileSync, readdirSync, realpathSync, renameSync, rmSync, statSync } from "node:fs";
import { randomBytes } from "node:crypto";
import { dirname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const UUID = "[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}";
const MOTIF = new RegExp(`^web-${UUID}$`);
const MOTIF_RESTE = new RegExp(`^\\.purge-web-${UUID}(-[0-9a-f]{8})?$`);
const ICI = dirname(fileURLToPath(import.meta.url));
const HEURE_MS = 3600 * 1000;

function argument(nom) {
  const i = process.argv.indexOf(nom);
  return i >= 0 ? (process.argv[i + 1] ?? "") : undefined;
}

const brutHeures = argument("--heures");
const brutJours = argument("--jours");
const heures = brutHeures !== undefined ? Number(brutHeures) : brutJours !== undefined ? Number(brutJours) * 24 : NaN;
const confirmer = process.argv.includes("--confirmer");
const racine = resolve(process.env.MONRECOURS_DOSSIERS ?? join(ICI, "..", "..", "DOSSIERS"));
const journal = resolve(process.env.MONRECOURS_JOURNAL_PURGE ?? join(ICI, "..", "..", "KNOWLEDGE", "qualite", "purge.jsonl"));

if (!Number.isInteger(heures) || heures < 1 || (brutHeures !== undefined && brutJours !== undefined)) {
  console.error("Indiquez UNE durée de conservation : --heures N (N >= 1, entier) ou --jours N.");
  process.exit(2);
}
if (!existsSync(racine)) {
  console.log(`Aucun dossier de consultations (${racine}).`);
  process.exit(0);
}

const racineReelle = realpathSync(racine);
const maintenant = Date.now();
const debut = maintenant;

/** Échéance d'un dossier, en ms, et son origine. Ne lit jamais le récit au-delà de `ouvert_le`. */
function echeance(chemin, infos) {
  try {
    const meta = JSON.parse(readFileSync(join(chemin, "CONSERVATION.json"), "utf8"));
    const t = Date.parse(meta.expire_le);
    if (Number.isFinite(t)) return { t, source: "conservation" };
  } catch {
    /* repli */
  }
  try {
    const enCours = JSON.parse(readFileSync(join(chemin, "DOSSIER_EN_COURS.json"), "utf8"));
    const brut = String(enCours.ouvert_le ?? "");
    const t = Date.parse(/[zZ]|[+-]\d\d:?\d\d$/.test(brut) ? brut : `${brut}Z`);
    if (Number.isFinite(t)) return { t: t + heures * HEURE_MS, source: "ouvert_le" };
  } catch {
    /* repli */
  }
  return { t: infos.mtimeMs + heures * HEURE_MS, source: "mtime" };
}

/** Confinement : jamais hors de la racine, jamais un lien symbolique. */
function confiner(nom) {
  const chemin = join(racineReelle, nom);
  const l = lstatSync(chemin);
  if (l.isSymbolicLink()) return { motif: "lien symbolique" };
  const reel = realpathSync(chemin);
  if (dirname(reel) !== racineReelle || !reel.startsWith(racineReelle + sep)) return { motif: "hors périmètre" };
  const infos = statSync(reel);
  if (!infos.isDirectory()) return { motif: "pas un répertoire" };
  return { reel, infos };
}

const compte = { eligibles: 0, conserves: 0, supprimes: 0, restes_repris: 0, echecs: 0 };
const sources = { conservation: 0, ouvert_le: 0, mtime: 0 };

for (const nom of readdirSync(racineReelle)) {
  const reste = MOTIF_RESTE.test(nom);
  if (!MOTIF.test(nom) && !reste) continue;

  let cible;
  try {
    cible = confiner(nom);
  } catch {
    console.error(`Ignoré (illisible) : ${nom}`);
    compte.echecs += 1;
    continue;
  }
  if (!cible.reel) {
    console.error(`Ignoré (${cible.motif}) : ${nom}`);
    continue;
  }

  if (reste) {
    // Suppression interrompue lors d'un passage précédent : déjà inaccessible.
    compte.eligibles += 1;
    if (!confirmer) continue;
    try {
      rmSync(cible.reel, { recursive: true, force: false });
      compte.restes_repris += 1;
    } catch (erreur) {
      compte.echecs += 1;
      console.error(`Échec de suppression d'un reste : ${erreur.code ?? "erreur"}`);
    }
    continue;
  }

  const { t, source } = echeance(cible.reel, cible.infos);
  if (maintenant < t) {
    compte.conserves += 1;
    continue;
  }
  compte.eligibles += 1;
  sources[source] += 1;
  if (!confirmer) continue;

  // 1. Retrait immédiat : le dossier n'est plus joignable par son identifiant.
  const retire = join(racineReelle, `.purge-${nom}-${randomBytes(4).toString("hex")}`);
  try {
    renameSync(cible.reel, retire);
  } catch (erreur) {
    compte.echecs += 1;
    console.error(`Échec du retrait d'une consultation expirée : ${erreur.code ?? "erreur"}`);
    continue;
  }
  // 2. Effacement. Un échec laisse un reste `.purge-…` repris au passage suivant.
  try {
    rmSync(retire, { recursive: true, force: false });
    compte.supprimes += 1;
  } catch (erreur) {
    compte.echecs += 1;
    console.error(`Effacement incomplet (repris au prochain passage) : ${erreur.code ?? "erreur"}`);
  }
}

const verbe = confirmer ? "supprimée(s)" : "à supprimer (simulation, ajouter --confirmer)";
console.log(
  `${compte.eligibles} consultation(s) web expirée(s) (conservation : ${heures} h) ${verbe} ; ` +
    `${compte.conserves} conservée(s)${compte.echecs ? ` ; ${compte.echecs} échec(s)` : ""}.`,
);

// Journal minimal : compteurs seulement — aucun identifiant, aucun contenu.
try {
  appendFileSync(
    journal,
    JSON.stringify({
      horodatage: new Date().toISOString(),
      mode: confirmer ? "reelle" : "simulation",
      heures,
      ...compte,
      sources,
      duree_ms: Date.now() - debut,
    }) + "\n",
    { mode: 0o600 },
  );
} catch (erreur) {
  console.error(`Journal non écrit (${erreur.code ?? "erreur"}) — la purge n'est pas annulée.`);
}

process.exit(compte.echecs > 0 ? 1 : 0);
