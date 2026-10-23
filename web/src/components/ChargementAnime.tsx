"use client";

import { useEffect, useState } from "react";

/**
 * Attente animée : les étapes réelles du traitement défilent pendant que le
 * moteur travaille. Le premier message est rendu côté serveur ; la zone est
 * annoncée poliment aux lecteurs d'écran.
 */
export function ChargementAnime({ etapes }: { etapes: string[] }) {
  const [index, setIndex] = useState(0);
  useEffect(() => {
    if (etapes.length < 2) return;
    const minuterie = window.setInterval(() => setIndex((i) => Math.min(i + 1, etapes.length - 1)), 1600);
    return () => window.clearInterval(minuterie);
  }, [etapes.length]);
  return (
    <div className="chargement chargement--anime" role="status" aria-live="polite">
      <span className="chargement__barre" aria-hidden="true" />
      <ol className="chargement__etapes">
        {etapes.map((e, i) => (
          <li key={e} className={i < index ? "est-fait" : i === index ? "est-en-cours" : "est-a-venir"}>
            <span className="chargement__puce" aria-hidden="true" />
            {e}
          </li>
        ))}
      </ol>
    </div>
  );
}
