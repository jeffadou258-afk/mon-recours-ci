"use client";

import { useEffect } from "react";

/**
 * Fait apparaître en douceur, au défilement, les éléments marqués
 * `data-apparition` (avec, si besoin, un délai CSS `--delai`).
 *
 * Le contenu reste visible sans JavaScript et pour qui préfère moins
 * d'animations : la classe `apparitions-actives` n'est posée sur <html> que si
 * le navigateur sait observer le défilement ET que la personne n'a pas demandé
 * de réduire les mouvements.
 */
export function Apparitions() {
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    const racine = document.documentElement;
    const elements = Array.from(document.querySelectorAll<HTMLElement>("[data-apparition]"));
    if (elements.length === 0) return;
    const observateur = new IntersectionObserver(
      (entrees) => {
        for (const entree of entrees) {
          if (entree.isIntersecting) {
            entree.target.classList.add("apparu");
            observateur.unobserve(entree.target);
          }
        }
      },
      { rootMargin: "0px 0px -8% 0px", threshold: 0.12 },
    );
    racine.classList.add("apparitions-actives");
    elements.forEach((el) => observateur.observe(el));
    return () => {
      observateur.disconnect();
      racine.classList.remove("apparitions-actives");
    };
  }, []);
  return null;
}
