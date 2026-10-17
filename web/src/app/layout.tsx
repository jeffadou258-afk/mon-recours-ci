import type { Metadata, Viewport } from "next";
import { Atkinson_Hyperlegible, Bricolage_Grotesque, Source_Serif_4 } from "next/font/google";
import { EnTete, PiedDePage } from "@/components/Cadre";
import { EnregistrementServiceWorker } from "@/components/EnregistrementServiceWorker";
import "./globals.css";

// Polices auto-hébergées par Next.js au moment du build : aucune requête vers
// Google depuis le navigateur des visiteurs.
const policeTexte = Atkinson_Hyperlegible({
  subsets: ["latin"],
  weight: ["400", "700"],
  variable: "--police-texte",
  display: "swap",
});
const policeTitre = Bricolage_Grotesque({
  subsets: ["latin"],
  weight: ["700", "800"],
  variable: "--police-titre",
  display: "swap",
});
const policeLoi = Source_Serif_4({
  subsets: ["latin"],
  variable: "--police-loi",
  display: "swap",
});

export const metadata: Metadata = {
  title: { default: "Mon Recours CI", template: "%s | Mon Recours CI" },
  description:
    "Service d'information juridique sur le droit ivoirien : décrivez votre situation, obtenez les articles de loi cités mot pour mot avec leur source officielle.",
  applicationName: "Mon Recours CI",
  robots: { index: false, follow: false },
  formatDetection: { telephone: false },
  icons: { icon: "/icone.svg", apple: "/apple-touch-icon.png" },
};

export const viewport: Viewport = {
  themeColor: "#0F2A22",
  width: "device-width",
  initialScale: 1,
};

export default function Racine({ children }: { children: React.ReactNode }) {
  return (
    <html lang="fr" className={`${policeTexte.variable} ${policeTitre.variable} ${policeLoi.variable}`}>
      <body>
        <a href="#contenu" className="lien-evitement">
          Aller au contenu
        </a>
        <EnTete />
        <main id="contenu" className="page">
          {children}
        </main>
        <PiedDePage />
        <EnregistrementServiceWorker />
      </body>
    </html>
  );
}
