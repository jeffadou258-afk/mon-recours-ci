/**
 * Parcours d'aiguillage côté serveur : de l'ouverture au choix, puis à la
 * procédure retenue. Le moteur est simulé — ce sont les contrôles du serveur web
 * qu'on vérifie ici (transmission, validation, refus), pas le moteur Python.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { gererOuvrir, gererRepondre } from "../../src/lib/server/handlers";
import type { ConfigServeur } from "../../src/lib/server/config";
import type { Recuperateur } from "../../src/lib/server/moteur";
import { requeteJson } from "../aides";

const CONFIG: ConfigServeur = {
  urlMoteur: "http://127.0.0.1:8765",
  cleMoteur: "cle-de-test-tres-secrete-0123456789",
  secretSession: "secret-de-session-de-test-0123456789-abcdef",
  delaiMs: 2000,
  production: false,
  debitVisiteur: 1000,
  demo: false,
};

/** Transport en file : chaque appel consomme la réponse suivante. */
function fileDattente(reponses: unknown[]) {
  const appels: { url: string; corps: string }[] = [];
  const recuperer: Recuperateur = async (url, init) => {
    appels.push({ url, corps: String(init.body ?? "") });
    const corps = reponses.length > 1 ? reponses.shift() : reponses[0];
    return new Response(JSON.stringify(corps), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  };
  return { recuperer, appels };
}

const AIGUILLAGE = {
  ok: true,
  data: {
    etape: "aiguillage",
    dossier_id: "DOSSIER-AIGUILLAGE",
    situation: "logement_reprise_par_le_bailleur",
    question: "Parmi ces situations, laquelle correspond à la vôtre ?",
    message: "Plusieurs situations peuvent correspondre à ce que vous décrivez.",
    option_aucune: "Aucune de ces situations ne correspond à la mienne",
    avertissement: "Je suis un service d'information juridique, pas un avocat.",
    options: [
      { cle: "LOGEME_440", libelle: "Le propriétaire veut reprendre le logement",
        titre: "Congé donné par le bailleur", article: "440", numero_texte: "2019-576",
        etat_verification: "VERIFIE" },
      { cle: "LOGEME_445", libelle: "Le propriétaire veut me faire partir",
        titre: "Expulsion forcée", article: "445", numero_texte: "2019-576",
        etat_verification: "VERIFIE" },
    ],
  },
};

function cookieDe(reponse: Response): string {
  return (reponse.headers.get("set-cookie") ?? "").split(";")[0] ?? "";
}

async function ouvrir(recuperer: Recuperateur) {
  const reponse = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Mon propriétaire veut récupérer son appartement." }),
    { config: () => CONFIG, recuperer },
  );
  const { data } = await reponse.json();
  return { reponse, data, cookie: cookieDe(reponse) };
}

test("ouverture ambiguë : le serveur restitue l'aiguillage, sans analyse", async () => {
  const { recuperer } = fileDattente([AIGUILLAGE]);
  const { reponse, data } = await ouvrir(recuperer);
  assert.equal(reponse.status, 200);
  assert.equal(data.etape, "aiguillage");
  assert.equal(data.options.length, 2);
  assert.ok(data.optionAucune.length > 0);
  assert.equal(data.reponse, undefined, "une réponse a été produite avant le choix");
  assert.equal(data.statut_reponse, undefined);
});

test("le choix est transmis au moteur tel quel, et la procédure retenue revient", async () => {
  const { recuperer, appels } = fileDattente([
    AIGUILLAGE,
    {
      ok: true,
      data: {
        etape: "clarification",
        dossier_id: "DOSSIER-AIGUILLAGE",
        tour: 1,
        fiches_identifiees: [
          { titre: "Congé donné par le bailleur", article: "440", numero_texte: "2019-576",
            etat_verification: "VERIFIE" },
        ],
        questions: [],
        avertissement: "Je suis un service d'information juridique, pas un avocat.",
      },
    },
  ]);
  const { cookie } = await ouvrir(recuperer);
  const reponse = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { aiguillage: "LOGEME_440" } }, { cookie }),
    { config: () => CONFIG, recuperer },
  );
  const { data } = await reponse.json();
  assert.equal(reponse.status, 200);
  assert.equal(data.etape, "clarification");
  assert.deepEqual((data.fiches ?? []).map((f: { article: string }) => f.article), ["440"]);
  // Le choix a bien été transmis au moteur, sous la clé attendue.
  assert.match(appels[1]!.corps, /"aiguillage"\s*:\s*"LOGEME_440"/);
});

test("« aucune situation » : aucune conclusion juridique non étayée", async () => {
  const { recuperer } = fileDattente([
    AIGUILLAGE,
    {
      ok: true,
      data: {
        etape: "reponse",
        reponse: {
          statut_reponse: "CONCLUSION_IMPOSSIBLE",
          message: "Aucune des situations proposées ne correspond à la vôtre.",
          avertissement: "Je suis un service d'information juridique, pas un avocat.",
        },
      },
    },
  ]);
  const { cookie } = await ouvrir(recuperer);
  const reponse = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { aiguillage: "aucune" } }, { cookie }),
    { config: () => CONFIG, recuperer },
  );
  const { data } = await reponse.json();
  assert.equal(data.etape, "reponse");
  assert.equal(data.statut, "CONCLUSION_IMPOSSIBLE");
  assert.equal(data.droit?.length ?? 0, 0, "une analyse a été servie sans source");
});

test("sélection invalide : le moteur repose la question, sans conclusion", async () => {
  const { recuperer } = fileDattente([
    AIGUILLAGE,
    {
      ok: true,
      data: { ...AIGUILLAGE.data, erreur_selection: "Choisissez l'une des situations proposées." },
    },
  ]);
  const { cookie } = await ouvrir(recuperer);
  const reponse = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { aiguillage: "LOGEME_999" } }, { cookie }),
    { config: () => CONFIG, recuperer },
  );
  const { data } = await reponse.json();
  assert.equal(data.etape, "aiguillage");
  assert.ok(data.erreurSelection);
  assert.equal(data.reponse, undefined);
});

test("réponse mal formée : refusée avant tout appel au moteur", async () => {
  const { recuperer, appels } = fileDattente([AIGUILLAGE]);
  const { cookie } = await ouvrir(recuperer);
  const avant = appels.length;
  const reponse = await gererRepondre(
    requeteJson("/api/repondre", { reponses: "LOGEME_440" }, { cookie }),
    { config: () => CONFIG, recuperer },
  );
  assert.equal(reponse.status, 400);
  assert.equal(appels.length, avant, "le moteur a été appelé avec une charge invalide");
});

test("clé de réponse hors format : refusée", async () => {
  const { recuperer, appels } = fileDattente([AIGUILLAGE]);
  const { cookie } = await ouvrir(recuperer);
  const avant = appels.length;
  const reponse = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { "aiguillage!": "LOGEME_440" } }, { cookie }),
    { config: () => CONFIG, recuperer },
  );
  assert.equal(reponse.status, 400);
  assert.equal(appels.length, avant);
});

test("sans cookie de dossier, aucune sélection n'est acceptée", async () => {
  const { recuperer, appels } = fileDattente([AIGUILLAGE]);
  await ouvrir(recuperer);
  const avant = appels.length;
  const reponse = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { aiguillage: "LOGEME_440" } }),
    { config: () => CONFIG, recuperer },
  );
  assert.equal(reponse.status, 409);
  assert.equal(appels.length, avant);
});
