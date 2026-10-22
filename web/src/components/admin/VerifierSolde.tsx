"use client";

import { useState } from "react";

/**
 * Vérification réelle du solde du fournisseur.
 *
 * Le bouton ne « réactive » rien par lui-même : il demande au serveur
 * d'interroger l'API officielle. Le message affiché est celui du serveur, et un
 * échec n'est jamais présenté comme un succès.
 */
export function VerifierSolde() {
  const [enCours, setEnCours] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [succes, setSucces] = useState(false);

  async function verifier() {
    if (enCours) return; // double clic : une seule requête
    setEnCours(true);
    setMessage(null);
    try {
      const reponse = await fetch("/api/admin/solde", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      });
      const corps = (await reponse.json()) as {
        ok?: boolean;
        data?: { reactive?: boolean; message?: string; manques?: string[] };
        erreur?: { message?: string };
      };
      if (!reponse.ok || corps.ok !== true) {
        setSucces(false);
        setMessage(corps.erreur?.message ?? "Vérification impossible : l'incident reste ouvert.");
        return;
      }
      const reactive = corps.data?.reactive === true;
      setSucces(reactive);
      const complement =
        corps.data?.manques && corps.data.manques.length > 0
          ? ` Configuration manquante : ${corps.data.manques.join(", ")}.`
          : "";
      setMessage((corps.data?.message ?? "") + complement);
      // Rechargement réel pour que le bandeau reflète l'état du serveur.
      if (reactive && typeof window !== "undefined") window.location.reload();
    } catch {
      setSucces(false);
      setMessage("Vérification impossible : l'incident reste ouvert.");
    } finally {
      setEnCours(false);
    }
  }

  return (
    <div className="verification-solde">
      <button
        type="button"
        className="bouton bouton--secondaire"
        onClick={verifier}
        disabled={enCours}
        aria-busy={enCours}
      >
        {enCours ? "Vérification en cours…" : "Vérifier le solde et réactiver DeepSeek"}
      </button>
      {message ? (
        <p
          className={succes ? "verification-solde__resultat" : "verification-solde__resultat verification-solde__resultat--refus"}
          role={succes ? "status" : "alert"}
        >
          {message}
        </p>
      ) : null}
    </div>
  );
}
