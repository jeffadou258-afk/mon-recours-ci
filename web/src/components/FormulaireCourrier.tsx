"use client";

/**
 * Complément du courrier.
 *
 * Le moteur ne devine ni le nom, ni l'adresse, ni les pièces jointes : il les
 * demande. Ce formulaire transmet ce que la personne accepte de donner, puis
 * affiche le courrier régénéré. Rien n'est envoyé, rien n'est enregistré hors
 * du dossier de la consultation.
 */

import { useState } from "react";
import { redigerCourrier } from "@/lib/client/api";
import type { VueBrouillon, VueChampCourrier } from "@/lib/types";
import { BoutonCopier } from "./BoutonCopier";

export function FormulaireCourrier({ brouillon }: { brouillon: VueBrouillon }) {
  const [texte, setTexte] = useState<string | null>(brouillon.texte);
  const [champs, setChamps] = useState<VueChampCourrier[]>(brouillon.champsACompleter ?? []);
  const [pdf, setPdf] = useState<boolean>(brouillon.pdfDisponible);
  const [valeurs, setValeurs] = useState<Record<string, string>>({});
  const [erreur, setErreur] = useState<string | null>(null);
  const [envoi, setEnvoi] = useState(false);

  async function soumettre(evenement: React.FormEvent) {
    evenement.preventDefault();
    const renseignes = Object.fromEntries(
      Object.entries(valeurs).filter(([, valeur]) => valeur.trim().length > 0),
    );
    if (Object.keys(renseignes).length === 0) {
      setErreur("Renseignez au moins une information, ou laissez le brouillon tel quel.");
      return;
    }
    setEnvoi(true);
    setErreur(null);
    const resultat = await redigerCourrier(renseignes);
    setEnvoi(false);
    if (!resultat.ok) {
      setErreur(resultat.erreur.message);
      return;
    }
    setTexte(resultat.data.texte);
    setChamps(resultat.data.champsACompleter);
    setPdf(resultat.data.pdfDisponible);
    setValeurs({});
  }

  return (
    <>
      {texte ? (
        <>
          <pre id="texte-brouillon" className="brouillon" tabIndex={0}>
            {texte}
          </pre>
          <BoutonCopier texte={texte} cible="texte-brouillon" />
          {pdf ? (
            <p className="bloc__note">
              {/* Le PDF est servi par le serveur pour CE dossier, identifié par le cookie
                  signé : le lien ne contient aucun identifiant ni chemin. */}
              <a className="bouton bouton--secondaire" href="/api/courrier/telecharger" download>
                Télécharger le courrier en PDF
              </a>
            </p>
          ) : null}
        </>
      ) : null}

      {champs.length > 0 ? (
        <form onSubmit={soumettre} className="courrier" aria-labelledby="titre-completer-courrier">
          <h3 id="titre-completer-courrier">Compléter le courrier</h3>
          <p className="bloc__note">
            Ces informations ne sont pas devinées : elles viennent de vous. Vous pouvez n&apos;en
            renseigner qu&apos;une partie — le reste sera de nouveau demandé.
          </p>
          {champs.map((champ) => (
            <label key={champ.champ} className="champ">
              <span>{champ.libelle}</span>
              <textarea
                name={champ.champ}
                rows={champ.champ === "pieces" ? 3 : 2}
                maxLength={1000}
                placeholder={champ.exemple ?? undefined}
                value={valeurs[champ.champ] ?? ""}
                onChange={(evenement) =>
                  setValeurs((actuels) => ({ ...actuels, [champ.champ]: evenement.target.value }))
                }
              />
            </label>
          ))}
          {erreur ? (
            <p className="formulaire__erreur" role="alert">
              {erreur}
            </p>
          ) : null}
          <div className="actions">
            <button type="submit" className="bouton" disabled={envoi}>
              {envoi ? "Rédaction…" : "Rédiger le courrier"}
            </button>
          </div>
        </form>
      ) : (
        <p className="bloc__note">
          Toutes les informations utiles sont renseignées. Relisez le courrier avant de l&apos;envoyer
          vous-même.
        </p>
      )}
    </>
  );
}
