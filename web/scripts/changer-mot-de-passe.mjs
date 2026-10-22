#!/usr/bin/env node
/**
 * Change le mot de passe d'un compte existant de MONRECOURS_COMPTES.
 *
 *   node scripts/changer-mot-de-passe.mjs --fichier /etc/mon-recours-ci/comptes.json \
 *        --email admin@exemple.ci --generer --sortie /root/nouveau-motdepasse.txt
 *
 *   node scripts/changer-mot-de-passe.mjs --fichier ... --email ... --mot-de-passe-fichier /chemin
 *
 * Le mot de passe n'est JAMAIS affiché ni journalisé : soit il est généré et
 * écrit dans un fichier en 600 (--sortie), soit il est lu depuis un fichier
 * (--mot-de-passe-fichier). Seule son empreinte scrypt entre dans le fichier de
 * comptes, avec les mêmes paramètres que le service (vérifiés par les tests).
 *
 * Un changement de mot de passe invalide les sessions existantes : le jeton
 * contient l'empreinte, donc l'ancien cookie ne vaut plus rien.
 */

import { randomInt } from "node:crypto";
import { chmodSync, existsSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs";
import { hacher, controlerMotDePasse } from "./creer-compte.mjs";

const ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789-_";

function generer(longueur = 24) {
  let sortie = "";
  for (let i = 0; i < longueur; i += 1) sortie += ALPHABET[randomInt(ALPHABET.length)];
  return sortie;
}

function argument(nom) {
  const index = process.argv.indexOf(nom);
  if (index < 0) return null;
  const valeur = process.argv[index + 1];
  if (!valeur || valeur.startsWith("--")) throw new Error(`${nom} attend une valeur`);
  return valeur;
}

function ecrirePrive(chemin, contenu) {
  writeFileSync(chemin, contenu, { mode: 0o600 });
  chmodSync(chemin, 0o600);
}

async function principal() {
  const fichier = argument("--fichier");
  const email = (argument("--email") ?? "").trim().toLowerCase();
  const source = argument("--mot-de-passe-fichier");
  const sortie = argument("--sortie");
  const genererIci = process.argv.includes("--generer");

  if (!fichier || !email) {
    console.error("Usage : --fichier <comptes.json> --email <adresse> (--generer --sortie <chemin> | --mot-de-passe-fichier <chemin>)");
    process.exit(2);
  }
  if (!existsSync(fichier)) {
    console.error(`Fichier introuvable : ${fichier}`);
    process.exit(2);
  }
  const mode = statSync(fichier).mode & 0o777;
  if (mode & 0o077) {
    console.error(`Le fichier ${fichier} est accessible au-delà du propriétaire (${mode.toString(8)}). Aucune modification.`);
    process.exit(3);
  }

  let comptes;
  try {
    comptes = JSON.parse(readFileSync(fichier, "utf8"));
  } catch {
    console.error("Le fichier de comptes n'est pas un JSON valide. Aucune modification.");
    process.exit(3);
  }
  if (!Array.isArray(comptes)) {
    console.error("Le fichier de comptes ne contient pas un tableau. Aucune modification.");
    process.exit(3);
  }
  const index = comptes.findIndex(
    (c) => typeof c?.email === "string" && c.email.trim().toLowerCase() === email,
  );
  if (index < 0) {
    console.error(`Aucun compte ${email}. Aucune modification.`);
    process.exit(4);
  }

  let motDePasse;
  if (genererIci) {
    if (!sortie) {
      console.error("--generer exige --sortie pour ne pas afficher le mot de passe.");
      process.exit(2);
    }
    motDePasse = generer(24);
  } else if (source) {
    motDePasse = readFileSync(source, "utf8").replace(/\r?\n$/, "");
  } else {
    console.error("Aucune source de mot de passe : --generer ou --mot-de-passe-fichier.");
    process.exit(2);
  }

  const probleme = controlerMotDePasse(motDePasse);
  if (probleme) {
    console.error(probleme);
    process.exit(5);
  }

  const empreinte = await hacher(motDePasse);
  const avant = comptes[index];
  comptes[index] = { ...avant, motDePasse: empreinte };

  const provisoire = `${fichier}.${process.pid}.tmp`;
  writeFileSync(provisoire, JSON.stringify(comptes, null, 1) + "\n", { mode: 0o600 });
  chmodSync(provisoire, 0o600);
  renameSync(provisoire, fichier);
  chmodSync(fichier, 0o600);

  if (genererIci) ecrirePrive(sortie, motDePasse + "\n");

  console.log(`Mot de passe changé pour ${email} (rôle : ${avant.role}).`);
  if (genererIci) {
    console.log(`Nouveau mot de passe écrit dans ${sortie} (600). Lisez-le, puis supprimez le fichier.`);
  }
  console.log("Les sessions ouvertes avec l'ancien mot de passe ne sont plus valides.");
}

principal().catch((erreur) => {
  console.error(`Échec : ${erreur.message}`);
  process.exit(1);
});
