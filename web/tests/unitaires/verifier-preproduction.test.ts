/**
 * Contrôle « empreintes scrypt » du script de préproduction.
 *
 * Le script `web/deploiement/verifier-preproduction.sh` est la porte d'entrée de
 * l'administration : il doit refuser un fichier de comptes contenant un mot de
 * passe en clair. Sa première version se contentait de vérifier qu'AU MOINS une
 * empreinte `scrypt$` existait — un fichier mixte dont le mot de passe en clair
 * commençait par « s » passait donc pour conforme.
 *
 * Ce test exécute le script réel sur des fichiers inertes (répertoire temporaire,
 * supprimé après), sans serveur et sans créer de compte utilisable : les adresses
 * sont en `.invalid` et les empreintes sont fabriquées. Il vérifie uniquement la
 * ligne de verdict sur le fichier de comptes.
 */

import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { chmodSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { after, before, describe, it } from "node:test";

const SCRIPT = resolve(__dirname, "../../deploiement/verifier-preproduction.sh");
// Le script exige une base HTTPS ; ce port local n'écoute pas : les contrôles
// réseau échouent proprement, seuls les contrôles de fichiers nous intéressent.
const BASE = "https://127.0.0.1:9";
const EMPREINTE =
  "scrypt$16384$8$1$c2VsZWN0ZWQxMjM0NTY3OA$" +
  "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA";

let dossier: string;

function executer(comptes: string): string {
  const env = join(dossier, "env");
  const fichier = join(dossier, "comptes.json");
  writeFileSync(fichier, comptes, { mode: 0o600 });
  chmodSync(fichier, 0o600);
  writeFileSync(
    env,
    [
      `MONRECOURS_SESSION_SECRET=${"x".repeat(48)}`,
      `MONRECOURS_COMPTES_FICHIER=${fichier}`,
      "",
    ].join("\n"),
    { mode: 0o600 },
  );
  try {
    return execFileSync("bash", [SCRIPT, BASE], {
      encoding: "utf8",
      env: { ...process.env, MONRECOURS_FICHIER_ENV: env },
      timeout: 60000,
    });
  } catch (erreur) {
    // Code de sortie 1 attendu quand au moins un contrôle échoue.
    const sortie = (erreur as { stdout?: string }).stdout;
    return sortie ?? "";
  }
}

function verdict(sortie: string): string {
  const ligne = sortie
    .split("\n")
    .find((l) => l.includes("fichier de comptes") && (l.includes("empreinte") || l.includes("hach")));
  return ligne ?? "";
}

describe("script de préproduction — empreintes de mots de passe", () => {
  before(() => {
    dossier = mkdtempSync(join(tmpdir(), "verif-preprod-"));
  });

  after(() => {
    rmSync(dossier, { recursive: true, force: true });
  });

  it("accepte un fichier où toutes les empreintes sont scrypt", () => {
    const sortie = executer(
      JSON.stringify([
        { email: "a@exemple.invalid", role: "administrateur", motDePasse: EMPREINTE },
        { email: "b@exemple.invalid", role: "lecteur", motDePasse: EMPREINTE },
      ]),
    );
    assert.match(verdict(sortie), /empreinte/);
    assert.doesNotMatch(verdict(sortie), /ÉCHEC/);
    assert.doesNotMatch(verdict(sortie), /non hach/);
  });

  it("refuse un mot de passe en clair commençant par « s »", () => {
    // C'est exactement le cas qui passait avant la correction.
    const sortie = executer(
      JSON.stringify([
        { email: "a@exemple.invalid", role: "administrateur", motDePasse: EMPREINTE },
        { email: "b@exemple.invalid", role: "lecteur", motDePasse: "secretEnClair123" },
      ]),
    );
    assert.match(verdict(sortie), /ÉCHEC/);
    assert.match(verdict(sortie), /1 mot\(s\) de passe non hachés/);
  });

  it("refuse un fichier sans aucune empreinte", () => {
    const sortie = executer(JSON.stringify([]));
    assert.match(verdict(sortie), /ÉCHEC/);
  });
});
