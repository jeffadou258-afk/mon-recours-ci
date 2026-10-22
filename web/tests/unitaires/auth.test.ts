import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { hacherMotDePasse, lireEmpreinte, verifierMotDePasse } from "../../src/lib/server/auth/motdepasse";
import { lireEtatAuth, type Compte } from "../../src/lib/server/auth/comptes";
import { creerJeton, NOM_COOKIE_ADMIN, verifierJeton } from "../../src/lib/server/auth/jeton";
import { evaluerAccesAdmin } from "../../src/lib/server/auth/acces";
import { gererConnexion, gererDeconnexion } from "../../src/lib/server/auth/handlers-auth";
import { creerEcrivain, lireAudit, type LigneAudit } from "../../src/lib/server/auth/audit";
import { construireTableauDeBord } from "../../src/lib/server/auth/tableau";
import { origineAutorisee } from "../../src/lib/server/handlers";
import { LimiteurVisiteurs } from "../../src/lib/server/limiteur";
// @ts-expect-error script .mjs sans déclaration de types
import { hacher as hacherScript, controlerMotDePasse } from "../../scripts/creer-compte.mjs";

const SECRET = "s".repeat(24) + "-secret-de-test-long";
const MDP_ADMIN = "correct horse battery staple";
const MDP_LECTEUR = "un autre mot de passe solide";

let preparation: Promise<{ env: Record<string, string>; admin: string; lecteur: string }> | null = null;
function preparer() {
  preparation ??= (async () => {
    const admin = await hacherMotDePasse(MDP_ADMIN);
    const lecteur = await hacherMotDePasse(MDP_LECTEUR);
    const env = {
      NODE_ENV: "test",
      MONRECOURS_SESSION_SECRET: SECRET,
      MONRECOURS_COMPTES: JSON.stringify([
        { email: "Admin@Exemple.ci", role: "administrateur", motDePasse: admin },
        { email: "lecteur@exemple.ci", role: "lecteur", motDePasse: lecteur },
      ]),
    };
    return { env, admin, lecteur };
  })();
  return preparation;
}

function requeteConnexion(corps: unknown, entetes: Record<string, string> = {}): Request {
  return new Request("http://localhost/api/connexion", {
    method: "POST",
    headers: { "content-type": "application/json", origin: "http://localhost", host: "localhost", ...entetes },
    body: JSON.stringify(corps),
  });
}

function dependances(env: Record<string, string | undefined>, journal: LigneAudit[] = []) {
  return {
    env,
    audit: async (l: LigneAudit) => {
      journal.push(l);
    },
    limiteurVisiteurs: new LimiteurVisiteurs(),
    limiteurAdresses: new LimiteurVisiteurs(),
  };
}

function cookieDe(reponse: Response): string {
  const entete = reponse.headers.get("set-cookie") ?? "";
  return entete.split(";")[0]!;
}

// ---------------------------------------------------------------------------
// Empreintes
// ---------------------------------------------------------------------------

test("mot de passe : jamais stocké en clair, vérifié en temps constant", async () => {
  const empreinte = await hacherMotDePasse(MDP_ADMIN);
  assert.ok(empreinte.startsWith("scrypt$16384$8$1$"));
  assert.ok(!empreinte.includes(MDP_ADMIN));
  assert.equal(await verifierMotDePasse(MDP_ADMIN, empreinte), true);
  assert.equal(await verifierMotDePasse("mauvais mot de passe", empreinte), false);
  // Compte inconnu : une vérification factice a lieu, et elle échoue toujours.
  assert.equal(await verifierMotDePasse(MDP_ADMIN, null), false);
  assert.equal(await verifierMotDePasse(MDP_ADMIN, "n'importe quoi"), false);
});

test("empreintes faibles ou malformées : refusées à la lecture", () => {
  assert.equal(lireEmpreinte("scrypt$1024$8$1$AAAAAAAAAAAAAAAAAAAAAA$" + "A".repeat(43)), null);
  assert.equal(lireEmpreinte("bcrypt$xx"), null);
  assert.equal(lireEmpreinte(""), null);
});

