import { test } from "node:test";
import assert from "node:assert/strict";
import { identifiantVisiteur, LimiteurVisiteurs } from "../../src/lib/server/limiteur";
import { gererOuvrir } from "../../src/lib/server/handlers";
import { CONFIG_TEST, fauxMoteur, fixture, requeteJson } from "../aides";

test("un visiteur est limité, un autre ne l'est pas ; la fenêtre se libère", () => {
  let t = 0;
  const l = new LimiteurVisiteurs(() => t);
  for (let i = 0; i < 3; i++) assert.equal(l.consommer("A", 3), 0);
  const attente = l.consommer("A", 3);
  assert.ok(attente >= 1 && attente <= 60);
  assert.equal(l.consommer("B", 3), 0, "un autre visiteur n'est pas pénalisé");
  t = 61_000;
  assert.equal(l.consommer("A", 3), 0, "la fenêtre glissante se libère");
});

test("identification : dernière valeur de X-Forwarded-For (ajoutée par le proxy)", () => {
  const r = (h: Record<string, string>) => new Request("http://x/", { headers: h });
  assert.equal(identifiantVisiteur(r({ "x-forwarded-for": "6.6.6.6, 41.202.1.2" })), "41.202.1.2");
  assert.equal(identifiantVisiteur(r({ "x-real-ip": "41.202.1.3" })), "41.202.1.3");
  assert.equal(identifiantVisiteur(r({})), "inconnu");
});

test("au-delà de la limite, /api/ouvrir répond 429 sans solliciter le moteur", async () => {
  const moteur = fauxMoteur(200, fixture("ouvrir_caution"));
  const limiteur = new LimiteurVisiteurs();
  const dep = { config: () => ({ ...CONFIG_TEST, debitVisiteur: 2 }), recuperer: moteur.recuperer, limiteur };
  const requete = () =>
    requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution." }, { "X-Forwarded-For": "41.202.1.9" });
  assert.equal((await gererOuvrir(requete(), dep)).status, 200);
  assert.equal((await gererOuvrir(requete(), dep)).status, 200);
  const refus = await gererOuvrir(requete(), dep);
  assert.equal(refus.status, 429);
  assert.ok(Number(refus.headers.get("retry-after")) >= 1);
  assert.equal((await refus.json()).erreur.code, "DEBIT_DEPASSE");
  assert.equal(moteur.appels.length, 2);
});
