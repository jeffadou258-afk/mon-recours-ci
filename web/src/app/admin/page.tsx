import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { AccesRefuse, TableauDeBord } from "@/components/admin/TableauDeBord";
import { evaluerAccesAdmin } from "@/lib/server/auth/acces";
import { creerEcrivain } from "@/lib/server/auth/audit";
import { lireEtatAuth } from "@/lib/server/auth/comptes";
import { construireTableauDeBord } from "@/lib/server/auth/tableau";

export const metadata: Metadata = {
  title: "Administration",
  robots: { index: false, follow: false },
};

// Jamais mis en cache ni pré-rendu : la décision d'accès est prise à chaque requête.
export const dynamic = "force-dynamic";
export const revalidate = 0;

export default async function PageAdministration() {
  const magasin = await cookies();
  const enteteCookie = magasin.getAll().map((c) => `${c.name}=${encodeURIComponent(c.value)}`).join("; ");
  const decision = evaluerAccesAdmin(enteteCookie || null);

  // Fermé (démonstration, aucun compte) ou non connecté : la page de connexion explique pourquoi.
  if (decision.acces === "ferme" || decision.acces === "anonyme") redirect("/connexion");

  const audit = creerEcrivain();
  const horodatage = new Date().toISOString();

  if (decision.acces === "refuse") {
    await audit({ horodatage, evenement: "acces_administration_refuse", compte: decision.compte.email });
    return <AccesRefuse email={decision.compte.email} />;
  }

  const etat = lireEtatAuth();
  if (etat.etat !== "actif") redirect("/connexion");
  await audit({ horodatage, evenement: "acces_administration", compte: decision.compte.email });
  const donnees = await construireTableauDeBord(decision.compte, etat.comptes, etat.ignores);
  return <TableauDeBord donnees={donnees} />;
}
