#!/usr/bin/env node
/**
 * Purge des consultations web anciennes (DOSSIERS/web-*), à lancer par
 * l'exploitant — jamais automatiquement par le moteur.
 *
 * Le moteur écrit chaque demande dans DOSSIERS/<dossier_id>/ pour la
 * traçabilité. Les consultations créées par l'interface portent un identifiant
 * `web-<uuid>`. Ce script supprime UNIQUEMENT ces dossiers-là, plus vieux que
 * N jours (date de dernière modification). Les dossiers créés autrement
 * (tests, démonstrations, CLI) ne sont jamais touchés.
 *
 *   node scripts/purger-consultations.mjs --jours 30              # simulation
 *   node scripts/purger-consultations.mjs --jours 30 --confirmer  # suppression
 *
 * Variable optionnelle : MONRECOURS_DOSSIERS (défaut : ../DOSSIERS).
 */

import { existsSync, readdirSync, rmSync, statSync } from "node:fs";
import { join, resolve } from "node:path";

const MOTIF = /^web-[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;

function argument(nom, defaut) {
  const i = process.argv.indexOf(nom);
  return i >= 0 ? process.argv[i + 1] : defaut;
}

const jours = Number(argument("--jours", ""));
const confirmer = process.argv.includes("--confirmer");
const racine = resolve(process.env.MONRECOURS_DOSSIERS ?? new URL("../../DOSSIERS", import.meta.url).pathname);

if (!Number.isFinite(jours) || jours < 1) {
  console.error("Indiquez une durée de conservation : --jours N (N >= 1).");
  process.exit(2);
}
if (!existsSync(racine)) {
  console.log(`Aucun dossier de consultations (${racine}).`);
  process.exit(0);
}

const limite = Date.now() - jours * 24 * 3600 * 1000;
let candidats = 0;
let conserves = 0;
for (const nom of readdirSync(racine)) {
  if (!MOTIF.test(nom)) continue;
  const chemin = join(racine, nom);
  const infos = statSync(chemin);
  if (!infos.isDirectory()) continue;
  if (infos.mtimeMs >= limite) {
    conserves++;
    continue;
  }
  candidats++;
  if (confirmer) rmSync(chemin, { recursive: true, force: true });
}

const verbe = confirmer ? "supprimée(s)" : "à supprimer (simulation, ajouter --confirmer)";
console.log(`${candidats} consultation(s) web de plus de ${jours} jour(s) ${verbe} ; ${conserves} conservée(s).`);
