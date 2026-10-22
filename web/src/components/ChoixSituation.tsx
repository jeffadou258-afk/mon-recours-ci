"use client";

import { useId, useState } from "react";
import type { VueAiguillage } from "@/lib/types";

/**
 * Aiguillage : le moteur ne peut pas déterminer laquelle de plusieurs
 * procédures s'applique. Il ne les présente pas toutes comme applicables — il
 * demande au citoyen de désigner sa situation, en langage de tous les jours.
 *
 * Une seule sélection, et toujours une porte de sortie honnête : « aucune de ces
 * situations ». Sans elle, on forcerait la personne à se reconnaître dans une
 * case qui n'est pas la sienne.
 */
export function ChoixSituation({
  vue,
  envoi = false,
  onChoisir,
}: {
  vue: VueAiguillage;
  envoi?: boolean;
  onChoisir: (cle: string) => void;
}) {
  const [choix, setChoix] = useState<string | null>(null);
  const groupe = useId();

  return (
    <section className="resultat" aria-labelledby="titre-aiguillage">
      <header className="statut statut--attention">
        <h2 id="titre-aiguillage" tabIndex={-1} className="statut__titre">
          Une précision est nécessaire
        </h2>
        <p className="statut__explication">{vue.message}</p>
      </header>

      {vue.erreurSelection ? (
        <p className="message-erreur" role="alert">
          {vue.erreurSelection}
        </p>
      ) : null}

      <form
        onSubmit={(evenement) => {
          evenement.preventDefault();
          if (choix && !envoi) onChoisir(choix);
        }}
      >
        <fieldset className="bloc">
          <legend className="bloc__titre">{vue.question}</legend>
          {vue.pourquoi ? <p className="bloc__note">{vue.pourquoi}</p> : null}
          <ul className="liste-choix">
            {vue.options.map((option) => (
              <li key={option.cle}>
                <label className="liste-choix__ligne">
                  <input
                    type="radio"
                    name={groupe}
                    value={option.cle}
                    checked={choix === option.cle}
                    onChange={() => setChoix(option.cle)}
                  />
                  <span>{option.libelle}</span>
                </label>
              </li>
            ))}
            <li>
              <label className="liste-choix__ligne liste-choix__ligne--aucune">
                <input
                  type="radio"
                  name={groupe}
                  value="aucune"
                  checked={choix === "aucune"}
                  onChange={() => setChoix("aucune")}
                />
                <span>{vue.optionAucune}</span>
              </label>
            </li>
          </ul>
        </fieldset>

        <div className="actions">
          <button type="submit" className="bouton" disabled={!choix || envoi}>
            {envoi ? "Envoi…" : "Continuer"}
          </button>
        </div>
      </form>

      {vue.avertissement ? <p className="bloc__note">{vue.avertissement}</p> : null}
    </section>
  );
}