test("script de création de compte : même format, vérifiable par le serveur", async () => {
  const empreinte = await hacherScript("phrase de passe de test 42");
  assert.equal(await verifierMotDePasse("phrase de passe de test 42", empreinte), true);
  assert.match(controlerMotDePasse("court") ?? "", /12 caractères/);
  assert.match(controlerMotDePasse("aaaaaaaaaaaaaaaa") ?? "", /répétitif/);
  assert.equal(controlerMotDePasse("une phrase suffisamment longue"), null);
});

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

test("configuration : administration fermée en démonstration, sans secret ou sans compte", async () => {
  const { env } = await preparer();
  assert.equal(lireEtatAuth({ ...env, MONRECOURS_MODE: "demo" }).etat, "desactive_demo");
  assert.equal(lireEtatAuth({ ...env, MONRECOURS_SESSION_SECRET: "court" }).etat, "non_configure");
  assert.equal(lireEtatAuth({ ...env, MONRECOURS_COMPTES: "" }).etat, "non_configure");
  assert.equal(lireEtatAuth({ ...env, MONRECOURS_COMPTES: "{pas du json" }).etat, "non_configure");
  const etat = lireEtatAuth(env);
  assert.equal(etat.etat, "actif");
  if (etat.etat === "actif") {
    assert.deepEqual(
      etat.comptes.map((c) => [c.email, c.role]),
      [
        ["admin@exemple.ci", "administrateur"],
        ["lecteur@exemple.ci", "lecteur"],
      ],
    );
  }
});

test("configuration : entrées douteuses écartées, jamais devinées", async () => {
  const { admin } = await preparer();
  const etat = lireEtatAuth({
    MONRECOURS_SESSION_SECRET: SECRET,
    MONRECOURS_COMPTES: JSON.stringify([
      { email: "a@exemple.ci", role: "superadmin", motDePasse: admin },
      { email: "b@exemple.ci", role: "administrateur", motDePasse: "motdepasseenclair" },
      { email: "pas-une-adresse", role: "administrateur", motDePasse: admin },
      { email: "c@exemple.ci", role: "administrateur", motDePasse: admin },
      { email: "C@exemple.ci", role: "lecteur", motDePasse: admin },
    ]),
  });
  assert.equal(etat.etat, "actif");
  if (etat.etat === "actif") {
    assert.deepEqual(etat.comptes.map((c) => c.email), ["c@exemple.ci"]);
    assert.equal(etat.ignores, 4);
  }
});

// ---------------------------------------------------------------------------
// Jeton de session
// ---------------------------------------------------------------------------

test("jeton : altéré, expiré, d'un autre secret ou d'un compte retiré → refusé", async () => {
  const { env } = await preparer();
  const etat = lireEtatAuth(env);
  assert.equal(etat.etat, "actif");
  if (etat.etat !== "actif") return;
  const [admin, lecteur] = etat.comptes as [Compte, Compte];
  const t0 = 1_800_000_000;
  const jeton = creerJeton(lecteur, SECRET, t0);

  assert.equal(verifierJeton(jeton, etat.comptes, SECRET, t0 + 10)?.email, "lecteur@exemple.ci");
  // Modifier la charge (pour viser le compte administrateur) casse la signature.
  const [charge, signature] = jeton.split(".") as [string, string];
  const falsifiee = JSON.parse(Buffer.from(charge, "base64url").toString());
  falsifiee.e = admin.email;
  falsifiee.r = "administrateur";
  const jetonFalsifie = `${Buffer.from(JSON.stringify(falsifiee)).toString("base64url")}.${signature}`;
  assert.equal(verifierJeton(jetonFalsifie, etat.comptes, SECRET, t0 + 10), null);

  assert.equal(verifierJeton(jeton, etat.comptes, SECRET, t0 + 2 * 3600 - 1)?.email, "lecteur@exemple.ci", "encore valide juste avant 2 h");
  assert.equal(verifierJeton(jeton, etat.comptes, SECRET, t0 + 2 * 3600), null, "expiré à 2 h pile");
  assert.equal(verifierJeton(jeton, etat.comptes, SECRET, t0 + 8 * 3600), null, "expiré");
  assert.equal(verifierJeton(jeton, etat.comptes, "x".repeat(40), t0 + 10), null, "autre secret");
  assert.equal(verifierJeton(jeton, [admin], SECRET, t0 + 10), null, "compte retiré");
  const mdpChange: Compte = { ...lecteur, empreinte: await hacherMotDePasse("nouveau mot de passe solide") };
  assert.equal(verifierJeton(jeton, [admin, mdpChange], SECRET, t0 + 10), null, "mot de passe changé");
  assert.equal(verifierJeton("web-123.abc", etat.comptes, SECRET, t0), null, "cookie de consultation");
});

