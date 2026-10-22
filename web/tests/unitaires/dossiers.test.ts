/**
 * Sécurité de l'accès aux courriers PDF.
 *
 * L'interface lit un fichier produit par le moteur : c'est le seul endroit du
 * projet où un chemin du système de fichiers est manipulé. Ces tests vérifient
 * les quatre protections décrites dans `src/lib/server/dossiers.ts` :
 *
 *   1. identifiant au format verrouillé (aucun séparateur, aucune traversée) ;
 *   2. selection du fichier par motif, jamais par un nom fourni par l'appelant ;
 *   3. confinement réel (`realpath`), y compris contre un lien symbolique ;
 *   4. dernier courrier retenu, pas un fichier arbitraire du dossier.
 */

import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdir, mkdtemp, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import {
  ConsultationExpiree,
  CourrierIntrouvable,
  dernierCourrierPdf,
  dureeConservationHeures,
  echeanceConsultation,
  racineDossiers,
} from "../../src/lib/server/dossiers";

const ID = "web-11111111-2222-4333-8444-555555555555";

async function bac(): Promise<string> {
  const racine = await mkdtemp(join(tmpdir(), "mrci-dossiers-"));
  process.env.MONRECOURS_DOSSIERS = racine;
  return racine;
}

async function ecrire(racine: string, dossier: string, nom: string, contenu = "%PDF-1.4 test"): Promise<string> {
  const repertoire = join(racine, dossier, "BROUILLONS");
  await mkdir(repertoire, { recursive: true });
  const chemin = join(repertoire, nom);
  await writeFile(chemin, contenu);
  return chemin;
}

test("racine : la variable d'environnement est respectée", async () => {
  const racine = await bac();
  assert.equal(racineDossiers(), racine);
  await rm(racine, { recursive: true, force: true });
});

test("le dernier courrier est retenu (horodatage dans le nom)", async () => {
  const racine = await bac();
  await ecrire(racine, ID, "20260101-090000_reclamation.pdf", "%PDF-1.4 ancien");
  await ecrire(racine, ID, "20260102-090000_reclamation.pdf", "%PDF-1.4 recent");
  const courrier = await dernierCourrierPdf(ID);
  assert.match(courrier.chemin, /20260102-090000_reclamation\.pdf$/);
  assert.equal(courrier.nom, "courrier-mon-recours-ci.pdf");
  assert.ok(courrier.octets > 0);
  await rm(racine, { recursive: true, force: true });
});

test("les fichiers hors motif sont ignorés", async () => {
  const racine = await bac();
  await ecrire(racine, ID, "secret.pdf");
  await ecrire(racine, ID, "20260101-090000_reclamation.pdf");
  const courrier = await dernierCourrierPdf(ID);
  assert.match(courrier.chemin, /_reclamation\.pdf$/);
  await rm(racine, { recursive: true, force: true });
});

test("aucun courrier : refus explicite, pas un chemin vide", async () => {
  const racine = await bac();
  await mkdir(join(racine, ID, "BROUILLONS"), { recursive: true });
  await assert.rejects(() => dernierCourrierPdf(ID), CourrierIntrouvable);
  await rm(racine, { recursive: true, force: true });
});

test("traversée de chemin refusée avant tout accès disque", async () => {
  await bac();
  for (const mauvais of ["../etc", "web-../../etc", "/etc/passwd", "web-x", "", "..", "web-11111111-2222-4333-8444-55555555555/"]) {
    await assert.rejects(() => dernierCourrierPdf(mauvais), CourrierIntrouvable, mauvais);
  }
});

test("un lien symbolique qui sort du dossier est refusé", async () => {
  const racine = await bac();
  const dehors = await mkdtemp(join(tmpdir(), "mrci-dehors-"));
  const cible = join(dehors, "ailleurs.pdf");
  await writeFile(cible, "%PDF-1.4 hors dossier");
  const repertoire = join(racine, ID, "BROUILLONS");
  await mkdir(repertoire, { recursive: true });
  await symlink(cible, join(repertoire, "20260101-090000_reclamation.pdf"));

  await assert.rejects(() => dernierCourrierPdf(ID), CourrierIntrouvable);

  await rm(racine, { recursive: true, force: true });
  await rm(dehors, { recursive: true, force: true });
});

