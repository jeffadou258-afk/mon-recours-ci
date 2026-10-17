import { test } from "node:test";
import assert from "node:assert/strict";
import { ConfigurationInvalide, lireConfig } from "../../src/lib/server/config";

const BASE = {
  MONRECOURS_API_KEY: "cle-de-test-0123456789",
  MONRECOURS_SESSION_SECRET: "secret-de-session-de-test-0123456789-abc",
};

test("configuration minimale valide", () => {
  const c = lireConfig(BASE);
  assert.equal(c.urlMoteur, "http://127.0.0.1:8765");
  assert.equal(c.delaiMs, 15000);
});

test("aucune clé par défaut : refus explicite", () => {
  assert.throws(() => lireConfig({}), ConfigurationInvalide);
  assert.throws(() => lireConfig({ ...BASE, MONRECOURS_API_KEY: "courte" }), ConfigurationInvalide);
  assert.throws(() => lireConfig({ ...BASE, MONRECOURS_SESSION_SECRET: "court" }), ConfigurationInvalide);
});

test("la clé n'est jamais envoyée en clair vers un hôte distant", () => {
  assert.throws(
    () => lireConfig({ ...BASE, MONRECOURS_API_URL: "http://moteur.exemple.ci:8765" }),
    ConfigurationInvalide,
  );
  assert.doesNotThrow(() => lireConfig({ ...BASE, MONRECOURS_API_URL: "https://moteur.exemple.ci" }));
  assert.throws(() => lireConfig({ ...BASE, MONRECOURS_API_URL: "ftp://127.0.0.1" }), ConfigurationInvalide);
});
