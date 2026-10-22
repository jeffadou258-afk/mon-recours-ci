#!/usr/bin/env node
/**
 * Crée l'entrée d'un compte pour MONRECOURS_COMPTES — à lancer sur une machine de confiance.
 *
 *   node scripts/creer-compte.mjs <adresse e-mail> [administrateur|lecteur]
 *   node scripts/creer-compte.mjs <adresse e-mail> [role] --fichier /etc/mon-recours-ci/comptes.json
 *
 * Le mot de passe est demandé deux fois, sans écho à l'écran (ou lu sur l'entrée
 * standard s'il n'y a pas de terminal). Il n'est jamais affiché, jamais écrit
 * sur disque : seule son EMPREINTE scrypt est imprimée ou enregistrée.
 *
 * `--fichier` ajoute l'entrée au fichier JSON utilisé par
 * `MONRECOURS_COMPTES_FICHIER` : lecture, refus des doublons, écriture atomique
 * en 600. Sans cette option, l'entrée est simplement imprimée sur la sortie
 * standard, à coller soi-même dans la variable.
 *
 * Mêmes paramètres que src/lib/server/auth/motdepasse.ts (vérifié par les tests).
 */

import { randomBytes, scrypt } from "node:crypto";
import { chmodSync, existsSync, readFileSync, renameSync, statSync, writeFileSync } from "node:fs";

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

/**
 * Ajoute l'entrée au fichier JSON de comptes, en refusant tout ce qui pourrait
 * affaiblir la sécurité : fichier lisible par d'autres, doublon d'adresse,
 * contenu qui n'est pas un tableau.
 */
export function ajouterAuFichier(chemin, entree) {
  let comptes = [];
  if (existsSync(chemin)) {
    const mode = statSync(chemin).mode & 0o777;
    if (mode & 0o077) {
      throw new Error(
        `le fichier ${chemin} est accessible au-delà du propriétaire (${mode.toString(8)}) : corrigez-le en 600 avant d'y écrire`,
      );
    }
    let contenu;
    try {
      contenu = JSON.parse(readFileSync(chemin, "utf8"));
    } catch {
      throw new Error(`le fichier ${chemin} n'est pas un JSON valide`);
    }
    if (!Array.isArray(contenu)) throw new Error(`le fichier ${chemin} ne contient pas un tableau`);
    comptes = contenu;
  }
  const deja = comptes.some(
    (c) => typeof c?.email === "string" && c.email.trim().toLowerCase() === entree.email,
  );
  if (deja) throw new Error(`${entree.email} existe déjà dans ${chemin} : rien n'a été modifié`);

  comptes.push(entree);
  const provisoire = `${chemin}.${process.pid}.tmp`;
  writeFileSync(provisoire, JSON.stringify(comptes, null, 1) + "\n", { mode: 0o600 });
  chmodSync(provisoire, 0o600);
  renameSync(provisoire, chemin);
  chmodSync(chemin, 0o600);
  return comptes.length;
}

async function principal() {
  // Options : `--fichier <chemin>` écrit l'entrée au lieu de l'imprimer.
  const brut = process.argv.slice(2);
  const iFichier = brut.indexOf("--fichier");
  const cheminFichier = iFichier >= 0 ? brut[iFichier + 1] : null;
  if (iFichier >= 0 && !cheminFichier) {
    console.error("--fichier attend un chemin. Aucun compte créé.");
    process.exit(2);
  }
  const positionnels = brut.filter((a, i) => i !== iFichier && i !== iFichier + 1);
  const [emailBrut, role = "administrateur"] = positionnels;
  const email = (emailBrut ?? "").trim().toLowerCase();
  if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email) || !ROLES.includes(role)) {
    console.error("Usage : node scripts/creer-compte.mjs <adresse e-mail> [administrateur|lecteur] [--fichier <chemin>]");
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
  if (cheminFichier) {
    const total = ajouterAuFichier(cheminFichier, entree);
    console.error(`Compte ${email} (${role}) enregistré dans ${cheminFichier} — ${total} compte(s), fichier en 600.`);
    console.error("Le mot de passe n'a pas été conservé. Pointez MONRECOURS_COMPTES_FICHIER sur ce fichier.");
    return;
  }
  console.error("Entrée à ajouter au tableau JSON de MONRECOURS_COMPTES (le mot de passe n'y figure pas) :");
  console.log(JSON.stringify(entree));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  principal().catch((e) => {
    console.error(`Erreur : ${e.message}`);
    process.exit(1);
  });
}
