"use client";

import { useState } from "react";
import type { VueReponse } from "@/lib/types";
import { supprimerConsultation } from "@/lib/client/api";
import { enregistrerTexte, syntheseTexte } from "@/lib/synthese";

/**
 * Ce que la personne peut faire de sa consultation : l'enregistrer sur son
 * appareil (texte ou PDF via l'impression), ou la supprimer du serveur.
 * Tout est réel : aucun bouton n'est décoratif.
 */
export function ActionsConsultation({ reponse }: { reponse: VueReponse | null }) {
  const [suppression, setSuppression] = useState<"repos" | "confirmer" | "encours" | "faite" | "echec">("repos");
  const jour = new Date().toISOString().slice(0, 10);

  async function supprimer() {
    setSuppression("encours");
    const r = await supprimerConsultation();
    setSuppression(r.ok ? "faite" : "echec");
  }

  return (
    <section className="bloc bloc--actions" aria-labelledby="titre-garder">
      <h2 id="titre-garder">Garder ou effacer cette consultation</h2>
      {reponse ? (
        <div className="actions">
          <button
            type="button"
            className="bouton bouton--secondaire"
            onClick={() => enregistrerTexte(`mon-recours-ci-synthese-${jour}.txt`, syntheseTexte(reponse))}
          >
            Enregistrer la synthèse (texte)
          </button>
          {reponse.brouillon?.disponible && reponse.brouillon.texte ? (
            <button
              type="button"
              className="bouton bouton--secondaire"
              onClick={() => enregistrerTexte(`mon-recours-ci-brouillon-${jour}.txt`, reponse.brouillon!.texte!)}
            >
              Enregistrer le brouillon (texte)
            </button>
          ) : null}
          <button type="button" className="bouton bouton--secondaire" onClick={() => window.print()}>
            Imprimer ou enregistrer en PDF
          </button>
        </div>
      ) : null}
      <p className="info" data-conservation="24h">
        <strong>Consultation temporaire.</strong> Elle sera supprimée du serveur 24 heures au plus après son début,
        et ne pourra pas être retrouvée ensuite. Enregistrez dès maintenant ce dont vous avez besoin.
      </p>
      <p className="bloc__note">
        Les fichiers sont fabriqués sur votre appareil : rien n&apos;est envoyé. Une fois enregistrés, ils restent sur
        votre appareil et ne sont pas concernés par la suppression. Pour un PDF, choisissez « Enregistrer en PDF »
        dans la fenêtre d&apos;impression.
      </p>

      {suppression === "faite" ? (
        <p className="info" role="status">
          Votre consultation a été supprimée du serveur. Ce qui est encore affiché disparaîtra à la fermeture de la
          page.
        </p>
      ) : suppression === "confirmer" || suppression === "encours" ? (
        <div className="confirmation" role="group" aria-label="Confirmer la suppression">
          <p>Supprimer définitivement votre récit et vos réponses du serveur ? Cette action ne peut pas être annulée.</p>
          <div className="actions">
            <button type="button" className="bouton bouton--danger" onClick={() => void supprimer()} disabled={suppression === "encours"}>
              {suppression === "encours" ? "Suppression…" : "Oui, supprimer"}
            </button>
            <button type="button" className="bouton bouton--secondaire" onClick={() => setSuppression("repos")}>
              Annuler
            </button>
          </div>
        </div>
      ) : (
        <>
          {suppression === "echec" ? (
            <p className="info" role="alert">
              La suppression n&apos;a pas abouti (session expirée ou service indisponible). Votre consultation sera
              effacée automatiquement du serveur 24 heures au plus après son début.
            </p>
          ) : null}
          <button type="button" className="lien-bouton" onClick={() => setSuppression("confirmer")}>
            Supprimer cette consultation du serveur
          </button>
        </>
      )}
    </section>
  );
}
