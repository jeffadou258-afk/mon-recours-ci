/**
 * Exécuté une fois au démarrage du serveur Next.js (runtime Node).
 *
 * Prépare l'empreinte factice utilisée pour vérifier les connexions à un compte
 * inconnu (voir `lib/server/auth/motdepasse.ts`) : aucune tentative de
 * connexion ne paie ce calcul. Rien n'est fait en démonstration, où
 * l'administration est fermée.
 */
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  if (process.env.MONRECOURS_MODE === "demo") return;
  const { preparerEmpreinteFactice } = await import("./lib/server/auth/motdepasse");
  await preparerEmpreinteFactice();
}
