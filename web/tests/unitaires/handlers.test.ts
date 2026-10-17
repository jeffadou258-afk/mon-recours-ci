import { test } from "node:test";
import assert from "node:assert/strict";
import { gererOuvrir, gererRepondre, gererSante } from "../../src/lib/server/handlers";
import { ConfigurationInvalide } from "../../src/lib/server/config";
import { emballer, nouvelIdentifiant } from "../../src/lib/server/session";
import { CONFIG_TEST, fauxMoteur, fixture, journalMuet, requeteJson } from "../aides";

const config = () => CONFIG_TEST;

function cookieValide(): string {
  return `mrci_dossier=${encodeURIComponent(emballer(nouvelIdentifiant(), CONFIG_TEST.secretSession))}`;
}

test("ouvrir : l'identifiant est généré côté serveur et posé en cookie HttpOnly", async () => {
  const moteur = fauxMoteur(200, fixture("ouvrir_caution"));
  const rep = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution.", dossier_id: "../pirate" }),
    { config, recuperer: moteur.recuperer, journal: journalMuet },
  );
  assert.equal(rep.status, 200);
  const envoye = JSON.parse(String(moteur.appels[0]!.init.body));
  assert.match(envoye.dossier_id, /^web-/, "le dossier_id fourni par le client doit être ignoré");
  assert.equal(moteur.appels[0]!.url, "http://127.0.0.1:8765/ouvrir");
  assert.equal((moteur.appels[0]!.init.headers as Record<string, string>)["X-API-Key"], CONFIG_TEST.cleMoteur);

  const cookie = rep.headers.get("set-cookie") ?? "";
  assert.match(cookie, /mrci_dossier=web-/);
  assert.match(cookie, /HttpOnly/);
  const corps = await rep.json();
  assert.equal(corps.ok, true);
  assert.equal(corps.data.etape, "clarification");
  assert.ok(!JSON.stringify(corps).includes(CONFIG_TEST.cleMoteur), "la clé ne doit jamais revenir au client");
  assert.ok(!JSON.stringify(corps).includes(envoye.dossier_id), "l'identifiant ne doit pas être exposé");
});

test("ouvrir hors catalogue : pas de cookie (aucune suite possible)", async () => {
  const moteur = fauxMoteur(200, fixture("ouvrir_hors"));
  const rep = await gererOuvrir(requeteJson("/api/ouvrir", { demande: "Mon patron ne me paie plus." }), {
    config,
    recuperer: moteur.recuperer,
  });
  assert.equal(rep.headers.get("set-cookie"), null);
  assert.equal((await rep.json()).data.statut, "CONCLUSION_IMPOSSIBLE");
});

test("entrées malformées : refusées avant tout appel au moteur", async () => {
  const moteur = fauxMoteur(200, {});
  const dep = { config, recuperer: moteur.recuperer };
  const cas: [Request, number, string][] = [
    [requeteJson("/api/ouvrir", "{pas du json"), 400, "ENTREE_INVALIDE"],
    [requeteJson("/api/ouvrir", [1, 2]), 400, "ENTREE_INVALIDE"],
    [requeteJson("/api/ouvrir", { demande: "" }), 400, "ENTREE_INVALIDE"],
    [requeteJson("/api/ouvrir", { demande: 12 }), 400, "ENTREE_INVALIDE"],
    [requeteJson("/api/ouvrir", { demande: "x".repeat(4001) }), 400, "ENTREE_INVALIDE"],
    [requeteJson("/api/ouvrir", { demande: "y".repeat(20000) }), 413, "CORPS_TROP_GRAND"],
    [
      new Request("http://localhost:3000/api/ouvrir", {
        method: "POST",
        headers: { "Content-Type": "text/plain" },
        body: "demande",
      }),
      415,
      "TYPE_NON_SUPPORTE",
    ],
  ];
  for (const [requete, statut, code] of cas) {
    const rep = await gererOuvrir(requete, dep);
    assert.equal(rep.status, statut, code);
    assert.equal((await rep.json()).erreur.code, code);
  }
  assert.equal(moteur.appels.length, 0);
});

test("requête d'un autre site : refusée (CSRF)", async () => {
  const moteur = fauxMoteur(200, fixture("ouvrir_caution"));
  const dep = { config, recuperer: moteur.recuperer };
  const r1 = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution." }, { Origin: "https://pirate.example" }),
    dep,
  );
  assert.equal(r1.status, 403);
  const r2 = await gererRepondre(
    requeteJson("/api/repondre", { reponses: {} }, { "Sec-Fetch-Site": "cross-site", Cookie: cookieValide() }),
    dep,
  );
  assert.equal(r2.status, 403);
  assert.equal(moteur.appels.length, 0);
});

test("répondre sans cookie, ou avec un cookie forgé : refusé sans joindre le moteur", async () => {
  const moteur = fauxMoteur(200, fixture("repondre_caution"));
  const dep = { config, recuperer: moteur.recuperer };
  const sans = await gererRepondre(requeteJson("/api/repondre", { reponses: { logement: "oui" } }), dep);
  assert.equal(sans.status, 409);
  assert.equal((await sans.json()).erreur.code, "SESSION_ABSENTE");
  const forge = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { logement: "oui" } }, { Cookie: "mrci_dossier=AUDIT1.ZmF1eA" }),
    dep,
  );
  assert.equal((await forge.json()).erreur.code, "SESSION_ABSENTE");
  assert.equal(moteur.appels.length, 0);
});

