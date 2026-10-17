"use client";

import { useEffect } from "react";

/**
 * Enregistre le service worker en production uniquement. Il ne met en cache que
 * les fichiers statiques de l'application, jamais les réponses de /api/*
 * (voir public/sw.js) : aucune consultation n'est stockée sur l'appareil.
 */
export function EnregistrementServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js", { scope: "/" }).catch(() => {
      // Sans service worker, l'application fonctionne normalement en ligne.
    });
  }, []);
  return null;
}
