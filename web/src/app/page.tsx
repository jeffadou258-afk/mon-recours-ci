import { Accueil } from "@/components/Accueil";
import { obtenirSante } from "@/lib/server/handlers";

// La couverture est lue en direct sur le moteur à chaque visite.
export const dynamic = "force-dynamic";

export default async function PageAccueil() {
  const sante = await obtenirSante();
  return <Accueil sante={sante} />;
}
