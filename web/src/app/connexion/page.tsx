import type { Metadata } from "next";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { FormulaireConnexion } from "@/components/FormulaireConnexion";
import { evaluerAccesAdmin } from "@/lib/server/auth/acces";

export const metadata: Metadata = {
  title: "Connexion",
};

// Lu à chaque requête : l'état dépend du cookie et de la configuration du serveur.
export const dynamic = "force-dynamic";

export default async function PageConnexion({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const parametres = await searchParams;
  const magasin = await cookies();
  const enteteCookie = magasin.getAll().map((c) => `${c.name}=${encodeURIComponent(c.value)}`).join("; ");
  const decision = evaluerAccesAdmin(enteteCookie || null);

  // Déjà connecté avec le rôle administrateur : inutile de se reconnecter.
  if (decision.acces === "autorise") redirect("/admin");

  const disponibilite =
    decision.acces === "ferme"
      ? decision.etat.etat === "desactive_demo"
        ? "desactive_demo"
        : "non_configure"
      : "actif";

  return (
    <section className="connexion">
      <div className="connexion__carte">
        <p className="connexion__surtitre">Espace réservé</p>
        <h1 className="titre-etape">Connexion</h1>
        <p className="formulaire__aide">
          Cet espace est réservé à l&apos;équipe qui administre Mon Recours CI. Il ne donne accès à aucune
          consultation de visiteur.
        </p>
        <FormulaireConnexion disponibilite={disponibilite} deconnecte={parametres.deconnecte === "1"} />
      </div>
    </section>
  );
}
