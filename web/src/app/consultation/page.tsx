import type { Metadata } from "next";
import { Parcours } from "@/components/Parcours";

export const metadata: Metadata = {
  title: "Décrire mon problème",
};

export default function PageConsultation() {
  return <Parcours />;
}
