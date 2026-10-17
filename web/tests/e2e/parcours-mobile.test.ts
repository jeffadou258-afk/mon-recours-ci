/**
 * Bout en bout dans un vrai navigateur (Chromium, gabarit téléphone), contre le
 * VRAI moteur Python. Aucune réponse simulée.
 *
 * L'interface est servie par le banc d'aperçu (apercu/serveur-apercu.tsx), qui
 * réutilise les composants et gestionnaires de l'application Next.js.
 */

import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { mkdir, readFile } from "node:fs/promises";
import { join } from "node:path";
import type { AddressInfo } from "node:net";
import type { Server } from "node:http";
import { chromium, type Browser, type BrowserContext, type Page } from "playwright";
import { construireClient, creerServeurApercu } from "../../apercu/serveur-apercu";
import { lancerMoteur, type MoteurLance } from "../moteur-reel";

const CAPTURES = join(__dirname, "captures");
const SECRET_SESSION = "secret-de-session-e2e-0123456789-abcdefghij";

let moteur: MoteurLance;
let serveur: Server;
let base: string;
let navigateur: Browser;

before(async () => {
  moteur = await lancerMoteur();
  process.env.MONRECOURS_API_URL = moteur.url;
  process.env.MONRECOURS_API_KEY = moteur.cle;
  process.env.MONRECOURS_SESSION_SECRET = SECRET_SESSION;
  await construireClient();
  serveur = creerServeurApercu();
  await new Promise<void>((ok) => serveur.listen(0, "127.0.0.1", ok));
  base = `http://127.0.0.1:${(serveur.address() as AddressInfo).port}`;
  navigateur = await chromium.launch();
  await mkdir(CAPTURES, { recursive: true });
});

after(async () => {
  await navigateur?.close();
  await new Promise<void>((ok) => (serveur ? serveur.close(() => ok()) : ok()));
  await moteur?.arreter();
});

async function contexteMobile(): Promise<BrowserContext> {
  return navigateur.newContext({
    viewport: { width: 360, height: 780 },
    deviceScaleFactor: 2,
    isMobile: true,
    hasTouch: true,
    locale: "fr-FR",
  });
}

async function sansDefilementHorizontal(page: Page): Promise<void> {
  const deborde = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
  assert.ok(deborde <= 0, `la page déborde horizontalement de ${deborde}px`);
}

test("accueil mobile : couverture réelle, pas de débordement", async () => {
  const ctx = await contexteMobile();
  const page = await ctx.newPage();
  await page.goto(base + "/");
  await page.getByRole("heading", { level: 1 }).waitFor();
  assert.match(await page.locator("body").innerText(), /13 situations sont couvertes/);
  await sansDefilementHorizontal(page);
  await page.screenshot({ path: join(CAPTURES, "01-accueil-mobile.png"), fullPage: true });
  await ctx.close();
});