// ---------------------------------------------------------------------------
// Décision d'accès : anonyme, utilisateur standard, administrateur
// ---------------------------------------------------------------------------

test("accès /admin : non authentifié → anonyme ; lecteur → refusé ; administrateur → autorisé", async () => {
  const { env } = await preparer();
  const etat = lireEtatAuth(env);
  if (etat.etat !== "actif") throw new Error("configuration de test invalide");
  const [admin, lecteur] = etat.comptes as [Compte, Compte];

  assert.equal(evaluerAccesAdmin(null, env).acces, "anonyme");
  assert.equal(evaluerAccesAdmin(`${NOM_COOKIE_ADMIN}=n%27importe.quoi`, env).acces, "anonyme");
  assert.equal(evaluerAccesAdmin(`${NOM_COOKIE_ADMIN}=${creerJeton(lecteur, SECRET)}`, env).acces, "refuse");
  assert.equal(evaluerAccesAdmin(`${NOM_COOKIE_ADMIN}=${creerJeton(admin, SECRET)}`, env).acces, "autorise");
  // Même avec un jeton administrateur valide, la démonstration publique reste fermée.
  assert.equal(
    evaluerAccesAdmin(`${NOM_COOKIE_ADMIN}=${creerJeton(admin, SECRET)}`, { ...env, MONRECOURS_MODE: "demo" }).acces,
    "ferme",
  );
});

// ---------------------------------------------------------------------------
// POST /api/connexion
// ---------------------------------------------------------------------------

test("connexion : aucun succès simulé quand l'authentification n'est pas configurée", async () => {
  const demo = await gererConnexion(requeteConnexion({ email: "a@b.ci", motDePasse: "x" }), dependances({ MONRECOURS_MODE: "demo" }));
  assert.equal(demo.status, 503);
  assert.equal(demo.headers.get("set-cookie"), null);
  assert.equal(((await demo.json()) as { erreur: { code: string } }).erreur.code, "AUTH_DESACTIVEE_DEMO");

  const vide = await gererConnexion(requeteConnexion({ email: "a@b.ci", motDePasse: "x" }), dependances({ MONRECOURS_SESSION_SECRET: SECRET }));
  assert.equal(vide.status, 503);
  assert.equal(vide.headers.get("set-cookie"), null);
});

test("connexion : même réponse que le compte existe ou non (aucune énumération)", async () => {
  const { env } = await preparer();
  const journal: LigneAudit[] = [];
  const dep = dependances(env, journal);
  const existant = await gererConnexion(requeteConnexion({ email: "admin@exemple.ci", motDePasse: "faux mot de passe" }), dep);
  const inconnu = await gererConnexion(requeteConnexion({ email: "personne@exemple.ci", motDePasse: "faux mot de passe" }), dep);
  assert.equal(existant.status, 401);
  assert.equal(inconnu.status, 401);
  assert.deepEqual(await existant.json(), await inconnu.json());
  assert.equal(existant.headers.get("set-cookie"), null);
  // Le journal ne contient ni l'adresse saisie ni le mot de passe tenté.
  const brut = JSON.stringify(journal);
  assert.ok(!brut.includes("faux mot de passe"));
  assert.ok(!brut.includes("personne@exemple.ci"));
  assert.deepEqual(journal.map((l) => l.evenement), ["connexion_refusee", "connexion_refusee"]);
});

