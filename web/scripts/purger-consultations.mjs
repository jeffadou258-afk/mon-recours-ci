#!/usr/bin/env node
/**
 * Purge des consultations web anciennes (DOSSIERS/web-*), à lancer par
 * l'exploitant — jamais automatiquement par le moteur.
 *
 * POLITIQUE DE CONSERVATION (hypothèse de conception : 90 jours)
 *   Durée de conservation : N jours, à valider juridiquement avant usage réel.
 *   Date de départ du délai : date de DERNIÈRE MODIFICATION du dossier
 *     (`mtime`). C'est la date la plus récente observable sans métadonnée
 *     supplémentaire ; elle ne peut donc que conserver plus longtemps, jamais
 *     moins. Un dossier est éligible quand son mtime date de PLUS de N jours.
 *   Périmètre : uniquement les dossiers `web-<uuid v4>` créés par l'interface.
 *     Les dossiers créés autrement (tests, démonstrations, CLI) ne sont jamais
 *     touchés.
 *   Mode par défaut : simulation. Toute suppression exige `--confirmer`.
 *
 * SAUVEGARDES — À LIRE
 *   Supprimer un dossier de l'espace actif ne supprime PAS ses copies de
 *   sauvegarde. Une archive chiffrée peut donc encore contenir un récit purgé.
 *   La durée de vie des sauvegardes doit être décidée séparément (voir
 *   docs/SAUVEGARDE_RESTAURATION.md) ; ce script le rappelle à chaque exécution
 *   réelle et ne touche jamais aux archives.
 *
 *   node scripts/purger-consultations.mjs --jours 90              # simulation
 *   node scripts/purger-consultations.mjs --jours 90 --confirmer  # suppression
 *
 * Variables : MONRECOURS_DOSSIERS (défaut : ../DOSSIERS),
 *             MONRECOURS_JOURNAL_PURGE (défaut : ../KNOWLEDGE/qualite/purge.jsonl).
 */

import { appendFileSync, existsSync, lstatSync, readdirSync, realpathSync, rmSync, statSync } from "node:fs";
import { dirname, join, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const MOTIF = /^web-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const ICI = dirname(fileURLToPath(import.meta.url));

function argument(nom, defaut) {
  const i = process.argv.indexOf(nom);
  return i >= 0 ? process.argv[i + 1] : defaut;
}

const jours = Number(argument("--jours", ""));
const confirmer = process.argv.includes("--confirmer");
const racine = resolve(process.env.MONRECOURS_DOSSIERS ?? join(ICI, "..", "..", "DOSSIERS"));
const journal = resolve(process.env.MONRECOURS_JOURNAL_PURGE ?? join(ICI, "..", "..", "KNOWLEDGE", "qualite", "purge.jsonl"));

if (!Number.isFinite(jours) || jours < 1) {
  console.error("Indiquez une durée de conservation : --jours N (N >= 1).");
  process.exit(2);
}
if (!existsSync(racine)) {
  console.log(`Aucun dossier de consultations (${racine}).`);
  process.exit(0);
}

const racineReelle = realpathSync(racine);
const limite = Date.now() - jours * 24 * 3600 * 1000;
const debut = Date.now();

let eligibles = 0;
let conserves = 0;
let supprimes = 0;
let echecs = 0;

for (const nom of readdirSync(racineReelle)) {
  if (!MOTIF.test(nom)) continue;
  const chemin = join(racineReelle, nom);

  // Confinement : jamais hors de la racine, jamais un lien symbolique.
  let reel;
  try {
    if (lstatSync(chemin).isSymbolicLink()) {
      console.error(`Ignoré (lien symbolique) : ${nom}`);
      continue;
    }
    reel = realpathSync(chemin);
  } catch (erreur) {
    console.error(`Ignoré (illisible) : ${nom}`);
    echecs += 1;
    continue;
  }
  if (!reel.startsWith(racineReelle + sep)) {
    console.error(`Ignoré (hors périmètre) : ${nom}`);
    continue;
  }

  let infos;
  try {
    infos = statSync(reel);
  } catch {
    console.error(`Ignoré (stat impossible) : ${nom}`);
    echecs += 1;
    continue;
  }
  if (!infos.isDirectory()) continue;

  if (infos.mtimeMs >= limite) {
    conserves += 1;
    continue;
  }

  eligibles += 1;
  if (!confirmer) continue;
  try {
    rmSync(reel, { recursive: true, force: false });
    supprimes += 1;
  } catch (erreur) {
    echecs += 1;
    console.error(`Échec de suppression (${nom}) : ${erreur.code ?? "erreur"}`);
  }
}

const verbe = confirmer ? "supprimée(s)" : "à supprimer (simulation, ajouter --confirmer)";
console.log(
  `${eligibles} consultation(s) web de plus de ${jours} jour(s) ${verbe} ; ` +
  `${conserves} conservée(s)${echecs ? ` ; ${echecs} échec(s)` : ""}.`
);
if (confirmer && supprimes > 0) {
  console.log(
    "Rappel : les copies de sauvegarde ne sont pas purgées par ce script. " +
    "Vérifier leur durée de vie (docs/SAUVEGARDE_RESTAURATION.md)."
  );
}

// Journal minimal : aucune donnée personnelle, aucun identifiant de dossier.
try {
  appendFileSync(journal, JSON.stringify({
    horodatage: new Date().toISOString(),
    mode: confirmer ? "reelle" : "simulation",
    jours,
    eligibles,
    conserves,
    supprimes,
    echecs,
    duree_ms: Date.now() - debut,
  }) + "\n");
} catch (erreur) {
  console.error(`Journal non écrit (${erreur.code ?? "erreur"}) — la purge n'est pas annulée.`);
}

process.exit(echecs > 0 ? 1 : 0);
