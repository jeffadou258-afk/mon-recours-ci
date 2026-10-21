import { test } from "node:test";
import assert from "node:assert/strict";
import { chmodSync, chownSync, mkdtempSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { hacherMotDePasse } from "../../src/lib/server/auth/motdepasse";
import { lireEtatAuth, TAILLE_MAX_FICHIER_COMPTES } from "../../src/lib/server/auth/comptes";
import { gererConnexion } from "../../src/lib/server/auth/handlers-auth";
import type { LigneAudit } from "../../src/lib/server/auth/audit";
import { LimiteurVisiteurs } from "../../src/lib/server/limiteur";

const SECRET = "f".repeat(40);

async function avecDossier(fn: (dossier: string, empreinte: string) => Promise<void> | void) {
  const dossier = mkdtempSync(join(tmpdir(), "mrci-comptes-"));
  try {
    await fn(dossier, await hacherMotDePasse("une phrase de passe solide"));
  } finally {
    rmSync(dossier, { recursive: true, force: true });
  }
}

function ecrire(chemin: string, contenu: string, mode = 0o600) {
  writeFileSync(chemin, contenu, { mode });
  chmodSync(chemin, mode); // indépendant de l'umask du processus de test
}

function raison(env: Record<string, string>): string {
  const etat = lireEtatAuth(env);
  assert.equal(etat.etat, "non_configure");
  return etat.etat === "non_configure" ? etat.raison : "";
}

test("fichier de comptes : lecture valide (0600 et 0400), entrées invalides écartées", async () => {
  await avecDossier((dossier, empreinte) => {
    const chemin = join(dossier, "comptes.json");
    const contenu = JSON.stringify([
      { email: "Admin@Exemple.ci", role: "administrateur", motDePasse: empreinte },
      { email: "x@exemple.ci", role: "superadmin", motDePasse: empreinte },
      { email: "y@exemple.ci", role: "lecteur", motDePasse: "en clair" },
    ]);
    for (const mode of [0o600, 0o400]) {
      ecrire(chemin, contenu, mode);
      const etat = lireEtatAuth({ MONRECOURS_SESSION_SECRET: SECRET, MONRECOURS_COMPTES_FICHIER: chemin });
      assert.equal(etat.etat, "actif", `mode ${mode.toString(8)}`);
      if (etat.etat === "actif") {
        assert.deepEqual(etat.comptes.map((c) => [c.email, c.role]), [["admin@exemple.ci", "administrateur"]]);
        assert.equal(etat.ignores, 2);
      }
      chmodSync(chemin, 0o600);
    }
  });
});

test("fichier de comptes : absent, relatif, JSON invalide, pas un tableau, vide → fermé", async () => {
  await avecDossier((dossier) => {
    const chemin = join(dossier, "comptes.json");
    const env = { MONRECOURS_SESSION_SECRET: SECRET, MONRECOURS_COMPTES_FICHIER: chemin };
    assert.match(raison(env), /introuvable/);
    assert.match(raison({ ...env, MONRECOURS_COMPTES_FICHIER: "comptes.json" }), /non absolu/);
    ecrire(chemin, "{pas du json");
    assert.match(raison(env), /JSON invalide/);
    ecrire(chemin, JSON.stringify({ email: "a@b.ci" }));
    assert.match(raison(env), /tableau/);
    ecrire(chemin, "[]");
    assert.match(raison(env), /aucun compte valide/);
  });
});

test("fichier de comptes : permissions trop larges, lien symbolique, dossier, taille → refusés", async () => {
  await avecDossier((dossier, empreinte) => {
    const chemin = join(dossier, "comptes.json");
    const contenu = JSON.stringify([{ email: "a@exemple.ci", role: "administrateur", motDePasse: empreinte }]);
    const env = { MONRECOURS_SESSION_SECRET: SECRET, MONRECOURS_COMPTES_FICHIER: chemin };
    for (const mode of [0o644, 0o640, 0o604, 0o660]) {
      ecrire(chemin, contenu, mode);
      assert.match(raison(env), /permissions .* trop larges/, `mode ${mode.toString(8)}`);
    }
    ecrire(chemin, contenu, 0o600);
    const lien = join(dossier, "lien.json");
    symlinkSync(chemin, lien);
    assert.match(raison({ ...env, MONRECOURS_COMPTES_FICHIER: lien }), /lien symbolique/);
    assert.match(raison({ ...env, MONRECOURS_COMPTES_FICHIER: dossier }), /pas un fichier ordinaire|permissions/);
    ecrire(chemin, " ".repeat(TAILLE_MAX_FICHIER_COMPTES + 1), 0o600);
    assert.match(raison(env), /trop volumineux/);
  });
});

test("fichier de comptes : propriétaire différent de l'utilisateur du service → refusé", { skip: process.getuid?.() !== 0 && "exige root pour changer le propriétaire" }, async () => {
  await avecDossier((dossier, empreinte) => {
    const chemin = join(dossier, "comptes.json");
    ecrire(chemin, JSON.stringify([{ email: "a@exemple.ci", role: "administrateur", motDePasse: empreinte }]));
    chownSync(chemin, 65534, 65534);
    assert.match(raison({ MONRECOURS_SESSION_SECRET: SECRET, MONRECOURS_COMPTES_FICHIER: chemin }), /appartenir/);
  });
});

test("priorité : les deux sources définies → configuration ambiguë, administration fermée", async () => {
  await avecDossier((dossier, empreinte) => {
    const chemin = join(dossier, "comptes.json");
    const liste = JSON.stringify([{ email: "a@exemple.ci", role: "administrateur", motDePasse: empreinte }]);
    ecrire(chemin, liste);
    const r = raison({ MONRECOURS_SESSION_SECRET: SECRET, MONRECOURS_COMPTES_FICHIER: chemin, MONRECOURS_COMPTES: liste });
    assert.match(r, /ambiguë/);
    // Une seule source à la fois : chacune fonctionne.
    assert.equal(lireEtatAuth({ MONRECOURS_SESSION_SECRET: SECRET, MONRECOURS_COMPTES_FICHIER: chemin }).etat, "actif");
    assert.equal(lireEtatAuth({ MONRECOURS_SESSION_SECRET: SECRET, MONRECOURS_COMPTES: liste }).etat, "actif");
  });
});

test("fichier de comptes : retirer un compte du fichier prend effet sans redémarrage", async () => {
  await avecDossier((dossier, empreinte) => {
    const chemin = join(dossier, "comptes.json");
    const env = { MONRECOURS_SESSION_SECRET: SECRET, MONRECOURS_COMPTES_FICHIER: chemin };
    ecrire(chemin, JSON.stringify([
      { email: "a@exemple.ci", role: "administrateur", motDePasse: empreinte },
      { email: "b@exemple.ci", role: "administrateur", motDePasse: empreinte },
    ]));
    const avant = lireEtatAuth(env);
    ecrire(chemin, JSON.stringify([{ email: "a@exemple.ci", role: "administrateur", motDePasse: empreinte }]));
    const apres = lireEtatAuth(env);
    assert.equal(avant.etat === "actif" && avant.comptes.length, 2);
    assert.equal(apres.etat === "actif" && apres.comptes.length, 1);
  });
});

test("fermeture journalisée avec sa raison, sans adresse, empreinte ni contenu du fichier", async () => {
  await avecDossier(async (dossier, empreinte) => {
    const chemin = join(dossier, "comptes.json");
    ecrire(chemin, JSON.stringify([{ email: "secret-admin@exemple.ci", role: "administrateur", motDePasse: empreinte }]), 0o644);
    const journal: LigneAudit[] = [];
    const r = await gererConnexion(
      new Request("http://localhost/api/connexion", {
        method: "POST",
        headers: { "content-type": "application/json", origin: "http://localhost", host: "localhost" },
        body: JSON.stringify({ email: "secret-admin@exemple.ci", motDePasse: "x" }),
      }),
      {
        env: { MONRECOURS_SESSION_SECRET: SECRET, MONRECOURS_COMPTES_FICHIER: chemin },
        audit: async (l) => {
          journal.push(l);
        },
        limiteurVisiteurs: new LimiteurVisiteurs(),
        limiteurAdresses: new LimiteurVisiteurs(),
      },
    );
    assert.equal(r.status, 503);
    const corps = JSON.stringify(await r.json());
    assert.doesNotMatch(corps, /permissions|0600/, "la raison technique n'est pas renvoyée au visiteur");
    assert.deepEqual(journal.map((l) => l.evenement), ["authentification_fermee"]);
    const brut = JSON.stringify(journal);
    assert.match(brut, /permissions du fichier de comptes trop larges/);
    assert.ok(!brut.includes("secret-admin") && !brut.includes("scrypt$") && !brut.includes(SECRET));
  });
});