test("répondre : réponse assainie, sans chemin serveur", async () => {
  const moteur = fauxMoteur(200, fixture("repondre_caution"));
  const rep = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { logement: "oui", inconnu: null } }, { Cookie: cookieValide() }),
    { config, recuperer: moteur.recuperer },
  );
  assert.equal(rep.status, 200);
  const texte = await rep.text();
  assert.doesNotMatch(texte, /\/home\/|DOSSIERS|traceabilite/);
  const corps = JSON.parse(texte);
  assert.equal(corps.data.sources.length, 2);
  const envoye = JSON.parse(String(moteur.appels[0]!.init.body));
  assert.deepEqual(envoye.reponses, { logement: "oui", inconnu: null });
});

test("analyse refusée par le moteur : présentée comme un résultat sans conclusion", async () => {
  const moteur = fauxMoteur(422, {
    ok: false,
    erreur: { code: "ANALYSE_REFUSEE", message: "analyse non conforme : REGLE_SANS_SOURCE" },
  });
  const rep = await gererRepondre(requeteJson("/api/repondre", { reponses: {} }, { Cookie: cookieValide() }), {
    config,
    recuperer: moteur.recuperer,
  });
  const corps = await rep.json();
  assert.equal(corps.ok, true);
  assert.equal(corps.data.statut, "ANALYSE_REFUSEE");
  assert.equal(corps.data.sources.length, 0);
  assert.equal(corps.data.droit.length, 0);
});

test("erreurs du moteur traduites, sans fuite de détail interne", async () => {
  const cas: [number, unknown, Record<string, string>, number, string][] = [
    [401, { ok: false, erreur: { code: "NON_AUTHENTIFIE" } }, {}, 500, "CONFIGURATION"],
    [429, { ok: false, erreur: { code: "DEBIT_DEPASSE" } }, { "Retry-After": "12" }, 429, "DEBIT_DEPASSE"],
    [422, fixtureErreur("DOSSIER_INCONNU"), {}, 409, "DOSSIER_INCONNU"],
    [422, fixtureErreur("CATALOGUE_INVALIDE"), {}, 503, "CATALOGUE_INVALIDE"],
    [422, { ok: false, erreur: { code: "INTERNE", message: "Traceback /Users/mac/secret.py" } }, {}, 502, "INTERNE"],
    [500, {}, {}, 503, "SERVICE_INDISPONIBLE"],
    [200, { ok: true, data: { etape: "nouvelle_etape_inconnue" } }, {}, 502, "REPONSE_INVALIDE"],
  ];
  for (const [statutMoteur, corps, entetes, statutAttendu, code] of cas) {
    const moteur = fauxMoteur(statutMoteur, corps, entetes);
    const rep = await gererOuvrir(requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution." }), {
      config,
      recuperer: moteur.recuperer,
      journal: journalMuet,
    });
    const texte = await rep.text();
    assert.equal(rep.status, statutAttendu, code);
    assert.equal(JSON.parse(texte).erreur.code, code);
    assert.doesNotMatch(texte, /Traceback|\/Users\//);
    if (code === "DEBIT_DEPASSE") {
      assert.equal(rep.headers.get("retry-after"), "12");
      assert.equal(JSON.parse(texte).erreur.reessayerDansSecondes, 12);
    }
  }
});

function fixtureErreur(code: string) {
  return { ok: false, erreur: { code, message: "…" } };
}

test("moteur injoignable ou trop lent : SERVICE_INDISPONIBLE, réessayable", async () => {
  const refuse = async () => {
    throw new TypeError("fetch failed");
  };
  const lent = (_: string, init: RequestInit) =>
    new Promise<Response>((_, rejeter) => {
      init.signal?.addEventListener("abort", () => rejeter(Object.assign(new Error("abort"), { name: "AbortError" })));
    });
  for (const recuperer of [refuse, lent]) {
    const rep = await gererSante(new Request("http://localhost:3000/api/sante"), {
      config: () => ({ ...CONFIG_TEST, delaiMs: 50 }),
      recuperer,
      journal: journalMuet,
    });
    assert.equal(rep.status, 503);
    const corps = await rep.json();
    assert.equal(corps.erreur.code, "SERVICE_INDISPONIBLE");
    assert.equal(corps.erreur.reessayable, true);
  }
});

test("configuration absente : le service refuse proprement, sans révéler la variable", async () => {
  const rep = await gererSante(new Request("http://localhost:3000/api/sante"), {
    config: () => {
      throw new ConfigurationInvalide("MONRECOURS_API_KEY est absente");
    },
    journal: journalMuet,
  });
  assert.equal(rep.status, 500);
  const texte = await rep.text();
  assert.equal(JSON.parse(texte).erreur.code, "CONFIGURATION");
  assert.doesNotMatch(texte, /MONRECOURS_/);
});
