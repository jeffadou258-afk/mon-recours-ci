#!/usr/bin/env node
/**
 * Crée l'entrée d'un compte pour MONRECOURS_COMPTES — à lancer sur une machine de confiance.
 *
 *   node scripts/creer-compte.mjs <adresse e-mail> [administrateur|lecteur]
 *
 * Le mot de passe est demandé deux fois, sans écho à l'écran (ou lu sur l'entrée
 * standard s'il n'y a pas de terminal). Il n'est jamais affiché, jamais écrit
 * sur disque : seule son EMPREINTE scrypt est imprimée, sous forme d'une entrée
 * JSON à ajouter au tableau de la variable MONRECOURS_COMPTES.
 *
 * Mêmes paramètres que src/lib/server/auth/motdepasse.ts (vérifié par les tests).
 */

import { randomBytes, scrypt } from "node:crypto";

export const PARAMETRES = { N: 16384, r: 8, p: 1, longueurCle: 32, longueurSel: 16 };
export const LONGUEUR_MIN = 12;
const ROLES = ["administrateur", "lecteur"];

export function hacher(motDePasse) {
  const { N, r, p, longueurCle, longueurSel } = PARAMETRES;
  const sel = randomBytes(longueurSel);
  return new Promise((resoudre, rejeter) => {
    scrypt(motDePasse.normalize("NFC"), sel, longueurCle, { N, r, p, maxmem: 256 * N * r * p }, (err, cle) => {
      if (err) return rejeter(err);
      resoudre(`scrypt$${N}$${r}$${p}$${sel.toString("base64url")}$${cle.toString("base64url")}`);
    });
  });
}

export function controlerMotDePasse(motDePasse) {
  if (motDePasse.length < LONGUEUR_MIN) return `Le mot de passe doit contenir au moins ${LONGUEUR_MIN} caractères.`;
  if (motDePasse.length > 1024) return "Le mot de passe est trop long (1024 caractères au maximum).";
  if (new Set(motDePasse).size < 5) return "Le mot de passe est trop répétitif.";
  return null;
}

function lireMasque(question) {
  return new Promise((resoudre, rejeter) => {
    const entree = process.stdin;
    process.stderr.write(question);
    let valeur = "";
    entree.setRawMode(true);
    entree.resume();
    entree.setEncoding("utf8");
    const surDonnee = (morceau) => {
      for (const c of morceau) {
        if (c === "\r" || c === "\n" || c === "\u0004") {
          entree.setRawMode(false);
          entree.pause();
          entree.removeListener("data", surDonnee);
          process.stderr.write("\n");
          return resoudre(valeur);
        }
        if (c === "\u0003") {
          entree.setRawMode(false);
          process.stderr.write("\n");
          return rejeter(new Error("annulé"));
        }
        if (c === "\u007f" || c === "\b") valeur = valeur.slice(0, -1);
        else valeur += c;
      }
    };
    entree.on("data", surDonnee);
  });
}

async function lireEntreeStandard() {
  let texte = "";
  for await (const morceau of process.stdin) texte += morceau;
  return texte.replace(/\r?\n$/, "");
}

async function principal() {
  const [emailBrut, role = "administrateur"] = process.argv.slice(2);
  const email = (emailBrut ?? "").trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || !ROLES.includes(role)) {
    console.error("Usage : node scripts/creer-compte.mjs <adresse e-mail> [administrateur|lecteur]");
    process.exit(2);
  }

  let motDePasse;
  if (process.stdin.isTTY) {
    motDePasse = await lireMasque("Mot de passe : ");
    const confirmation = await lireMasque("Confirmez le mot de passe : ");
    if (motDePasse !== confirmation) {
      console.error("Les deux saisies ne correspondent pas. Aucun compte créé.");
      process.exit(1);
    }
  } else {
    motDePasse = await lireEntreeStandard();
  }
  const probleme = controlerMotDePasse(motDePasse);
  if (probleme) {
    console.error(`${probleme} Aucun compte créé.`);
    process.exit(1);
  }

  const entree = { email, role, motDePasse: await hacher(motDePasse) };
  console.error("Entrée à ajouter au tableau JSON de MONRECOURS_COMPTES (le mot de passe n'y figure pas) :");
  console.log(JSON.stringify(entree));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  principal().catch((e) => {
    console.error(`Erreur : ${e.message}`);
    process.exit(1);
  });
}
