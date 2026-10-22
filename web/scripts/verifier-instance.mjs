#!/usr/bin/env node
/**
 * Contrôle d'une instance DÉPLOYÉE avant ouverture au public.
 *
 *   node scripts/verifier-instance.mjs https://mon-recours.exemple.ci
 *   npm run verifier:instance -- https://mon-recours.exemple.ci
 *
 * À lancer depuis n'importe où, sur l'URL réelle, après installation et avant
 * d'annoncer le service. Il ne modifie rien : uniquement des requêtes de lecture
 * et une seule demande d'ouverture sans session (rejetée par le serveur).
 *
 * Sortie : PASS / FAIL / INFO par contrôle, code de sortie 1 si un FAIL.
 *
 * Ce qu'il ne peut PAS prouver : que le corpus est juridiquement juste, que les
 * sauvegardes se restaurent, que l'administration est utilisable par un humain.
 * Ces points restent manuels (voir docs/MISE_EN_PRODUCTION.md).
 */

const URL_BASE = (process.argv[2] || "").replace(/\/+$/, "");
if (!/^https?:\/\/[^/]+/.test(URL_BASE)) {
  console.error("Usage : node scripts/verifier-instance.mjs https://votre-domaine.tld");
  process.exit(2);
}
const HTTPS = URL_BASE.startsWith("https://");
const resultats = [];
let echecs = 0;

function noter(nom, etat, detail = "") {
  if (etat === "FAIL") echecs++;
  resultats.push({ nom, etat, detail });
  console.log(`  ${etat.padEnd(4)} ${nom}${detail ? " — " + detail : ""}`);
}

async function appel(chemin, options = {}) {
  const debut = Date.now();
  try {
    const r = await fetch(`${URL_BASE}${chemin}`, { redirect: "manual", ...options });
    const corps = options.method === "HEAD" ? "" : await r.text();
    return { statut: r.status, entetes: r.headers, corps, ms: Date.now() - debut };
  } catch (e) {
    return { statut: 0, entetes: new Headers(), corps: String(e.message), ms: Date.now() - debut };
  }
}

console.log(`\n  Instance contrôlée : ${URL_BASE}\n`);

// 1. Disponibilité et en-têtes de sécurité
const accueil = await appel("/", { method: "GET" });
noter("page d'accueil répond", accueil.statut === 200 ? "PASS" : "FAIL", `${accueil.statut} en ${accueil.ms} ms`);
const h = accueil.entetes;
noter("aucune version serveur exposée", !h.get("x-powered-by") ? "PASS" : "FAIL", h.get("x-powered-by") || "absent");
noter("Content-Security-Policy", h.get("content-security-policy") ? "PASS" : "FAIL");
noter("X-Content-Type-Options: nosniff", h.get("x-content-type-options") === "nosniff" ? "PASS" : "FAIL");
if (HTTPS) {
  const hsts = h.get("strict-transport-security") || "";
  const duree = Number((hsts.match(/max-age=(\d+)/) || [])[1] || 0);
  noter("HSTS actif (≥ 6 mois)", duree >= 15552000 ? "PASS" : "FAIL", hsts || "absent");
} else {
  noter("HSTS", "INFO", "non exigé en HTTP local");
}

