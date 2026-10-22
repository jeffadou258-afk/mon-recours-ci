// Configuration ESLint de l'interface (règles officielles de Next.js + TypeScript).
// Les outils ne sont pas dans package.json : la CI les installe pour la seule
// étape « ESLint » (voir .github/workflows/interface-web.yml), après la
// construction, pour que `next build` ne change pas de comportement.
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat({ baseDirectory: dirname(fileURLToPath(import.meta.url)) });

const config = [
  { ignores: [".next/**", "node_modules/**", "next-env.d.ts", "tests/e2e/captures/**"] },
  ...compat.extends("next/core-web-vitals", "next/typescript"),
];

export default config;
