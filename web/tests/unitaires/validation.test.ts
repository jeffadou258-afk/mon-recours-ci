import { test } from "node:test";
import assert from "node:assert/strict";
import { LONGUEUR_MAX_DEMANDE, LONGUEUR_MAX_REPONSE, validerDemande, validerReponses } from "../../src/lib/validation";

test("une demande normale est acceptée et nettoyée", () => {
  const r = validerDemande("  Mon bailleur garde ma caution.  ");
  assert.deepEqual(r, { ok: true, valeur: "Mon bailleur garde ma caution." });
});

test("les entrées malformées sont refusées avec un message en français", () => {
  for (const entree of [undefined, null, 42, {}, [], "", "   ", "court"]) {
    const r = validerDemande(entree);
    assert.equal(r.ok, false, `entrée acceptée à tort : ${JSON.stringify(entree)}`);
    if (!r.ok) assert.match(r.message, /[a-zé]/);
  }
});

test("la limite de longueur du moteur (4000) est respectée", () => {
  assert.equal(validerDemande("a".repeat(LONGUEUR_MAX_DEMANDE)).ok, true);
  assert.equal(validerDemande("a".repeat(LONGUEUR_MAX_DEMANDE + 1)).ok, false);
});

test("les caractères de contrôle et l'octet nul sont retirés", () => {
  const r = validerDemande("Mon bailleur\u0000 garde\u0007 ma caution");
  assert.deepEqual(r, { ok: true, valeur: "Mon bailleur garde ma caution" });
});

test("réponses : « je ne sais pas » devient null, les clés exotiques sont refusées", () => {
  assert.deepEqual(validerReponses({ logement: "oui", autre: null, vide: "  " }), {
    ok: true,
    valeur: { logement: "oui", autre: null, vide: null },
  });
  assert.equal(validerReponses({ "../x": "oui" }).ok, false);
  assert.equal(validerReponses({ __proto__x: "oui", "a b": "x" }).ok, false);
  assert.equal(validerReponses({ logement: 3 }).ok, false);
  assert.equal(validerReponses(["oui"]).ok, false);
  assert.equal(validerReponses("oui").ok, false);
  assert.equal(validerReponses({ logement: "x".repeat(LONGUEUR_MAX_REPONSE + 1) }).ok, false);
  const trop = Object.fromEntries(Array.from({ length: 21 }, (_, i) => [`q${i}`, "oui"]));
  assert.equal(validerReponses(trop).ok, false);
});