test("parcours complet au toucher : décrire → préciser → résultat avec citations", async () => {
  const ctx = await contexteMobile();
  const page = await ctx.newPage();
  await page.goto(base + "/");
  await page.getByRole("link", { name: "Décrire mon problème" }).first().tap();
  await page.waitForURL(/\/consultation$/);

  // Entrée malformée : refusée localement, aucun appel réseau.
  let appels = 0;
  page.on("request", (r) => {
    if (r.url().includes("/api/")) appels++;
  });
  await page.getByRole("button", { name: "Analyser ma situation" }).tap();
  await page.getByText("Décrivez votre situation avant d'envoyer.").waitFor();
  assert.equal(appels, 0);

  await page
    .getByLabel("Expliquez avec vos mots ce qui vous arrive")
    .fill("Mon bailleur refuse de me rendre ma caution de deux mois depuis que j'ai quitté l'appartement.");
  await page.getByRole("button", { name: "Analyser ma situation" }).tap();

  await page.getByRole("heading", { name: "Quelques précisions" }).waitFor();
  const focus = await page.evaluate(() => document.activeElement?.id);
  assert.equal(focus, "titre-clarification", "le focus doit aller au titre de l'étape");
  await page.screenshot({ path: join(CAPTURES, "02-clarification-mobile.png"), fullPage: true });
  await sansDefilementHorizontal(page);

  await page.getByRole("radio", { name: "Oui" }).tap();
  assert.ok(await page.getByRole("radio", { name: "Oui" }).isChecked());
  await page.getByRole("button", { name: "Obtenir le résultat" }).tap();

  await page.getByRole("heading", { name: "Des textes du corpus correspondent à votre situation" }).waitFor();
  const texte = await page.locator("main").innerText();
  assert.match(texte, /Art\. 416/);
  assert.match(texte, /Le contrat de location peut prévoir un dépôt de garantie/);
  assert.match(texte, /Référence vérifiée/);
  assert.match(texte, /Faire relire votre situation/);
  assert.doesNotMatch(texte, /DOSSIERS|\/home\/|traceabilite/);

  // Provenance dépliable, lien vers le document officiel.
  await page.getByText("Provenance du texte").first().tap();
  const lien = page.getByRole("link", { name: /Ouvrir le document officiel/ }).first();
  assert.match((await lien.getAttribute("href")) ?? "", /^https:\/\/www\.dgi\.gouv\.ci\//);

  await sansDefilementHorizontal(page);
  await page.screenshot({ path: join(CAPTURES, "03-resultat-mobile.png"), fullPage: true });

  // Le cookie de session n'est pas lisible par le script de la page.
  assert.equal(await page.evaluate(() => document.cookie), "");
  const cookies = await ctx.cookies();
  const session = cookies.find((c) => c.name === "mrci_dossier");
  assert.ok(session?.httpOnly && session.sameSite === "Strict");

  await page.getByRole("button", { name: "Nouvelle demande" }).tap();
  await page.getByRole("heading", { name: "Décrivez votre situation" }).waitFor();
  await ctx.close();
});

test("question hors catalogue : « aucune conclusion possible » affiché clairement", async () => {
  const ctx = await contexteMobile();
  const page = await ctx.newPage();
  await page.goto(base + "/consultation");
  await page
    .getByLabel("Expliquez avec vos mots ce qui vous arrive")
    .fill("Mon employeur ne me paie plus mon salaire depuis trois mois.");
  await page.getByRole("button", { name: "Analyser ma situation" }).tap();
  await page.getByRole("heading", { name: "Aucune conclusion possible avec les textes disponibles" }).waitFor();
  const texte = await page.locator("main").innerText();
  assert.match(texte, /Travail/);
  assert.equal(await page.locator("blockquote").count(), 0, "aucune citation ne doit apparaître");
  await page.screenshot({ path: join(CAPTURES, "04-sans-fiche-mobile.png"), fullPage: true });
  await ctx.close();
});

test("urgence et verrous humains visibles dès la clarification", async () => {
  const ctx = await contexteMobile();
  const page = await ctx.newPage();
  await page.goto(base + "/consultation");
  await page
    .getByLabel("Expliquez avec vos mots ce qui vous arrive")
    .fill("On veut m'expulser demain matin avec la police, le bailleur a changé les serrures.");
  await page.getByRole("button", { name: "Analyser ma situation" }).tap();
  await page.getByRole("heading", { name: "Situation à traiter rapidement" }).waitFor();
  await page.getByRole("heading", { name: "Un professionnel doit intervenir avant toute démarche" }).waitFor();
  await page.screenshot({ path: join(CAPTURES, "05-urgence-mobile.png"), fullPage: true });
  await ctx.close();
});

test("moteur indisponible : message clair et bouton Réessayer, saisie conservée", async () => {
  const ctx = await contexteMobile();
  const page = await ctx.newPage();
  await page.goto(base + "/consultation");
  const urlReelle = process.env.MONRECOURS_API_URL;
  process.env.MONRECOURS_API_URL = "http://127.0.0.1:9"; // port fermé
  try {
    const demande = "Mon bailleur garde ma caution depuis deux mois.";
    await page.getByLabel("Expliquez avec vos mots ce qui vous arrive").fill(demande);
    await page.getByRole("button", { name: "Analyser ma situation" }).tap();
    await page.getByText("Service momentanément indisponible").waitFor();
    assert.ok(await page.getByRole("button", { name: "Réessayer" }).isVisible());
    assert.equal(await page.getByLabel("Expliquez avec vos mots ce qui vous arrive").inputValue(), demande);
    await page.screenshot({ path: join(CAPTURES, "06-indisponible-mobile.png"), fullPage: true });

    process.env.MONRECOURS_API_URL = urlReelle;
    await page.getByRole("button", { name: "Réessayer" }).tap();
    await page.getByRole("heading", { name: "Quelques précisions" }).waitFor();
  } finally {
    process.env.MONRECOURS_API_URL = urlReelle;
  }
  await ctx.close();
});

test("perte de réseau côté navigateur : message « Pas de connexion »", async () => {
  const ctx = await contexteMobile();
  const page = await ctx.newPage();
  await page.goto(base + "/consultation");
  await ctx.setOffline(true);
  await page.getByLabel("Expliquez avec vos mots ce qui vous arrive").fill("Mon bailleur garde ma caution depuis deux mois.");
  await page.getByRole("button", { name: "Analyser ma situation" }).tap();
  await page.getByText("Pas de connexion").waitFor();
  await ctx.setOffline(false);
  await ctx.close();
});

test("police de secours large (DejaVu Sans) : aucune page ne déborde sur 360 px", async () => {
  // Les polices auto-hébergées peuvent manquer (réseau lent, blocage) : la mise
  // en page doit tenir avec une police de secours large.
  const ctx = await contexteMobile();
  const page = await ctx.newPage();
  for (const chemin of ["/", "/consultation", "/comprendre"]) {
    await page.goto(base + chemin);
    await page.addStyleTag({
      content: ":root{--police-texte:'DejaVu Sans';--police-titre:'DejaVu Sans';--police-loi:'DejaVu Serif'} *{font-family:'DejaVu Sans',sans-serif}",
    });
    await page.waitForTimeout(100);
    await sansDefilementHorizontal(page);
  }
  await ctx.close();
});

test("bureau : mise en page large lisible", async () => {
  const ctx = await navigateur.newContext({ viewport: { width: 1280, height: 900 }, locale: "fr-FR" });
  const page = await ctx.newPage();
  await page.goto(base + "/");
  await page.screenshot({ path: join(CAPTURES, "07-accueil-bureau.png"), fullPage: true });
  await sansDefilementHorizontal(page);
  await ctx.close();
});

test("le code envoyé au navigateur ne contient ni clé, ni secret, ni nom de variable serveur", async () => {
  const bundle = await readFile(join(__dirname, "..", "..", "apercu", "dist", "app.js"), "utf8");
  for (const interdit of [moteur.cle, SECRET_SESSION, "MONRECOURS_", "X-API-Key", "127.0.0.1:"]) {
    assert.ok(!bundle.includes(interdit), `trouvé dans le bundle client : ${interdit.slice(0, 12)}…`);
  }
});
