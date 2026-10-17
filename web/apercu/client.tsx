/**
 * Point d'entrée navigateur du banc d'aperçu : monte le même composant
 * <Parcours /> que la page Next.js /consultation.
 */
import { createRoot } from "react-dom/client";
import { Parcours } from "../src/components/Parcours";

const racine = document.getElementById("racine");
if (racine) createRoot(racine).render(<Parcours />);
