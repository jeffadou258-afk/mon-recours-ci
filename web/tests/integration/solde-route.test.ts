/**
 * Route réelle POST /api/admin/solde, appelée sans navigateur ni Next.
 *
 * Le service externe (moteur Python puis DeepSeek) est simulé par un
 * `Recuperateur` : aucun crédit n'est dépensé, aucun réseau n'est touché.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { executerVerificationSolde } from "../../src/lib/server/solde-route";
import { hacherMotDePasse } from "../../src/lib/server/auth/motdepasse";
import { lireEtatAuth, type Compte } from "../../src/lib/server/auth/comptes";
import { creerJeton, NOM_COOKIE_ADMIN } from "../../src/lib/server/auth/jeton";

const SECRET = "s".repeat(40);
const CLE_MOTEUR = "cle-moteur-de-test-0123456789abcdef";

let preparation: Promise<{ env: Record<string, string>; admin: string; lecteur: string }> | null = null;

function preparer() {
  preparation ??= (async () => {
    const admin = await hacherMotDePasse("mot de passe administrateur solide");
    const lecteur = await hacherMotDePasse("mot de passe lecteur solide");
    const env: Record<string, string> = {
      NODE_ENV: "test",
      MONRECOURS_SESSION_SECRET: SECRET,
      MONRECOURS_API_URL: "http://127.0.0.1:8765",
      MONRECOURS_API_KEY: CLE_MOTEUR,
      MONRECOURS_COMPTES: JSON.stringify([
        { email: "admin@exemple.ci", role: "administrateur", motDePasse: admin },
        { email: "lecteur@exemple.ci", role: "lecteur", motDePasse: lecteur },
      ]),
    };
    return { env, admin, lecteur };
  })();
  return preparation;
}

async function cookie(role: "administrateur" | "lecteur"): Promise<string> {
  const { env } = await preparer();
  const etat = lireEtatAuth(env);
  if (etat.etat !== "actif") throw new Error("configuration de test invalide");
  const compte = etat.comptes.find((c) => c.role === role) as Compte | undefined;
  if (!compte) throw new Error("compte de test introuvable");
  const jeton = creerJeton(compte, SECRET);
  return `${NOM_COOKIE_ADMIN}=${encodeURIComponent(jeton)}`;
}

function requete(entetes: Record<string, string> = {}): Request {
  return new Request("http://localhost/api/admin/solde", {
    method: "POST",
    headers: { "content-type": "application/json", host: "localhost", origin: "http://localhost", ...entetes },
    body: "{}",
  });
}

function moteur(corps: unknown, statut = 200) {
  const appels: string[] = [];
  const recuperer = async (url: string) => {
    appels.push(url);
    return new Response(JSON.stringify(corps), {
      status: statut,
      headers: { "Content-Type": "application/json" },
    });
  };
  return { recuperer, appels };
}

const audit = async () => {};

function charge(data: Record<string, unknown>) {
  return { ok: true, data };
}

async function appeler(entetes: Record<string, string>, recuperer: (url: string) => Promise<Response>) {
  const { env } = await preparer();
  const reponse = await executerVerificationSolde(requete(entetes), {
    env,
    recuperer: recuperer as never,
    audit,
  });
  return { statut: reponse.status, corps: (await reponse.json()) as Record<string, never> };
}

// ---------------------------------------------------------------------------
// Autorisation
// ---------------------------------------------------------------------------

test("sans session : 403, et le moteur n'est pas appelé", async () => {
  const { recuperer, appels } = moteur(charge({ reactive: true }));
  const { statut, corps } = await appeler({}, recuperer);
  assert.equal(statut, 403);
  assert.equal((corps as never as { erreur: { code: string } }).erreur.code, "ACCES_REFUSE");
  assert.equal(appels.length, 0, "le moteur a été sollicité sans autorisation");
});

test("session de lecteur : 403, pas d'appel au moteur", async () => {
  const { recuperer, appels } = moteur(charge({ reactive: true }));
  const { statut } = await appeler({ cookie: await cookie("lecteur") }, recuperer);
  assert.equal(statut, 403);
  assert.equal(appels.length, 0);
});

test("session d'administrateur : la vérification passe", async () => {
  const { recuperer, appels } = moteur(
    charge({ reactive: true, etat: "POSITIF", mode: "llm", devise: "USD", solde: "12.50", message: "ok" }),
  );
  const { statut, corps } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  assert.equal(statut, 200);
  assert.equal(appels.length, 1);
  assert.match(appels[0]!, /\/llm\/verifier-solde$/);
  assert.equal((corps as never as { data: { reactive: boolean } }).data.reactive, true);
});

// ---------------------------------------------------------------------------
// Résultats du fournisseur
// ---------------------------------------------------------------------------

test("solde positif : réactivation annoncée", async () => {
  const { recuperer } = moteur(charge({ reactive: true, mode: "llm", etat: "POSITIF", solde: "9.99" }));
  const { corps } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  const data = (corps as never as { data: { reactive: boolean; mode: string } }).data;
  assert.equal(data.reactive, true);
  assert.equal(data.mode, "llm");
});

test("solde épuisé : pas de réactivation, secours maintenu", async () => {
  const { recuperer } = moteur(charge({ reactive: false, mode: "deterministe", etat: "EPUISE", solde: "0" }));
  const { corps } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  const data = (corps as never as { data: { reactive: boolean; mode: string; etat: string } }).data;
  assert.equal(data.reactive, false);
  assert.equal(data.mode, "deterministe");
  assert.equal(data.etat, "EPUISE");
});

test("réponse ambiguë : pas de réactivation", async () => {
  const { recuperer } = moteur(charge({ reactive: false, etat: "AMBIGU", mode: "deterministe" }));
  const { corps } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  assert.equal((corps as never as { data: { reactive: boolean } }).data.reactive, false);
});

test("moteur injoignable : 503, aucun succès affiché", async () => {
  const recuperer = async () => {
    throw new Error("ECONNREFUSED");
  };
  const { statut, corps } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  assert.equal(statut, 503);
  assert.equal((corps as never as { ok: boolean }).ok, false);
});

test("moteur en erreur : 502, aucun succès affiché", async () => {
  const { recuperer } = moteur({ ok: false, erreur: { code: "INTERNE" } }, 500);
  const { statut } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  assert.equal(statut, 502);
});

test("moteur qui répond ok:false : 502", async () => {
  const { recuperer } = moteur({ ok: false, data: { reactive: true } }, 200);
  const { statut } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  assert.equal(statut, 502);
});

// ---------------------------------------------------------------------------
// Origine
// ---------------------------------------------------------------------------

test("origine étrangère : 403, aucun appel", async () => {
  const { recuperer, appels } = moteur(charge({ reactive: true }));
  const { statut, corps } = await appeler(
    { cookie: await cookie("administrateur"), origin: "https://attaquant.example" },
    recuperer,
  );
  assert.equal(statut, 403);
  assert.equal((corps as never as { erreur: { code: string } }).erreur.code, "ORIGINE_REFUSEE");
  assert.equal(appels.length, 0);
});

test("origine « null » d'un navigateur de même site : acceptée", async () => {
  const { recuperer } = moteur(charge({ reactive: false, etat: "EPUISE" }));
  const { statut } = await appeler(
    { cookie: await cookie("administrateur"), origin: "null", "sec-fetch-site": "same-origin" },
    recuperer,
  );
  assert.equal(statut, 200);
});

test("origine « null » sans preuve de même site : refusée", async () => {
  const { recuperer } = moteur(charge({ reactive: false }));
  const { statut } = await appeler(
    { cookie: await cookie("administrateur"), origin: "null", "sec-fetch-site": "cross-site" },
    recuperer,
  );
  assert.equal(statut, 403);
});

// ---------------------------------------------------------------------------
// Confidentialité et concurrence
// ---------------------------------------------------------------------------

test("la réponse ne contient ni la clé du moteur ni un secret", async () => {
  const { recuperer } = moteur(
    charge({ reactive: true, message: "ok", manques: [], incident: { ouvert: false } }),
  );
  const { corps } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  const texte = JSON.stringify(corps);
  assert.ok(!texte.includes(CLE_MOTEUR));
  assert.ok(!texte.includes("sk-"));
  assert.ok(!texte.includes(SECRET));
});

test("deux vérifications simultanées restent cohérentes", async () => {
  const { recuperer } = moteur(charge({ reactive: false, etat: "ERREUR", mode: "deterministe" }));
  const entetes = { cookie: await cookie("administrateur") };
  const [a, b] = await Promise.all([appeler(entetes, recuperer), appeler(entetes, recuperer)]);
  assert.equal(a.statut, 200);
  assert.equal(b.statut, 200);
  assert.equal(
    (a.corps as never as { data: { reactive: boolean } }).data.reactive,
    (b.corps as never as { data: { reactive: boolean } }).data.reactive,
    "deux réponses contradictoires",
  );
});

test("un corps inattendu du moteur ne produit pas de succès", async () => {
  const { recuperer } = moteur({ ok: true, data: "réponse inattendue" });
  const { statut, corps } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  assert.equal(statut, 200);
  assert.equal((corps as never as { data: { reactive: boolean } }).data.reactive, false);
});

test("ni Origin ni Sec-Fetch-Site : refusée (provenance non prouvée)", async () => {
  const { env } = await preparer();
  const { recuperer, appels } = moteur(charge({ reactive: true }));
  const nue = new Request("http://localhost/api/admin/solde", {
    method: "POST",
    headers: { "content-type": "application/json", host: "localhost", cookie: await cookie("administrateur") },
    body: "{}",
  });
  const reponse = await executerVerificationSolde(nue, { env, recuperer: recuperer as never, audit });
  assert.equal(reponse.status, 403);
  assert.equal(appels.length, 0);
});

test("Sec-Fetch-Site cross-site : refusée même avec une origine plausible", async () => {
  const { recuperer, appels } = moteur(charge({ reactive: true }));
  const { statut } = await appeler(
    { cookie: await cookie("administrateur"), "sec-fetch-site": "cross-site" },
    recuperer,
  );
  assert.equal(statut, 403);
  assert.equal(appels.length, 0);
});

test("l'incident renvoyé ne contient que des champs connus", async () => {
  const { recuperer } = moteur(
    charge({
      reactive: false,
      etat: "EPUISE",
      incident: { statut: "CREDITS_EPUISES", ouvert: true, persistant: false, champ_inconnu: "sk-fuite-0123456789" },
    }),
  );
  const { corps } = await appeler({ cookie: await cookie("administrateur") }, recuperer);
  const texte = JSON.stringify(corps);
  assert.ok(!texte.includes("champ_inconnu"));
  assert.ok(!texte.includes("sk-fuite"));
  const incident = (corps as never as { data: { incident: { ouvert: boolean; persistant: boolean } } }).data.incident;
  assert.equal(incident.ouvert, true);
  assert.equal(incident.persistant, false);
});
