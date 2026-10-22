import { test } from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { TableauDeBord, type DonneesTableauDeBord } from "../../src/components/admin/TableauDeBord";
import { assainirSante } from "../../src/lib/server/assainir";
import type { VueSante } from "../../src/lib/types";
import { fixture } from "../aides";

/**
 * L'administrateur doit voir, sans ambiguïté, que le fournisseur de langage est
 * hors service pour épuisement de crédits et que le service continue.
 */

function texteVisible(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x27;|&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ");
}

const SANTE: VueSante = assainirSante(fixture("sante").data);

function donnees(sante: VueSante | null): DonneesTableauDeBord {
  return {
    compte: { email: "admin@exemple.ci", role: "administrateur" },
    plateforme: { mode: "reel", moteur: "joignable", langageActif: false, versionInterface: "0.1.2" },
    sante,
    comptes: [{ email: "admin@exemple.ci", role: "administrateur" }],
    comptesIgnores: 0,
    audit: null,
    parametres: [{ libelle: "Clé d'accès au moteur", valeur: "Configurée" }],
  };
}

const INCIDENT = {
  statut: "CREDITS_EPUISES",
  ouvert: true,
  fournisseur: "deepseek",
  detecteLe: "2026-10-22T20:14:00",
  resoluLe: null,
  objet: "Crédits deepseek épuisés — Mon Recours CI",
  consequence: "Le moteur déterministe fonctionne en secours : les consultations restent traitées, sans compréhension assistée.",
  actionAttendue: "Vérifier le solde du fournisseur et rétablir le service.",
};

test("administration : l'épuisement des crédits est signalé explicitement", () => {
  const html = renderToStaticMarkup(
    <TableauDeBord donnees={donnees({ ...SANTE, incidentLangage: INCIDENT })} />,
  );
  const visible = texteVisible(html);
  assert.ok(visible.includes("DeepSeek indisponible — crédits épuisés."));
  assert.ok(visible.includes("Le moteur de secours fonctionne."));
  assert.ok(visible.includes("Vérifiez le solde du fournisseur."));
  assert.ok(visible.includes("Crédits deepseek épuisés — Mon Recours CI"));
  assert.ok(visible.includes("2026-10-22T20:14:00"));
  assert.ok(visible.includes("deepseek"));
  assert.match(html, /role="alert"/);
  assert.match(html, /data-incident="credits-epuises"/);
});

test("administration : aucune alerte quand le fournisseur fonctionne", () => {
  const html = renderToStaticMarkup(
    <TableauDeBord donnees={donnees({ ...SANTE, incidentLangage: null })} />,
  );
  assert.doesNotMatch(html, /data-incident="credits-epuises"/);
  assert.ok(!texteVisible(html).includes("crédits épuisés."));
});

test("administration : l'alerte ne contient ni clé ni donnée personnelle", () => {
  const html = renderToStaticMarkup(
    <TableauDeBord donnees={donnees({ ...SANTE, incidentLangage: INCIDENT })} />,
  );
  // On isole la zone d'alerte : la page affiche par ailleurs l'e-mail de
  // connexion de l'administrateur, ce qui est légitime.
  const zone = html.slice(html.indexOf("credits-epuises"), html.indexOf("admin__entete"));
  assert.ok(zone.length > 0, "zone d'alerte introuvable");
  assert.doesNotMatch(zone, /sk-[A-Za-z0-9]{8,}/);
  assert.doesNotMatch(zone, /MONRECOURS_LLM/);
  assert.doesNotMatch(zone, /@exemple\.ci/);
});

test("administration : aucun faux bouton de réactivation", () => {
  const html = renderToStaticMarkup(
    <TableauDeBord donnees={donnees({ ...SANTE, incidentLangage: INCIDENT })} />,
  );
  const zone = html.slice(html.indexOf("credits-epuises"), html.indexOf("admin__entete"));
  assert.doesNotMatch(zone, /<button/i, "un bouton inerte est proposé dans l'alerte");
});