test("connexion : origine étrangère et entrées invalides refusées", async () => {
  const { env } = await preparer();
  const etrangere = await gererConnexion(
    requeteConnexion({ email: "admin@exemple.ci", motDePasse: MDP_ADMIN }, { origin: "https://pirate.example" }),
    dependances(env),
  );
  assert.equal(etrangere.status, 403);
  for (const corps of [{}, { email: "pas-une-adresse", motDePasse: "x" }, { email: "a@b.ci", motDePasse: "" }, { email: "a@b.ci", motDePasse: "x".repeat(2000) }]) {
    const r = await gererConnexion(requeteConnexion(corps), dependances(env));
    assert.equal(r.status, 400, JSON.stringify(corps).slice(0, 60));
  }
});

test("origine : formulaire même origine avec Origin « null » accepté, croisé refusé", () => {
  // `Referrer-Policy: no-referrer` fait envoyer `Origin: null` par Chrome sur une
  // soumission de formulaire, même de même origine. La déconnexion échouait en 403
  // en production : ce test décrit la règle attendue.
  const cas = (entetes: Record<string, string>) =>
    origineAutorisee(
      new Request("https://exemple.ci/api/deconnexion", { method: "POST", headers: entetes }),
    );
  assert.equal(cas({ origin: "null", "sec-fetch-site": "same-origin" }), true, "navigateur même origine");
  assert.equal(cas({ origin: "null" }), false, "« null » sans preuve de même origine");
  assert.equal(cas({ origin: "null", "sec-fetch-site": "cross-site" }), false, "« null » depuis un autre site");
  assert.equal(cas({ origin: "null", "sec-fetch-site": "same-site" }), false, "« null » depuis un sous-domaine");
  assert.equal(cas({ origin: "https://exemple.ci", host: "exemple.ci" }), true, "origine explicite identique");
  assert.equal(cas({ origin: "https://pirate.example", host: "exemple.ci" }), false, "origine étrangère");
  assert.equal(cas({}), true, "aucune origine (curl, tests) : toléré");
});

test("connexion : tentatives limitées par adresse (même depuis plusieurs visiteurs)", async () => {
  const { env } = await preparer();
  const dep = dependances(env);
  const statuts: number[] = [];
  for (let i = 0; i < 7; i++) {
    const r = await gererConnexion(
      requeteConnexion({ email: "admin@exemple.ci", motDePasse: `essai ${i}` }, { "x-forwarded-for": `10.0.0.${i}` }),
      dep,
    );
    statuts.push(r.status);
    if (r.status === 429) assert.ok(Number(r.headers.get("retry-after")) >= 1);
  }
  assert.deepEqual(statuts, [401, 401, 401, 401, 401, 429, 429]);
  // Le bon mot de passe n'est plus testé tant que la limite court.
  const bloque = await gererConnexion(requeteConnexion({ email: "admin@exemple.ci", motDePasse: MDP_ADMIN }), dep);
  assert.equal(bloque.status, 429);
});

test("connexion réussie : cookie HttpOnly, SameSite=Strict, Secure en production, destination fixe", async () => {
  const { env } = await preparer();
  const journal: LigneAudit[] = [];
  const r = await gererConnexion(
    requeteConnexion({ email: "  ADMIN@exemple.ci ", motDePasse: MDP_ADMIN, redirection: "https://pirate.example" }),
    dependances({ ...env, NODE_ENV: "production" }, journal),
  );
  assert.equal(r.status, 200);
  assert.deepEqual(await r.json(), { ok: true, data: { redirection: "/admin" } });
  const cookie = r.headers.get("set-cookie") ?? "";
  for (const attendu of ["mrci_admin=", "Path=/", "HttpOnly", "SameSite=Strict", "Secure", "Max-Age=7200"]) {
    assert.ok(cookie.includes(attendu), `${attendu} absent de ${cookie}`);
  }
  assert.ok(!cookie.includes(MDP_ADMIN));
  assert.equal(evaluerAccesAdmin(cookieDe(r), env).acces, "autorise");
  assert.deepEqual(journal.map((l) => [l.evenement, l.compte]), [["connexion_reussie", "admin@exemple.ci"]]);
});

