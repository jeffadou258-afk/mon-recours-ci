#!/usr/bin/env node
/**
 * Vérifie qu'aucun secret ne se trouve dans le code envoyé au navigateur.
 *
 *   npm run build && npm run verifier:secrets            # analyse .next/static
 *   node scripts/verifier-secrets.mjs apercu/dist         # autre dossier
 *
 * Cherche : les VALEURS des variables MONRECOURS_* (environnement courant et
 * .env.local / .env), leurs NOMS, et l'en-tête X-API-Key. Code de sortie 1 si
 * quelque chose est trouvé.
 */

import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join, relative } from "node:path";

const racine = new URL("..", import.meta.url).pathname;
const dossiers = process.argv.slice(2).length ? process.argv.slice(2) : [".next/static"];

function lireFichierEnv(chemin) {
  if (!existsSync(chemin)) return {};
  const valeurs = {};
  for (const ligne of readFileSync(chemin, "utf8").split(/\r?\n/)) {
    const m = /^\s*(MONRECOURS_[A-Z_]+)\s*=\s*(.*)\s*$/.exec(ligne);
    if (m) valeurs[m[1]] = m[2].replace(/^["']|["']$/g, "");
  }
  return valeurs;
}

const valeurs = {
  ...lireFichierEnv(join(racine, ".env")),
  ...lireFichierEnv(join(racine, ".env.local")),
  ...Object.fromEntries(Object.entries(process.env).filter(([k]) => k.startsWith("MONRECOURS_"))),
};

const motifs = [
  { nom: "nom de variable serveur", texte: "MONRECOURS_" },
  { nom: "en-tête d'authentification du moteur", texte: "X-API-Key" },
];
for (const [cle, valeur] of Object.entries(valeurs)) {
  // L'URL et le délai ne sont pas secrets, mais l'URL du moteur n'a rien à faire côté client non plus.
  if (valeur && valeur.length >= 8 && cle !== "MONRECOURS_API_TIMEOUT_MS") {
    motifs.push({ nom: `valeur de ${cle}`, texte: valeur });
  }
}

function* fichiers(dossier) {
  for (const nom of readdirSync(dossier)) {
    const chemin = join(dossier, nom);
    if (statSync(chemin).isDirectory()) yield* fichiers(chemin);
    else if (/\.(js|mjs|css|html|json|map|txt)$/.test(nom)) yield chemin;
  }
}

let analyses = 0;
const trouvailles = [];
for (const d of dossiers) {
  const absolu = join(racine, d);
  if (!existsSync(absolu)) {
    console.error(`Dossier introuvable : ${d} (lancez d'abord la construction).`);
    process.exit(2);
  }
  for (const f of fichiers(absolu)) {
    analyses++;
    const contenu = readFileSync(f, "utf8");
    for (const m of motifs) {
      if (contenu.includes(m.texte)) trouvailles.push(`${relative(racine, f)} : ${m.nom}`);
    }
  }
}

if (analyses === 0) {
  console.error("Aucun fichier analysé : vérification impossible.");
  process.exit(2);
}
if (trouvailles.length) {
  console.error("SECRETS DÉTECTÉS DANS LE CODE CLIENT :");
  for (const t of trouvailles) console.error(`  - ${t}`);
  process.exit(1);
}
console.log(`OK : ${analyses} fichiers clients analysés, ${motifs.length} motifs recherchés, aucun secret trouvé.`);
