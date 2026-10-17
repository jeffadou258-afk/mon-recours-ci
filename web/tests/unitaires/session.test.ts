import { test } from "node:test";
import assert from "node:assert/strict";
import {
  deballer,
  emballer,
  enteteCookie,
  lireCookie,
  nouvelIdentifiant,
} from "../../src/lib/server/session";

const SECRET = "secret-de-session-de-test-0123456789-abcdef";

test("un identifiant est aléatoire et accepté par le moteur (pas de séparateur de chemin)", () => {
  const a = nouvelIdentifiant();
  const b = nouvelIdentifiant();
  assert.notEqual(a, b);
  assert.match(a, /^web-[0-9a-f-]{36}$/);
  assert.ok(!/[\\/]|\.\./.test(a));
});

test("un cookie signé est relu, un cookie altéré ou forgé est rejeté", () => {
  const id = nouvelIdentifiant();
  const cookie = emballer(id, SECRET);
  assert.equal(deballer(cookie, SECRET), id);

  const autreId = nouvelIdentifiant();
  const signature = cookie.slice(cookie.lastIndexOf(".") + 1);
  assert.equal(deballer(`${autreId}.${signature}`, SECRET), null, "signature réutilisée sur un autre dossier");
  assert.equal(deballer(emballer(id, "un-autre-secret-de-trente-deux-car"), SECRET), null);
  assert.equal(deballer(`${id}.`, SECRET), null);
  assert.equal(deballer(id, SECRET), null);
  assert.equal(deballer("AUDIT1.abc", SECRET), null, "identifiant non généré par l'interface");
  assert.equal(deballer(null, SECRET), null);
});

test("le cookie est HttpOnly, SameSite=Strict, limité à /api", () => {
  const entete = enteteCookie("x.y", true);
  for (const attendu of ["HttpOnly", "SameSite=Strict", "Path=/api", "Secure", "Max-Age=7200"]) {
    assert.ok(entete.includes(attendu), `${attendu} absent de ${entete}`);
  }
  assert.ok(!enteteCookie("x.y", false).includes("Secure"));
});

test("lecture de l'en-tête Cookie", () => {
  assert.equal(lireCookie("a=1; mrci_dossier=abc.def; b=2"), "abc.def");
  assert.equal(lireCookie("a=1"), null);
  assert.equal(lireCookie(null), null);
});
