import type { Metadata } from "next";
import { Parcours } from "@/components/Parcours";

export const metadata: Metadata = {
  title: "Décrire mon problème",
};

export default function PageConsultation() {
  // Lu côté serveur, comme le bandeau de `layout.tsx` : en démonstration, le
  // parcours ne doit rien affirmer sur un moteur qui n'est pas interrogé.
  return <Parcours demo={process.env.MONRECOURS_MODE === "demo"} />;
}
