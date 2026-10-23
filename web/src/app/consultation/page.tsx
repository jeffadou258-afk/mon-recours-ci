import type { Metadata } from "next";
import { Parcours } from "@/components/Parcours";
import { obtenirSante } from "@/lib/server/handlers";

export const metadata: Metadata = {
  title: "Décrire mon problème",
};

// L'avis de confidentialité dépend de l'état réel du moteur (couche de langage
// active ou non) : il est donc lu à chaque visite.
export const dynamic = "force-dynamic";

export default async function PageConsultation() {
  // Lu côté serveur, comme le bandeau de `layout.tsx` : en démonstration, le
  // parcours ne doit rien affirmer sur un moteur qui n'est pas interrogé.
  const demo = process.env.MONRECOURS_MODE === "demo";
  // On n'affiche « aucune IA » que si le moteur CONFIRME que la couche de
  // langage est inactive. Moteur muet ou état inconnu : avis prudent (IA).
  const sante = demo ? null : await obtenirSante();
  const iaExterne = !(sante && sante.langageActif === false);
  return <Parcours demo={demo} iaExterne={iaExterne} />;
}
