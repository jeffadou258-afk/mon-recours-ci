/**
 * Accueil vivant et consultation interactive : ce que le rendu serveur garantit
 * (contenu complet sans JavaScript, chiffres réels, rien d'inventé).
 */
import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { renderToStaticMarkup } from "react-dom/server";
import { Accueil } from "../../src/components/Accueil";
import { Parcours, SITUATIONS } from "../../src/components/Parcours";
import { ChargementAnime } from "../../src/components/ChargementAnime";
import { PartageWhatsApp } from "../../src/components/PartageWhatsApp";
import { BoutonDictee } from "../../src/components/BoutonDictee";
import { IllustrationHeros, SCENES } from "../../src/components/anime/IllustrationHeros";
import { Faq } from "../../src/components/Faq";
import { assainirSante } from "../../src/lib/server/assainir";
import { fixture } from "../aides";

function texteVisible(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x27;|&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ");
}

const SANTE = assainirSante(fixture("sante").data);
const CATALOGUE = JSON.parse(readFileSync(join(__dirname, "..", "..", "..", "KNOWLEDGE", "catalogue.json"), "utf8")) as {
  fiches: { titre: string }[];
};

test("accueil : les compteurs affichent la VRAIE valeur dès le rendu serveur", () => {
  const html = renderToStaticMarkup(<Accueil sante={SANTE} />);
  const visible = texteVisible(html);
  assert.match(visible, /13 situations, dans \d+ domaines/);
  assert.match(html, /class="chiffres"/);
  assert.match(visible, /situations traitées/);
  assert.doesNotMatch(visible, /\b0 situations/);
});

test("accueil : vidéo sans lecture automatique, FAQ, partage et illustration décorative", () => {
  const html = renderToStaticMarkup(<Accueil sante={SANTE} />);
  assert.match(html, /<video[^>]*preload="none"/);
  assert.doesNotMatch(html, /<video[^>]*autoplay/i);
  assert.match(html, /src="\/video\/presentation\.mp4"/);
  assert.match(html, /Questions fréquentes/);
  assert.match(html, /href="https:\/\/wa\.me\/\?text=/);
  assert.match(html, /class="illus" aria-hidden="true"/);
  // Apparitions : marquées, mais visibles par défaut (aucune opacité en ligne).
  assert.match(html, /data-apparition=""/);
  assert.doesNotMatch(html, /opacity:\s*0/);
});

test("illustration : les intitulés animés sont des fiches réelles du catalogue", () => {
  const titres = new Set(CATALOGUE.fiches.map((f) => f.titre));
  for (const s of SCENES) assert.ok(titres.has(s.fiche), `fiche inconnue : ${s.fiche}`);
  const html = renderToStaticMarkup(<IllustrationHeros />);
  assert.doesNotMatch(texteVisible(html), /Art(icle)?\.? ?\d+/i, "aucun numéro d'article dans l'illustration");
});

test("FAQ : réponses repliables, sans promesse de gratuité ni d'absence d'IA", () => {
  const visible = texteVisible(renderToStaticMarkup(<Faq />));
  assert.match(visible, /remplace-t-il un avocat/);
  assert.match(visible, /Supprimer cette consultation du serveur/);
  assert.doesNotMatch(visible, /gratuit/i);
  assert.doesNotMatch(visible, /intelligence artificielle|aucun tiers/i);
});

test("consultation : dix situations en un clic, toutes dans les domaines couverts", () => {
  const html = renderToStaticMarkup(<Parcours iaExterne />);
  assert.equal((html.match(/class="situation"/g) ?? []).length, SITUATIONS.length);
  assert.equal(SITUATIONS.length, 10);
  const couverts = new Set([
    "logement_baux_foncier",
    "famille_mariage_filiation",
    "contrats_dettes_commerce",
    "penal_procedure_penale",
  ]);
  for (const s of SITUATIONS) assert.ok(couverts.has(s.domaine), s.titre);
  assert.match(texteVisible(html), /Mon bailleur garde ma caution/);
  assert.doesNotMatch(texteVisible(html), /licenci|employeur|salaire impayé/i);
});

test("dictée : rien n'est rendu côté serveur (bouton seulement si le navigateur sait faire)", () => {
  assert.equal(renderToStaticMarkup(<BoutonDictee onTexte={() => undefined} />), "");
});

test("attente animée : toutes les étapes listées, la première en cours", () => {
  const html = renderToStaticMarkup(<ChargementAnime etapes={["Un", "Deux", "Trois"]} />);
  assert.match(html, /role="status"/);
  assert.match(html, /class="est-en-cours"[^>]*>.*Un/);
  assert.equal((html.match(/est-a-venir/g) ?? []).length, 2);
});

test("partage WhatsApp : lien wa.me, nouvel onglet, sans référent", () => {
  const html = renderToStaticMarkup(<PartageWhatsApp />);
  assert.match(html, /href="https:\/\/wa\.me\/\?text=Mon%20Recours%20CI/);
  assert.match(html, /target="_blank"/);
  assert.match(html, /rel="noopener noreferrer"/);
});