test("deux dossiers ne se mélangent pas", async () => {
  const racine = await bac();
  const autre = "web-99999999-8888-4777-8666-555555555555";
  await ecrire(racine, autre, "20260101-090000_reclamation.pdf", "%PDF-1.4 autre");
  await assert.rejects(() => dernierCourrierPdf(ID), CourrierIntrouvable,
    "le dossier demandé ne doit pas voir le courrier d'un autre");
  await rm(racine, { recursive: true, force: true });
});

test("un dossier inconnu ne produit aucune erreur système visible", async () => {
  const racine = await bac();
  await assert.rejects(
    () => dernierCourrierPdf("web-22222222-3333-4444-8555-666666666666"),
    (erreur: Error) => erreur instanceof CourrierIntrouvable && !/ENOENT|EACCES/.test(erreur.message),
  );
  await rm(racine, { recursive: true, force: true });
});

// --- Conservation temporaire (24 heures) ------------------------------------

async function conservation(racine: string, dossier: string, expireDansMs: number): Promise<void> {
  const maintenant = Date.now();
  await mkdir(join(racine, dossier), { recursive: true });
  await writeFile(
    join(racine, dossier, "CONSERVATION.json"),
    JSON.stringify({
      version: 1,
      cree_le: new Date(maintenant + expireDansMs - 24 * 3600 * 1000).toISOString(),
      expire_le: new Date(maintenant + expireDansMs).toISOString(),
      duree_heures: 24,
    }),
  );
}

test("conservation : avant l'échéance, le courrier est servi", async () => {
  const racine = await bac();
  await ecrire(racine, ID, "20261022-080000_reclamation.pdf");
  await conservation(racine, ID, 60_000);
  const courrier = await dernierCourrierPdf(ID);
  assert.ok(courrier.octets > 0);
  await rm(racine, { recursive: true, force: true });
});

test("conservation : après l'échéance, le courrier n'est plus servi, même avant la purge", async () => {
  const racine = await bac();
  await ecrire(racine, ID, "20261022-080000_reclamation.pdf");
  await conservation(racine, ID, -1);
  await assert.rejects(() => dernierCourrierPdf(ID), (e: Error) => e instanceof ConsultationExpiree);
  await rm(racine, { recursive: true, force: true });
});

test("conservation : une consultation expirée n'empêche pas une autre, non expirée", async () => {
  const racine = await bac();
  const autre = "web-99999999-8888-4777-8666-555555555555";
  await ecrire(racine, ID, "20261022-080000_reclamation.pdf");
  await ecrire(racine, autre, "20261022-090000_reclamation.pdf");
  await conservation(racine, ID, -1);
  await conservation(racine, autre, 3600_000);
  await assert.rejects(() => dernierCourrierPdf(ID), (e: Error) => e instanceof ConsultationExpiree);
  assert.ok((await dernierCourrierPdf(autre)).octets > 0);
  await rm(racine, { recursive: true, force: true });
});

test("conservation : repli sur ouvert_le pour un dossier antérieur, sans CONSERVATION.json", async () => {
  const racine = await bac();
  await ecrire(racine, ID, "20261022-080000_reclamation.pdf");
  const ouvert = new Date(Date.now() - 25 * 3600 * 1000).toISOString().replace(/\.\d{3}Z$/, "+00:00");
  await writeFile(join(racine, ID, "DOSSIER_EN_COURS.json"), JSON.stringify({ ouvert_le: ouvert }));
  const echeance = await echeanceConsultation(ID, 24);
  assert.ok(echeance !== null && echeance < Date.now());
  await assert.rejects(() => dernierCourrierPdf(ID), (e: Error) => e instanceof ConsultationExpiree);
  await rm(racine, { recursive: true, force: true });
});

test("conservation : un dossier absent n'a pas d'échéance (rien n'est recréé)", async () => {
  const racine = await bac();
  assert.equal(await echeanceConsultation(ID), null);
  await rm(racine, { recursive: true, force: true });
});

test("conservation : durée configurable, valeur invalide refusée", () => {
  assert.equal(dureeConservationHeures({}), 24);
  assert.equal(dureeConservationHeures({ MONRECOURS_CONSERVATION_HEURES: "48" }), 48);
  for (const brut of ["0", "-1", "abc", "1.5"]) {
    assert.throws(() => dureeConservationHeures({ MONRECOURS_CONSERVATION_HEURES: brut }));
  }
});
