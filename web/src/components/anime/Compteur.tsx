"use client";

import { useEffect, useRef, useState } from "react";

const FORMAT = new Intl.NumberFormat("fr-FR");

/**
 * Nombre qui défile de 0 jusqu'à sa valeur quand il devient visible.
 *
 * Le rendu serveur affiche directement la valeur réelle : sans JavaScript ou si
 * les mouvements sont réduits, on lit toujours le vrai chiffre. L'animation ne
 * dure qu'un instant et se termine sur la valeur exacte.
 */
export function Compteur({ valeur, duree = 1400 }: { valeur: number; duree?: number }) {
  const [affiche, setAffiche] = useState(valeur);
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return;
    if (window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return;
    let image = 0;
    const observateur = new IntersectionObserver(
      (entrees) => {
        if (!entrees.some((e) => e.isIntersecting)) return;
        observateur.disconnect();
        const debut = performance.now();
        const pas = (maintenant: number) => {
          const t = Math.min(1, (maintenant - debut) / duree);
          const adouci = 1 - Math.pow(1 - t, 3);
          setAffiche(Math.round(valeur * adouci));
          if (t < 1) image = requestAnimationFrame(pas);
        };
        setAffiche(0);
        image = requestAnimationFrame(pas);
      },
      { threshold: 0.6 },
    );
    observateur.observe(el);
    return () => {
      observateur.disconnect();
      cancelAnimationFrame(image);
    };
  }, [valeur, duree]);

  return (
    <span ref={ref} className="compteur-anime">
      {FORMAT.format(affiche)}
    </span>
  );
}
