import type { Metadata } from "next";

export const metadata: Metadata = { title: "Hors ligne" };

export default function PageHorsLigne() {
  return (
    <section className="prose">
      <h1>Vous êtes hors ligne</h1>
      <p>
        Mon Recours CI a besoin d&apos;une connexion pour consulter son moteur juridique. Aucune
        réponse n&apos;est enregistrée sur votre appareil.
      </p>
      <p>
        <a href="/" className="bouton">
          Réessayer
        </a>
      </p>
    </section>
  );
}
