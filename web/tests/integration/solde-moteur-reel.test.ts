/**
 * POST /api/admin/solde de bout en bout : route web réelle -> moteur Python
 * RÉEL (bin/serveur_api.py) -> faux DeepSeek LOCAL (127.0.0.1).
 *
 * Seul DeepSeek est simulé : aucun crédit, aucun réseau extérieur. C'est ce test
 * qui aurait révélé que le moteur aiguillait `/llm/verifier-solde` vers
 * `repondre` (ENTREE_INVALIDE) : la réactivation n'atteignait jamais le moteur.
 */

import { test, before, after, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { createServer, type Server } from "node:http";
import { mkdtempSync, rmSync, writeFileSync, readFileSync, mkdirSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import type { AddressInfo } from "node:net";
import { executerVerificationSolde } from "../../src/lib/server/solde-route";
import { hacherMotDePasse } from "../../src/lib/server/auth/motdepasse";
import { lireEtatAuth, type Compte } from "../../src/lib/server/auth/comptes";
import { creerJeton, NOM_COOKIE_ADMIN } from "../../src/lib/server/auth/jeton";
import type { ConfigServeur } from "../../src/lib/server/config";
import { lancerMoteur, type MoteurLance } from "../moteur-reel";

const SECRET = "secret-de-session-de-test-0123456789-abcdef";
const CLE_LLM = "sk-faux-deepseek-0123456789abcdef-ne-doit-pas-sortir";

let dossier = "";
let fichierIncident = "";
let moteur: MoteurLance;
let faux: Server;
let reponseSolde: { statut: number; corps: string } = { statut: 200, corps: "{}" };
let appelsSolde: string[] = [];
let env: Record<string, string> = {};

const POSITIF = JSON.stringify({
  is_available: true,
  balance_infos: [{ currency: "USD", total_balance: "4.20", granted_balance: "0", topped_up_balance: "4.20" }],
});
const EPUISE = JSON.stringify({ is_available: false, balance_infos: [{ currency: "USD", total_balance: "0.00" }] });

function ouvrirIncident(): void {
  writeFileSync(
    fichierIncident,
    JSON.stringify({ statut: "CREDITS_EPUISES", fournisseur: "deepseek", detecte_le: "2026-10-22T20:00:00", resolu_le: null }),
  );
}

before(async () => {
  dossier = mkdtempSync(join(tmpdir(), "solde-reel-"));
  const runtime = join(dossier, "RUNTIME");
  mkdirSync(runtime, { mode: 0o700 });
  fichierIncident = join(runtime, "incident.json");

  faux = createServer((requete, reponse) => {
    if (requete.method === "GET" && requete.url === "/user/balance") {
      appelsSolde.push(String(requete.headers.authorization ?? ""));
      reponse.writeHead(reponseSolde.statut, { "Content-Type": "application/json" });
      reponse.end(reponseSolde.corps);
      return;
    }
    reponse.writeHead(500);
    reponse.end();
  });
  await new Promise<void>((ok) => faux.listen(0, "127.0.0.1", () => ok()));
  const portFaux = (faux.address() as AddressInfo).port;

  moteur = await lancerMoteur({
    env: {
      MONRECOURS_PDF_NON_DISTRIBUES: "1",
      MONRECOURS_INCIDENT_FICHIER: fichierIncident,
      MONRECOURS_LLM_REGISTRE: join(runtime, "registre.json"),
      MONRECOURS_VERROU_SOLDE: join(runtime, "verrou.lock"),
      MONRECOURS_LLM_FOURNISSEUR: "deepseek",
      MONRECOURS_LLM_API_KEY: CLE_LLM,
      MONRECOURS_LLM_ACCORD_DONNEES: "oui",
      MONRECOURS_LLM_URL: `http://127.0.0.1:${portFaux}/chat/completions`,
      MONRECOURS_LLM_URL_SOLDE: `http://127.0.0.1:${portFaux}/user/balance`,
    },
  });

  const admin = await hacherMotDePasse("mot de passe administrateur solide");
  const lecteur = await hacherMotDePasse("mot de passe lecteur solide");
  env = {
    NODE_ENV: "test",
    MONRECOURS_SESSION_SECRET: SECRET,
    MONRECOURS_API_URL: moteur.url,
    MONRECOURS_API_KEY: moteur.cle,
    MONRECOURS_COMPTES: JSON.stringify([
      { email: "admin@exemple.ci", role: "administrateur", motDePasse: admin },
      { email: "lecteur@exemple.ci", role: "lecteur", motDePasse: lecteur },
    ]),
  };
});

after(async () => {
  await moteur?.arreter();
  await new Promise<void>((ok) => (faux ? faux.close(() => ok()) : ok()));
  rmSync(dossier, { recursive: true, force: true });
});

beforeEach(() => {
  appelsSolde = [];
  reponseSolde = { statut: 200, corps: POSITIF };
  ouvrirIncident();
});

function config(): ConfigServeur {
  return {
    urlMoteur: moteur.url,
    cleMoteur: moteur.cle,
    secretSession: SECRET,
    delaiMs: 20000,
    production: false,
    debitVisiteur: 1000,
    demo: false,
  };
}

function cookie(role: "administrateur" | "lecteur"): string {
  const etat = lireEtatAuth(env);
  if (etat.etat !== "actif") throw new Error("configuration de test invalide");
  const compte = etat.comptes.find((c) => c.role === role) as Compte | undefined;
  if (!compte) throw new Error("compte introuvable");
  return `${NOM_COOKIE_ADMIN}=${encodeURIComponent(creerJeton(compte, SECRET))}`;
}

async function appeler(entetes: Record<string, string>) {
  const requete = new Request("http://localhost/api/admin/solde", {
    method: "POST",
    headers: { "content-type": "application/json", host: "localhost", origin: "http://localhost", ...entetes },
    body: "{}",
  });
  const reponse = await executerVerificationSolde(requete, { env, config: config(), audit: async () => {} });
  const texte = await reponse.text();
  assert.ok(!texte.includes(CLE_LLM), "la clé du fournisseur est sortie du serveur");
  assert.ok(!texte.includes(moteur.cle), "la clé du moteur est sortie du serveur");
  return { statut: reponse.status, corps: JSON.parse(texte) as { ok: boolean; data?: Record<string, unknown> } };
}

async function incidentDuMoteur(): Promise<{ ouvert: boolean }> {
  const reponse = await fetch(`${moteur.url}/sante`, { headers: { "X-API-Key": moteur.cle } });
  const corps = (await reponse.json()) as { data: { langage: { incident: { ouvert: boolean } } } };
  return corps.data.langage.incident;
}

test("administrateur, solde positif : le moteur réel clôt l'incident", async () => {
  assert.equal((await incidentDuMoteur()).ouvert, true);
  const { statut, corps } = await appeler({ cookie: cookie("administrateur") });
  assert.equal(statut, 200, JSON.stringify(corps));
  assert.equal(corps.data?.reactive, true);
  assert.equal(corps.data?.etat, "POSITIF");
  assert.equal((await incidentDuMoteur()).ouvert, false, "l'état du moteur n'a pas changé");
  assert.equal(JSON.parse(readFileSync(fichierIncident, "utf8")).statut, "RESOLU");
  assert.deepEqual(appelsSolde, [`Bearer ${CLE_LLM}`]);
});

test("solde épuisé : 200, pas de réactivation, incident ouvert dans le moteur", async () => {
  reponseSolde = { statut: 200, corps: EPUISE };
  const { statut, corps } = await appeler({ cookie: cookie("administrateur") });
  assert.equal(statut, 200);
  assert.equal(corps.data?.reactive, false);
  assert.equal(corps.data?.etat, "EPUISE");
  assert.equal((await incidentDuMoteur()).ouvert, true);
});

test("erreur HTTP du fournisseur : incident ouvert, aucun succès", async () => {
  reponseSolde = { statut: 503, corps: "{}" };
  const { corps } = await appeler({ cookie: cookie("administrateur") });
  assert.equal(corps.data?.reactive, false);
  assert.equal(corps.data?.etat, "ERREUR");
  assert.equal((await incidentDuMoteur()).ouvert, true);
});

test("réponse mal formée : incident ouvert", async () => {
  reponseSolde = { statut: 200, corps: "<html>" };
  const { corps } = await appeler({ cookie: cookie("administrateur") });
  assert.equal(corps.data?.etat, "AMBIGU");
  assert.equal((await incidentDuMoteur()).ouvert, true);
});

test("sans session : 403, le fournisseur n'est jamais interrogé", async () => {
  const { statut } = await appeler({});
  assert.equal(statut, 403);
  assert.equal(appelsSolde.length, 0);
  assert.equal((await incidentDuMoteur()).ouvert, true);
});

test("session de lecteur : 403, le fournisseur n'est jamais interrogé", async () => {
  const { statut } = await appeler({ cookie: cookie("lecteur") });
  assert.equal(statut, 403);
  assert.equal(appelsSolde.length, 0);
});

test("origine étrangère : 403, le fournisseur n'est jamais interrogé", async () => {
  const { statut } = await appeler({ cookie: cookie("administrateur"), origin: "https://attaquant.example" });
  assert.equal(statut, 403);
  assert.equal(appelsSolde.length, 0);
});
