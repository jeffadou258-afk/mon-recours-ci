import { test } from "node:test";
import assert from "node:assert/strict";
import { decisionVerificationSolde } from "../../src/lib/server/solde";

/**
 * Qui peut déclencher un appel au fournisseur ? Le refus doit être la règle
 * par défaut : sans session administrateur valide, aucune vérification.
 */

const ENV_FERME = { MONRECOURS_AUTH: "desactive" } as Record<string, string>;

test("sans cookie, la vérification est refusée", () => {
  const decision = decisionVerificationSolde(null, ENV_FERME);
  assert.equal(decision.autorise, false);
});

test("un cookie forgé ne donne aucun droit", () => {
  const decision = decisionVerificationSolde("mrci_session=forgé-au-hasard", ENV_FERME);
  assert.equal(decision.autorise, false);
});

test("un cookie vide ne donne aucun droit", () => {
  assert.equal(decisionVerificationSolde("", ENV_FERME).autorise, false);
});

test("un motif de refus est toujours renseigné", () => {
  const decision = decisionVerificationSolde(null, ENV_FERME);
  assert.equal(decision.autorise, false);
  if (!decision.autorise) {
    assert.ok(["anonyme", "refuse", "ferme"].includes(decision.motif));
  }
});
