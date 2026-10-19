/**
 * BANC D'APERÇU — outil de test, PAS un serveur de production.
 *
 * Pourquoi il existe : il permet de piloter l'interface dans un vrai navigateur
 * (tests de bout en bout, captures mobiles) dans un environnement où Next.js ne
 * peut pas être installé. Il réutilise À L'IDENTIQUE :
 *   - les composants de src/components (rendus côté serveur ou montés côté client) ;
 *   - les gestionnaires de src/lib/server/handlers.ts pour /api/* ;
 *   - la feuille de style src/app/globals.css.
 * Seule la « colle » Next.js (routage, polices auto-hébergées, metadata) diffère.
 * En usage normal, lancer l'application avec `npm run dev` ou `npm run build && npm start`.
 *
 *   MONRECOURS_API_URL=… MONRECOURS_API_KEY=… MONRECOURS_SESSION_SECRET=… npm run apercu
 */

import { createServer, type IncomingMessage, type ServerResponse } from "node:http";
import { readFile, mkdir } from "node:fs/promises";
import { join, extname } from "node:path";
import { renderToString } from "react-dom/server";
import * as esbuild from "esbuild";
import { Accueil } from "../src/components/Accueil";
import { EnTete, PiedDePage } from "../src/components/Cadre";
import PageComprendre from "../src/app/comprendre/page";
import { gererOuvrir, gererRepondre, gererSante, gererSupprimer, obtenirSante } from "../src/lib/server/handlers";

const RACINE_WEB = join(__dirname, "..");
const DIST = join(__dirname, "dist");

export async function construireClient(): Promise<void> {
  await mkdir(DIST, { recursive: true });
  await esbuild.build({
    entryPoints: [join(__dirname, "client.tsx")],
    bundle: true,
    minify: true,
    format: "esm",
    target: "es2020",
    jsx: "automatic",
    outfile: join(DIST, "app.js"),
    tsconfig: join(RACINE_WEB, "tsconfig.json"),
    define: { "process.env.NODE_ENV": '"production"' },
    logLevel: "warning",
  });
}

function page(titre: string, corps: string, avecScript = false): string {
  return `<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#1C2B26">
<meta name="robots" content="noindex, nofollow">
<title>${titre}</title>
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" href="/icone.svg" type="image/svg+xml">
<link rel="stylesheet" href="/app.css">
</head>
<body>
<a href="#contenu" class="lien-evitement">Aller au contenu</a>
${renderToString(<EnTete />)}
<main id="contenu" class="page">${corps}</main>
${renderToString(<PiedDePage />)}
${avecScript ? '<script type="module" src="/app.js"></script>' : ""}
</body>
</html>`;
}

const MANIFESTE = JSON.stringify({
  name: "Mon Recours CI",
  short_name: "Mon Recours",
  lang: "fr",
  start_url: "/",
  display: "standalone",
  background_color: "#F5F7F4",
  theme_color: "#1C2B26",
  icons: [{ src: "/icone.svg", sizes: "any", type: "image/svg+xml" }],
});

const TYPES: Record<string, string> = {
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".svg": "image/svg+xml",
  ".png": "image/png",
};

async function versRequeteWeb(req: IncomingMessage): Promise<Request> {
  const morceaux: Buffer[] = [];
  for await (const m of req) morceaux.push(m as Buffer);
  const entetes = new Headers();
  for (const [nom, valeur] of Object.entries(req.headers)) {
    if (typeof valeur === "string") entetes.set(nom, valeur);
    else if (Array.isArray(valeur)) entetes.set(nom, valeur.join(", "));
  }
  const methode = req.method ?? "GET";
  return new Request(`http://${req.headers.host ?? "localhost"}${req.url ?? "/"}`, {
    method: methode,
    headers: entetes,
    body: methode === "GET" || methode === "HEAD" ? undefined : Buffer.concat(morceaux),
  });
}

async function envoyerWeb(reponse: Response, res: ServerResponse): Promise<void> {
  const entetes: Record<string, string | string[]> = {};
  reponse.headers.forEach((valeur, nom) => {
    entetes[nom] = valeur;
  });
  res.writeHead(reponse.status, entetes);
  res.end(Buffer.from(await reponse.arrayBuffer()));
}

function envoyerHtml(res: ServerResponse, statut: number, html: string): void {
  res.writeHead(statut, {
    "Content-Type": "text/html; charset=utf-8",
    "Content-Security-Policy":
      "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
  });
  res.end(html);
}

export function creerServeurApercu() {
  return createServer(async (req, res) => {
    try {
      const url = new URL(req.url ?? "/", "http://localhost");
      const chemin = url.pathname;

      if (chemin === "/api/sante" && req.method === "GET") return envoyerWeb(await gererSante(await versRequeteWeb(req)), res);
      if (chemin === "/api/ouvrir" && req.method === "POST") return envoyerWeb(await gererOuvrir(await versRequeteWeb(req)), res);
      if (chemin === "/api/repondre" && req.method === "POST")
        return envoyerWeb(await gererRepondre(await versRequeteWeb(req)), res);
      if (chemin === "/api/supprimer" && req.method === "POST")
        return envoyerWeb(await gererSupprimer(await versRequeteWeb(req)), res);
      if (chemin.startsWith("/api/")) {
        res.writeHead(405, { "Content-Type": "application/json" });
        return res.end('{"ok":false}');
      }

      if (chemin === "/") {
        const sante = await obtenirSante();
        return envoyerHtml(res, 200, page("Mon Recours CI", renderToString(<Accueil sante={sante} />)));
      }
      if (chemin === "/consultation") {
        return envoyerHtml(res, 200, page("Décrire mon problème | Mon Recours CI", '<div id="racine"></div>', true));
      }
      if (chemin === "/comprendre") {
        return envoyerHtml(res, 200, page("Comprendre les résultats | Mon Recours CI", renderToString(<PageComprendre />)));
      }
      if (chemin === "/manifest.webmanifest") {
        res.writeHead(200, { "Content-Type": "application/manifest+json" });
        return res.end(MANIFESTE);
      }

      let fichier: string | null = null;
      if (chemin === "/app.css") fichier = join(RACINE_WEB, "src", "app", "globals.css");
      else if (chemin === "/app.js") fichier = join(DIST, "app.js");
      else if (/^\/[a-z0-9-]+\.(svg|png|js)$/.test(chemin)) fichier = join(RACINE_WEB, "public", chemin.slice(1));
      if (fichier) {
        const contenu = await readFile(fichier);
        res.writeHead(200, { "Content-Type": TYPES[extname(fichier)] ?? "application/octet-stream" });
        return res.end(contenu);
      }
      return envoyerHtml(res, 404, page("Page introuvable", "<h1>Page introuvable</h1>"));
    } catch (erreur) {
      console.error("erreur du banc d'aperçu :", erreur instanceof Error ? erreur.message : erreur);
      if (!res.headersSent) res.writeHead(500);
      res.end();
    }
  });
}

if (require.main === module) {
  const port = Number(process.env.PORT ?? 3000);
  construireClient().then(() => {
    creerServeurApercu().listen(port, "127.0.0.1", () => {
      console.log(`Banc d'aperçu sur http://127.0.0.1:${port} (outil de test, pas de production)`);
    });
  });
}
