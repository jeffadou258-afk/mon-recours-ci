/**
 * Mode démonstration — la Preview publique doit fonctionner sans moteur.
 *
 * Ce que ces tests garantissent :
 *   1. le mode n'est actif que sur `MONRECOURS_MODE=demo` (jamais par défaut) ;
 *   2. les réponses ont la même forme que celles du vrai moteur, donc les
 *      gestionnaires et l'interface ne voient aucune différence ;
 *   3. **aucun transport n'est appelé** : un `fetch` qui lèverait une erreur
 *      n'est jamais atteint ;
 *   4. aucune charge ne contient de chemin du système de fichiers ;
 *   5. la configuration de démo n'exige pas de clé d'API, mais exige toujours
 *      le secret de session (le cookie signé continue de protéger l'accès).
 */

import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { estModeDemo, reponseDemo, PDF_DEMONSTRATION } from "../../src/lib/server/demo";
import { appelerMoteur } from "../../src/lib/server/moteur";
import { lireConfig, ConfigurationInvalide } from "../../src/lib/server/config";

const CONFIG_DEMO = lireConfig({
  MONRECOURS_MODE: "demo",
  MONRECOURS_SESSION_SECRET: "secret-de-session-de-demonstration-0123456789",
});

function sansCheminAbsolu(valeur: unknown): boolean {
  const texte = JSON.stringify(valeur);
  return !texte.includes("/Users/") && !texte.includes("DOSSIERS/");
}

/** Charge d'une réponse de démonstration, avec le type affiné. */
function charge(route: Parameters<typeof reponseDemo>[0], corps?: Record<string, unknown>) {
  const reponse = reponseDemo(route, corps);
  if (!reponse.joignable) throw new Error("une réponse de démonstration est toujours joignable");
  return (reponse.corps as { data: Record<string, any> }).data;
}

describe("mode démonstration", () => {
  it("n'est actif que sur la valeur exacte « demo »", () => {
    assert.equal(estModeDemo({ MONRECOURS_MODE: "demo" }), true);
    for (const valeur of ["", "DEMO", "demoo", "production", undefined]) {
      assert.equal(estModeDemo(valeur === undefined ? {} : { MONRECOURS_MODE: valeur }), false);
    }
  });

  it("la configuration de démo ne demande pas de clé d'API", () => {
    assert.equal(CONFIG_DEMO.demo, true);
    assert.equal(CONFIG_DEMO.cleMoteur, "");
  });

  it("le secret de session reste obligatoire en démo", () => {
    assert.throws(
      () => lireConfig({ MONRECOURS_MODE: "demo" }),
      (erreur: unknown) => erreur instanceof ConfigurationInvalide,
    );
  });

  it("n'appelle aucun transport : un fetch qui échoue n'est jamais atteint", async () => {
    const interdit = () => {
      throw new Error("le mode démonstration ne doit joindre aucun moteur");
    };
    const reponse = await appelerMoteur(CONFIG_DEMO, "/ouvrir", { dossier_id: "DEMO-1" }, interdit);
    assert.equal(reponse.joignable, true);
    assert.equal(reponse.statut, 200);
  });

  it("renvoie une ouverture de la même forme que le moteur", async () => {
    const reponse = await appelerMoteur(CONFIG_DEMO, "/ouvrir", { dossier_id: "DEMO-1" });
    assert.ok(reponse.joignable);
    const data = (reponse.corps as { data: Record<string, unknown> }).data;
    assert.equal(data.etape, "clarification");
    assert.ok(Array.isArray(data.questions));
    assert.ok(Array.isArray(data.fiches_identifiees));
  });

  it("renvoie une conclusion analysée, avec ses sections", async () => {
    const reponse = await appelerMoteur(CONFIG_DEMO, "/repondre", { dossier_id: "DEMO-1" });
    if (!reponse.joignable) throw new Error("réponse attendue joignable");
    const data = (reponse.corps as { data: Record<string, any> }).data;
    assert.equal(data.etape, "reponse");
    assert.equal(data.reponse.statut_reponse, "ANALYSE_CONFORME");
    assert.ok(data.reponse.sections["2_droit"].length > 0);
  });

  it("reprend l'identifiant de dossier demandé, sans le figer", async () => {
    const reponse = await appelerMoteur(CONFIG_DEMO, "/repondre", { dossier_id: "AUTRE-42" });
    const texte = JSON.stringify(reponse);
    assert.ok(texte.includes("AUTRE-42"));
    assert.ok(!texte.includes("__DOSSIER__"));
  });

  it("aucune charge ne contient de chemin du système de fichiers", () => {
    for (const route of ["/sante", "/ouvrir", "/repondre", "/courrier", "/supprimer"] as const) {
      const reponse = reponseDemo(route, { dossier_id: "DEMO-1" });
      assert.ok(sansCheminAbsolu(reponse), `chemin détecté dans ${route}`);
    }
  });

  it("la suppression répond par un succès explicite", () => {
    assert.equal(charge("/supprimer").supprime, true);
  });

  it("le PDF de démonstration est un fichier statique", () => {
    assert.match(PDF_DEMONSTRATION, /^demo\/[a-z0-9-]+\.pdf$/);
    assert.ok(!PDF_DEMONSTRATION.includes(".."));
  });
});
