/*
 * Service worker de Mon Recours CI.
 *
 * Règle de confidentialité : AUCUNE réponse de /api/* n'est mise en cache, et
 * aucune page de consultation non plus. Seuls les fichiers statiques versionnés
 * (/_next/static/*, icônes, manifeste) et la page hors ligne sont conservés.
 */

const VERSION = "mrci-v1";
const PAGE_HORS_LIGNE = "/hors-ligne";
const PRECHARGE = [PAGE_HORS_LIGNE, "/icone.svg", "/manifest.webmanifest"];

self.addEventListener("install", (evenement) => {
  evenement.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(PRECHARGE)).then(() => self.skipWaiting()),
  );
});

self.addEventListener("activate", (evenement) => {
  evenement.waitUntil(
    caches
      .keys()
      .then((cles) => Promise.all(cles.filter((c) => c !== VERSION).map((c) => caches.delete(c))))
      .then(() => self.clients.claim()),
  );
});

function estStatique(url) {
  return (
    url.pathname.startsWith("/_next/static/") ||
    url.pathname === "/icone.svg" ||
    url.pathname === "/icone-maskable.svg" ||
    url.pathname.startsWith("/icone-") ||
    url.pathname === "/manifest.webmanifest"
  );
}

self.addEventListener("fetch", (evenement) => {
  const requete = evenement.request;
  if (requete.method !== "GET") return;
  const url = new URL(requete.url);
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith("/api/")) return; // jamais de cache : réseau uniquement

  if (estStatique(url)) {
    evenement.respondWith(
      caches.match(requete).then(
        (enCache) =>
          enCache ||
          fetch(requete).then((reponse) => {
            if (reponse.ok) {
              const copie = reponse.clone();
              caches.open(VERSION).then((cache) => cache.put(requete, copie));
            }
            return reponse;
          }),
      ),
    );
    return;
  }

  if (requete.mode === "navigate") {
    evenement.respondWith(fetch(requete).catch(() => caches.match(PAGE_HORS_LIGNE)));
  }
});
