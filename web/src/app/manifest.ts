import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Mon Recours CI",
    short_name: "Mon Recours",
    description: "Information juridique sur le droit ivoirien, avec les textes de loi cités à la source.",
    lang: "fr",
    start_url: "/",
    scope: "/",
    display: "standalone",
    orientation: "portrait",
    background_color: "#F5F7F4",
    theme_color: "#1C2B26",
    icons: [
      { src: "/icone-192.png", sizes: "192x192", type: "image/png", purpose: "any" },
      { src: "/icone-512.png", sizes: "512x512", type: "image/png", purpose: "any" },
      { src: "/icone-maskable-512.png", sizes: "512x512", type: "image/png", purpose: "maskable" },
      { src: "/icone.svg", sizes: "any", type: "image/svg+xml", purpose: "any" },
    ],
  };
}