test("utilisateur standard : un rôle envoyé par le client n'élève jamais les droits", async () => {
  const { env } = await preparer();
  const r = await gererConnexion(
    requeteConnexion({ email: "lecteur@exemple.ci", motDePasse: MDP_LECTEUR, role: "administrateur", admin: true }),
    dependances(env),
  );
  assert.equal(r.status, 200);
  assert.equal(evaluerAccesAdmin(cookieDe(r), env).acces, "refuse");
});

// ---------------------------------------------------------------------------
// POST /api/deconnexion
// ---------------------------------------------------------------------------

test("déconnexion : cookie effacé, retour à la connexion, événement journalisé", async () => {
  const { env } = await preparer();
  const etat = lireEtatAuth(env);
  if (etat.etat !== "actif") throw new Error("configuration de test invalide");
  const journal: LigneAudit[] = [];
  const r = await gererDeconnexion(
    new Request("http://localhost/api/deconnexion", {
      method: "POST",
      headers: {
        origin: "http://localhost",
        host: "localhost",
        cookie: `${NOM_COOKIE_ADMIN}=${creerJeton(etat.comptes[0]!, SECRET)}`,
      },
    }),
    dependances(env, journal),
  );
  assert.equal(r.status, 303);
  assert.equal(r.headers.get("location"), "/connexion?deconnecte=1");
  assert.match(r.headers.get("set-cookie") ?? "", /mrci_admin=; Path=\/; Max-Age=0; HttpOnly; SameSite=Strict/);
  assert.deepEqual(journal.map((l) => l.evenement), ["deconnexion"]);

  const etrangere = await gererDeconnexion(
    new Request("http://localhost/api/deconnexion", { method: "POST", headers: { origin: "https://pirate.example", host: "localhost" } }),
    dependances(env),
  );
  assert.equal(etrangere.status, 403);
});

// ---------------------------------------------------------------------------
// Journal d'audit et tableau de bord
// ---------------------------------------------------------------------------

test("audit : fichier optionnel, lu du plus récent au plus ancien", async () => {
  const dossier = mkdtempSync(join(tmpdir(), "mrci-audit-"));
  try {
    const env = { MONRECOURS_AUDIT_FICHIER: join(dossier, "audit.jsonl") };
    assert.equal(await lireAudit(50, {}), null, "sans fichier : non connecté");
    const ecrire = creerEcrivain(env);
    const avertissement = console.warn;
    console.warn = () => {};
    try {
      await ecrire({ horodatage: "2026-10-21T10:00:00.000Z", evenement: "connexion_reussie", compte: "a@b.ci" });
      await ecrire({ horodatage: "2026-10-21T10:05:00.000Z", evenement: "deconnexion", compte: "a@b.ci" });
    } finally {
      console.warn = avertissement;
    }
    const lues = await lireAudit(50, env);
    assert.deepEqual(lues?.map((l) => l.evenement), ["deconnexion", "connexion_reussie"]);
    assert.equal(readFileSync(env.MONRECOURS_AUDIT_FICHIER, "utf8").split("\n").filter(Boolean).length, 2);
  } finally {
    rmSync(dossier, { recursive: true, force: true });
  }
});

