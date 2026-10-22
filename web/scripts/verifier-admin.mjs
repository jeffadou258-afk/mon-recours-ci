#!/usr/bin/env node
/**
 * Vérifie le parcours d'administration de bout en bout, sans moteur et sans donnée réelle.
 *
 *   npm run verifier:admin
 *
 * Ce que ce script prouve (et non ce qu'il suppose) :
 *   1. `/admin` sans cookie renvoie vers la connexion                  (307)
 *   2. un mauvais mot de passe est refusé                              (401)
 *   3. un compte inconnu donne exactement la même réponse              (401, pas d'énumération)
 *   4. une connexion valide pose un cookie HttpOnly + SameSite=Strict  (200)
 *   5. `/admin` avec ce cookie affiche le tableau de bord              (200)
 *   6. un cookie falsifié est refusé                                   (307)
 *   7. la déconnexion efface le cookie et referme l'accès              (200 puis 307)
 *   8. le journal d'audit reçoit les événements, sans mot de passe     (fichier)
 *   9. les tentatives sont limitées par adresse                        (429)
 *
 * Il démarre sa propre instance sur un port libre, avec un compte JETABLE tiré au
 * hasard, un répertoire temporaire, et un moteur volontairement injoignable
 * (127.0.0.1:9) pour rester hermétique. Rien n'est écrit dans le dépôt.
 */

