import type { NextConfig } from "next";

const enDeveloppement = process.env.NODE_ENV !== "production";

// Politique de sécurité du contenu : tout est servi depuis l'origine de l'app.
// Le navigateur ne parle qu'à /api/* (même origine) ; le moteur juridique n'est
// jamais joint directement depuis le client.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${enDeveloppement ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "font-src 'self'",
  "connect-src 'self'",
  "manifest-src 'self'",
  "worker-src 'self'",
  "frame-ancestors 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "object-src 'none'",
].join("; ");

const configuration: NextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  // L'application n'utilise pas next/image : l'optimisation d'images est désactivée
  // et aucun domaine distant n'est autorisé (pas de `remotePatterns`). Le traitement
  // d'images a fait l'objet des avis GHSA-2464-fhr4-w9xw (oct. 2026) et
  // GHSA-cjq9-62q9-8jv4 (sept. 2026). La correction reste la mise à jour de
  // Next.js (15.5.28) ; ce réglage n'est qu'une précaution supplémentaire.
  images: { unoptimized: true },
  async headers() {
    return [
      {
        source: "/:chemin*",
        headers: [
          { key: "Content-Security-Policy", value: csp },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
          { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
        ],
      },
      {
        source: "/api/:chemin*",
        headers: [{ key: "Cache-Control", value: "no-store" }],
      },
      {
        source: "/sw.js",
        headers: [
          { key: "Cache-Control", value: "no-cache" },
          { key: "Service-Worker-Allowed", value: "/" },
        ],
      },
    ];
  },
};

export default configuration;