test("tableau de bord : aucune valeur secrète, données absentes dites absentes", async () => {
  const { env } = await preparer();
  const etat = lireEtatAuth(env);
  if (etat.etat !== "actif") throw new Error("configuration de test invalide");
  const cle = "cle-moteur-tres-secrete-0123456789";
  const envComplet = { ...env, MONRECOURS_API_KEY: cle, MONRECOURS_API_URL: "http://127.0.0.1:8765" };
  const donnees = await construireTableauDeBord(etat.comptes[0]!, etat.comptes, 0, envComplet, {
    recuperer: async () => {
      throw new Error("moteur arrêté");
    },
  });
  const brut = JSON.stringify(donnees);
  assert.ok(!brut.includes(cle), "clé du moteur exposée");
  assert.ok(!brut.includes(SECRET), "secret de session exposé");
  assert.ok(!brut.includes("scrypt$"), "empreinte exposée");
  assert.equal(donnees.sante, null);
  assert.equal(donnees.plateforme.moteur, "injoignable");
  assert.equal(donnees.audit, null);
  assert.equal(donnees.parametres.find((p) => p.libelle === "Clé d'accès au moteur")?.valeur, "Configurée");
});

// ---------------------------------------------------------------------------
// F1 — sessions de deux heures
// ---------------------------------------------------------------------------

test("session : durée de 2 h, expiration vérifiée côté serveur même si le navigateur garde le cookie", async () => {
  const { DUREE_SESSION_ADMIN_SECONDES } = await import("../../src/lib/server/auth/jeton");
  assert.equal(DUREE_SESSION_ADMIN_SECONDES, 7200);
  const { env } = await preparer();
  const etat = lireEtatAuth(env);
  if (etat.etat !== "actif") throw new Error("configuration de test invalide");
  const admin = etat.comptes[0]!;
  const t0 = 1_800_000_000;
  const jeton = creerJeton(admin, SECRET, t0);
  const cookie = `${NOM_COOKIE_ADMIN}=${jeton}`;
  assert.equal(evaluerAccesAdmin(cookie, env, t0 + 7199).acces, "autorise");
  assert.equal(evaluerAccesAdmin(cookie, env, t0 + 7200).acces, "anonyme");
  assert.equal(evaluerAccesAdmin(cookie, env, t0 + 86400).acces, "anonyme");
  // Un jeton « allongé » (exp repoussé) n'est pas accepté : la signature ne correspond plus.
  const [charge, signature] = jeton.split(".") as [string, string];
  const allonge = JSON.parse(Buffer.from(charge, "base64url").toString());
  allonge.exp = t0 + 30 * 86400;
  const faux = `${Buffer.from(JSON.stringify(allonge)).toString("base64url")}.${signature}`;
  assert.equal(evaluerAccesAdmin(`${NOM_COOKIE_ADMIN}=${faux}`, env, t0 + 7300).acces, "anonyme");
});

// ---------------------------------------------------------------------------
// F6 — empreinte factice prête dès le démarrage
// ---------------------------------------------------------------------------

test("empreinte factice : préparée au démarrage, coût comparable compte existant / inconnu", async () => {
  const { preparerEmpreinteFactice } = await import("../../src/lib/server/auth/motdepasse");
  await preparerEmpreinteFactice();
  const { register } = await import("../../src/instrumentation");
  const avant = process.env.NEXT_RUNTIME;
  process.env.NEXT_RUNTIME = "nodejs";
  try {
    await register();
  } finally {
    if (avant === undefined) delete process.env.NEXT_RUNTIME;
    else process.env.NEXT_RUNTIME = avant;
  }

  const empreinte = await hacherMotDePasse(MDP_ADMIN);
  const mesurer = async (stockee: string | null) => {
    const t = process.hrtime.bigint();
    await verifierMotDePasse("mot de passe essayé", stockee);
    return Number(process.hrtime.bigint() - t) / 1e6;
  };
  const existant: number[] = [];
  const inconnu: number[] = [];
  for (let i = 0; i < 7; i++) {
    existant.push(await mesurer(empreinte));
    inconnu.push(await mesurer(null));
  }
  const mediane = (v: number[]) => [...v].sort((a, b) => a - b)[Math.floor(v.length / 2)]!;
  const rapport = mediane(inconnu) / mediane(existant);
  assert.ok(rapport > 0.5 && rapport < 2, `rapport des durées inconnu/existant = ${rapport.toFixed(2)}`);
});