// 2. État du corpus : le service dit-il la vérité sur ce qu'il sert ?
const sante = await appel("/api/sante");
let donnees = null;
try {
  donnees = JSON.parse(sante.corps);
} catch {
  /* corps non JSON */
}
const corpus = donnees?.data?.corpus ?? donnees?.corpus ?? null;
noter("route /api/sante", sante.statut === 200 && corpus ? "PASS" : "FAIL", `${sante.statut}`);
if (corpus) {
  const articles = Number(corpus.articles ?? 0);
  const documents = Number(corpus.documents ?? 0);
  noter("corpus réellement connecté", articles > 0 && documents > 0 ? "PASS" : "FAIL", `${documents} document(s), ${articles} article(s)`);
  noter("intégrité annoncée", corpus.integrite ? "INFO" : "FAIL", String(corpus.integrite ?? "non renseignée"));
  const mode = donnees?.mode ?? donnees?.data?.mode ?? corpus.modeIntegrite;
  noter("mode de service", mode === "demonstration" ? "FAIL" : "PASS", mode === "demonstration" ? "DÉMONSTRATION sur une URL de production" : "service réel");
  noter("avertissement juridique présent", /validation juridique|conseil juridique|pas un avocat/i.test(sante.corps) ? "PASS" : "FAIL");
} else {
  noter("corpus", "FAIL", "réponse inexploitable");
}

// 3. Les routes qui ne doivent jamais s'ouvrir sans session
const admin = await appel("/admin");
noter("/admin fermé sans session", admin.statut === 307 || admin.statut === 302 ? "PASS" : "FAIL", `${admin.statut}`);
const pdf = await appel("/api/courrier/telecharger");
const typePdf = pdf.entetes.get("content-type") || "";
noter("PDF interdit sans session", /pdf/i.test(typePdf) ? "FAIL" : "PASS", `${pdf.statut} ${typePdf}`);

const EN_TETES_POST = {
  "content-type": "application/json",
  // Le serveur refuse toute écriture sans origine : un navigateur l'envoie toujours.
  origin: URL_BASE,
};

// 4. Le formulaire refuse proprement une saisie vide
const ouvrir = await appel("/api/ouvrir", {
  method: "POST",
  headers: EN_TETES_POST,
  body: JSON.stringify({ demande: "" }),
});
noter("saisie vide rejetée (pas 500)", ouvrir.statut >= 400 && ouvrir.statut < 500 ? "PASS" : "FAIL", `${ouvrir.statut}`);
noter("aucune trace technique dans l'erreur", /at .*\.(js|ts):|node_modules|\/opt\/|stack/i.test(ouvrir.corps) ? "FAIL" : "PASS");

// 5. Limitation de débit réellement active (sur une route protégée)
let limite = false;
for (let i = 0; i < 25 && !limite; i++) {
  const r = await appel("/api/ouvrir", {
    method: "POST",
    headers: EN_TETES_POST,
    body: JSON.stringify({ demande: "" }),
  });
  if (r.statut === 429) limite = true;
}
noter("limitation de débit active", limite ? "PASS" : "FAIL", limite ? "429 observé sur /api/ouvrir" : "25 requêtes sans 429");

// 6. Pas de mode démonstration résiduel
const bandeau = /DÉMONSTRATION PUBLIQUE|DEMONSTRATION PUBLIQUE/.test(accueil.corps);
noter("aucun bandeau de démonstration", bandeau ? "FAIL" : "PASS");

// 7. Redirection HTTP → HTTPS (uniquement si l'on teste en HTTPS)
if (HTTPS) {
  const enHttp = URL_BASE.replace(/^https:/, "http:");
  try {
    const r = await fetch(enHttp + "/", { redirect: "manual" });
    const lieu = r.headers.get("location") || "";
    noter("HTTP redirige vers HTTPS", r.status >= 300 && r.status < 400 && lieu.startsWith("https://") ? "PASS" : "FAIL", `${r.status} ${lieu}`);
  } catch {
    noter("HTTP redirige vers HTTPS", "INFO", "port 80 non joignable depuis ici");
  }
}

console.log(`\n  ${resultats.filter((r) => r.etat === "PASS").length} PASS · ${echecs} FAIL · ${resultats.filter((r) => r.etat === "INFO").length} INFO\n`);
if (echecs > 0) {
  console.log("  Instance NON prête pour une ouverture au public.");
  process.exit(1);
}
console.log("  Contrôles automatiques satisfaits. Les vérifications manuelles restent requises");
console.log("  (restauration de sauvegarde, parcours d'administration, relecture juridique).");