import { spawn } from "node:child_process";
import { randomInt } from "node:crypto";
import { chmodSync, existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { hacher } from "./creer-compte.mjs";

const ALPHABET = "abcdefghijkmnpqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789";
const EMAIL = "verification@mon-recours.test";
const PORT = 3200 + randomInt(300);
const BASE = `http://127.0.0.1:${PORT}`;

const resultats = [];
function verifier(nom, condition, detail = "") {
  resultats.push({ nom, ok: Boolean(condition), detail });
  console.log(`${condition ? "  OK   " : "  ECHEC"} ${nom}${detail ? " — " + detail : ""}`);
}

function motDePasseAleatoire(longueur = 18) {
  return Array.from({ length: longueur }, () => ALPHABET[randomInt(ALPHABET.length)]).join("");
}

function cookieDepuis(reponse, nom) {
  const brut = reponse.headers.getSetCookie?.() ?? [];
  for (const ligne of brut) {
    if (ligne.startsWith(nom + "=")) return ligne.split(";")[0];
  }
  return null;
}

async function attendreServeur(delaiMs = 60000) {
  const fin = Date.now() + delaiMs;
  while (Date.now() < fin) {
    try {
      const r = await fetch(`${BASE}/`, { redirect: "manual" });
      if (r.status < 500) return true;
    } catch {
      /* pas encore prêt */
    }
    await new Promise((r) => setTimeout(r, 400));
  }
  return false;
}

const dossier = mkdtempSync(join(tmpdir(), "verif-admin-"));
const cheminComptes = join(dossier, "comptes.json");
const cheminAudit = join(dossier, "audit.jsonl");
const motDePasse = motDePasseAleatoire();

writeFileSync(cheminComptes, JSON.stringify([{ email: EMAIL, role: "administrateur", motDePasse: await hacher(motDePasse) }]) + "\n");
chmodSync(cheminComptes, 0o600);
writeFileSync(cheminAudit, "");
chmodSync(cheminAudit, 0o600);

const serveur = spawn("node_modules/.bin/next", ["start", "-p", String(PORT)], {
  cwd: process.cwd(),
  env: {
    ...process.env,
    NODE_ENV: "production",
    PORT: String(PORT),
    MONRECOURS_SESSION_SECRET: "0".repeat(64),
    MONRECOURS_API_KEY: "cle-de-verification-0000000000",
    MONRECOURS_API_URL: "http://127.0.0.1:9", // moteur absent : le tableau de bord doit rester lisible
    MONRECOURS_COMPTES_FICHIER: cheminComptes,
    MONRECOURS_AUDIT_FICHIER: cheminAudit,
  },
  stdio: ["ignore", "pipe", "pipe"],
});
let journalServeur = "";
serveur.stdout.on("data", (d) => (journalServeur += d));
serveur.stderr.on("data", (d) => (journalServeur += d));

function arreter() {
  try {
    serveur.kill("SIGTERM");
  } catch {
    /* déjà arrêté */
  }
  rmSync(dossier, { recursive: true, force: true });
}

try {
  if (!(await attendreServeur())) {
    console.error("Le serveur n'a pas démarré. Journal :\n" + journalServeur.slice(-1500));
    arreter();
    process.exit(1);
  }

  // 1. /admin sans cookie
  const anonyme = await fetch(`${BASE}/admin`, { redirect: "manual" });
  const lieu = anonyme.headers.get("location") ?? "";
  verifier("/admin sans cookie renvoie vers la connexion", anonyme.status === 307 && lieu.includes("/connexion"), `${anonyme.status} -> ${lieu}`);

  const poster = (chemin, corps, entetes = {}) =>
    fetch(`${BASE}${chemin}`, {
      method: "POST",
      headers: { "content-type": "application/json", "x-forwarded-for": "198.51.100.10", ...entetes },
      body: JSON.stringify(corps),
      redirect: "manual",
    });

  // 2. mauvais mot de passe
  const mauvais = await poster("/api/connexion", { email: EMAIL, motDePasse: "mauvais-mot-de-passe-000" });
  verifier("mauvais mot de passe refusé", mauvais.status === 401, String(mauvais.status));
  const corpsMauvais = await mauvais.text();

  // 3. compte inconnu : même réponse
  const inconnu = await poster("/api/connexion", { email: "inconnu@mon-recours.test", motDePasse: "mauvais-mot-de-passe-000" });
  const corpsInconnu = await inconnu.text();
  verifier("compte inconnu : réponse identique (pas d'énumération)", inconnu.status === 401 && corpsInconnu === corpsMauvais, `${inconnu.status}, corps ${corpsInconnu === corpsMauvais ? "identique" : "DIFFÉRENT"}`);

  // 4. connexion valide
  const bon = await poster("/api/connexion", { email: EMAIL, motDePasse });
  const setCookie = bon.headers.getSetCookie?.() ?? [];
  const cookieAdmin = cookieDepuis(bon, "mrci_admin") ?? setCookie.find((c) => c.startsWith("mrci_admin="))?.split(";")[0] ?? null;
  const entete = setCookie.join(" | ");
  verifier("connexion valide acceptée", bon.status === 200, String(bon.status));
  verifier("cookie HttpOnly", /HttpOnly/i.test(entete));
  verifier("cookie SameSite=Strict", /SameSite=Strict/i.test(entete));

  // 5. /admin avec le cookie
  const acces = await fetch(`${BASE}/admin`, { headers: { cookie: cookieAdmin ?? "" }, redirect: "manual" });
  const html = await acces.text();
  verifier("/admin accessible avec le cookie", acces.status === 200 && /Tableau de bord/i.test(html), String(acces.status));
  verifier("le tableau de bord dit que le moteur est injoignable", /njoignable/i.test(html));

  // 6. cookie falsifié
  const faux = await fetch(`${BASE}/admin`, { headers: { cookie: `${cookieAdmin ?? "monrecours_admin=x"}.tampered` }, redirect: "manual" });
  verifier("cookie falsifié refusé", faux.status === 307, String(faux.status));

  // 7. déconnexion
  const deconnexion = await poster("/api/deconnexion", {}, { cookie: cookieAdmin ?? "" });
  const efface = (deconnexion.headers.getSetCookie?.() ?? []).join(" | ");
  verifier("déconnexion traitée", [200, 303].includes(deconnexion.status), String(deconnexion.status));
  verifier("cookie effacé à la déconnexion", /Max-Age=0|Expires=Thu, 01 Jan 1970/i.test(efface));
  const sansCookie = await fetch(`${BASE}/admin`, { redirect: "manual" });
  verifier("/admin refermé pour un navigateur déconnecté", sansCookie.status === 307, String(sansCookie.status));

  // Limitation assumée du jeton sans état : on la mesure au lieu de la taire.
  const rejoue = await fetch(`${BASE}/admin`, { headers: { cookie: cookieAdmin ?? "" }, redirect: "manual" });
  if (rejoue.status === 200) {
    console.log("  LIMITE  un cookie copié AVANT la déconnexion reste valide jusqu'à l'expiration (2 h) — pas de révocation côté serveur");
  } else {
    console.log("  NOTE    le cookie copié est refusé après déconnexion");
  }

  // 8. journal d'audit
  await new Promise((r) => setTimeout(r, 300));
  const lignes = existsSync(cheminAudit) ? readFileSync(cheminAudit, "utf8").trim().split("\n").filter(Boolean) : [];
  verifier("journal d'audit écrit", lignes.length >= 3, `${lignes.length} ligne(s)`);
  verifier("aucun mot de passe dans le journal", !lignes.some((l) => l.includes(motDePasse)));
  verifier("aucune adresse e-mail en clair dans le journal", !lignes.some((l) => l.includes(EMAIL)));

  // 9. limitation des tentatives (en dernier : le compteur est déjà entamé)
  let bloquee = false;
  for (let i = 0; i < 8 && !bloquee; i++) {
    const r = await poster("/api/connexion", { email: EMAIL, motDePasse: "encore-faux-000000" }, { "x-forwarded-for": "203.0.113.55" });
    if (r.status === 429) bloquee = true;
  }
  verifier("tentatives limitées (429)", bloquee);
} finally {
  arreter();
}

const echecs = resultats.filter((r) => !r.ok);
console.log(`\n  ${resultats.length - echecs.length}/${resultats.length} contrôles réussis`);
process.exit(echecs.length === 0 ? 0 : 1);
