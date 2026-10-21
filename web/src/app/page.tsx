import { Accueil } from "@/components/Accueil";
import { obtenirSante } from "@/lib/server/handlers";

// La couverture est lue en direct sur le moteur à chaque visite.
export const dynamic = "force-dynamic";

export default async function PageAccueil() {
  const sante = await obtenirSante();
  // En démonstration, l'accueil le dit explicitement : le corpus complet n'est
  // pas connecté, et les chiffres affichés sont ceux du produit, pas d'un
  // chargement réel.
  const demo = process.env.MONRECOURS_MODE === "demo";
  // Ni démonstration ni clé de moteur : l'instance n'est pas configurée. Le dire
  // évite qu'un déploiement raté passe pour le service réel momentanément en
  // panne.
  const nonConfigure = !demo && !process.env.MONRECOURS_API_KEY;
  return <Accueil sante={sante} demo={demo} nonConfigure={nonConfigure} />;
}
