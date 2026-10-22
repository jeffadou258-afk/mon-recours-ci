// Configuration ESLint de l'interface (règles officielles de Next.js + TypeScript).
// Les outils ne sont pas dans package.json : la CI les installe pour la seule
// étape « ESLint » (voir .github/workflows/interface-web.yml), après la
// construction, pour que `next build` ne change pas de comportement.
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

const config = [
  {
    // Fichiers générés ou produits par les outils : jamais relus à la main.
    ignores: [".next/**", "node_modules/**", "next-env.d.ts", "apercu/dist/**", "tests/e2e/captures/**"],
  },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    rules: {
      // Choix délibéré : liens HTML ordinaires (rechargement complet). Ils
      // fonctionnent sans le routeur Next.js — page « hors ligne » servie par le
      // service worker, aperçu `apercu/` rendu hors de Next — et ne gardent
      // aucun état de consultation en mémoire d'une page à l'autre.
      "@next/next/no-html-link-for-pages": "off",
    },
  },
  {
    // Tests : les réponses enregistrées du moteur sont lues comme JSON libre.
    files: ["tests/**/*.ts", "tests/**/*.tsx"],
    rules: { "@typescript-eslint/no-explicit-any": "off" },
  },
];

export default config;
