"use client";

import { useState, type FormEvent } from "react";
import type { VueClarification } from "@/lib/types";
import { LONGUEUR_MAX_REPONSE } from "@/lib/validation";
import { BandeauUrgence, EncadreVerrous } from "./Alertes";
import { BadgeVerification } from "./Badges";

type Choix = "oui" | "non" | "inconnu" | "";

interface Saisie {
  choix: Choix;
  precision: string;
}

/**
 * Compose la réponse transmise au moteur. « Je ne sais pas » sans précision
 * envoie `null` : le moteur enregistre alors le fait comme manquant, au lieu
 * d'une réponse inventée.
 */
export function composerReponse(s: Saisie): string | null {
  const precision = s.precision.trim();
  if (s.choix === "oui" || s.choix === "non") {
    return precision ? `${s.choix}, ${precision}` : s.choix;
  }
  return precision || null;
}

interface Props {
  vue: VueClarification;
  envoi: boolean;
  onEnvoyer: (reponses: Record<string, string | null>) => void;
}

export function Clarification({ vue, envoi, onEnvoyer }: Props) {
  const [saisies, setSaisies] = useState<Record<string, Saisie>>(() =>
    Object.fromEntries(vue.questions.map((q) => [q.cle, { choix: "", precision: "" }])),
  );

  function modifier(cle: string, partiel: Partial<Saisie>) {
    setSaisies((s) => ({ ...s, [cle]: { ...(s[cle] ?? { choix: "", precision: "" }), ...partiel } }));
  }

  function soumettre(e: FormEvent) {
    e.preventDefault();
    const reponses: Record<string, string | null> = {};
    for (const q of vue.questions) {
      reponses[q.cle] = composerReponse(saisies[q.cle] ?? { choix: "", precision: "" });
    }
    onEnvoyer(reponses);
  }

  return (
    <section aria-labelledby="titre-clarification">
      <h2 id="titre-clarification" tabIndex={-1} className="titre-etape">
        {vue.questions.length > 0 ? "Quelques précisions" : "Textes repérés"}
      </h2>

      <BandeauUrgence urgence={vue.urgence} />
      <EncadreVerrous verrous={vue.verrous} />

      <section className="bloc" aria-labelledby="titre-fiches">
        <h3 id="titre-fiches">Textes qui pourraient concerner votre situation</h3>
        {vue.fiches.length === 0 ? (
          <p className="vide">Aucun texte repéré.</p>
        ) : (
          <ul className="fiches">
            {vue.fiches.map((f, i) => (
              <li key={`${f.numeroTexte}-${f.article}-${i}`}>
                <span className="fiches__titre">{f.titre}</span>
                <span className="fiches__ref">
                  Article {f.article}
                  {f.numeroTexte ? `, texte n° ${f.numeroTexte}` : ""}
                </span>
                <BadgeVerification etat={f.etatVerification} />
              </li>
            ))}
          </ul>
        )}
        <p className="bloc__note">
          Ces textes sont repérés automatiquement. Le moteur confirmera ceux qu&apos;il retient après vos
          réponses.
        </p>
      </section>

      <form className="formulaire" onSubmit={soumettre} noValidate>
        {vue.questions.length > 0 ? (
          <p>Vos réponses permettent de vérifier que ces textes s&apos;appliquent bien à vous.</p>
        ) : (
          <p>Aucune précision n&apos;est nécessaire. Vous pouvez obtenir le résultat.</p>
        )}
        {vue.questions.map((q) => {
          const s = saisies[q.cle] ?? { choix: "", precision: "" };
          const idPrecision = `precision-${q.cle}`;
          return (
            <fieldset key={q.cle} className="question">
              <legend>{q.question}</legend>
              <div className="choix" role="radiogroup">
                {(
                  [
                    ["oui", "Oui"],
                    ["non", "Non"],
                    ["inconnu", "Je ne sais pas"],
                  ] as const
                ).map(([valeur, libelle]) => (
                  <label key={valeur} className="choix__option">
                    <input
                      type="radio"
                      name={`q-${q.cle}`}
                      value={valeur}
                      checked={s.choix === valeur}
                      onChange={() => modifier(q.cle, { choix: valeur })}
                    />
                    <span>{libelle}</span>
                  </label>
                ))}
              </div>
              <label htmlFor={idPrecision} className="question__precision">
                Précision (facultatif)
              </label>
              <textarea
                id={idPrecision}
                rows={2}
                maxLength={LONGUEUR_MAX_REPONSE}
                value={s.precision}
                onChange={(e) => modifier(q.cle, { precision: e.target.value })}
              />
            </fieldset>
          );
        })}
        <div className="actions">
          <button type="submit" className="bouton" disabled={envoi} aria-disabled={envoi}>
            {envoi ? "Analyse en cours…" : "Obtenir le résultat"}
          </button>
        </div>
      </form>

      {vue.noteCorpus ? <p className="bloc__note">{vue.noteCorpus}</p> : null}
    </section>
  );
}
