"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import type { ErreurApi, VueAiguillage, VueClarification, VueOuverture, VueReponse } from "@/lib/types";
import { envoyerReponses, ouvrirDossier } from "@/lib/client/api";
import { LONGUEUR_MAX_DEMANDE, validerDemande } from "@/lib/validation";
import { ActionsConsultation } from "./ActionsConsultation";
import { ChoixSituation } from "./ChoixSituation";
import { Clarification } from "./Clarification";
import { Etapes } from "./Etapes";
import { Chargement, MessageErreur } from "./MessageErreur";
import { VueRefusee, VueResultat, VueSansFiche } from "./Resultats";

/** Amorces de rédaction : elles remplissent la zone de texte, la personne les modifie. */
const AMORCES = [
  "Mon bailleur refuse de me rendre ma caution depuis que j'ai quitté le logement.",
  "Mon propriétaire veut augmenter mon loyer.",
  "On veut m'expulser de mon logement.",
];

type Etat =
  | { phase: "saisie" }
  | { phase: "ouverture" }
  | { phase: "clarification"; vue: VueClarification; envoi: boolean }
  | { phase: "aiguillage"; vue: VueAiguillage; envoi: boolean }
  | { phase: "fin"; ouverture: VueOuverture; reponse: VueReponse | null };

/** Parcours complet : décrire → préciser → résultat. Tout l'état vit en mémoire. */
export function Parcours({
  demo = false,
  iaExterne = true,
}: {
  demo?: boolean;
  /**
   * La couche de langage (DeepSeek) est-elle active ? Par défaut VRAI : sans
   * preuve du contraire, on n'affirme jamais qu'aucune IA n'est utilisée.
   */
  iaExterne?: boolean;
} = {}) {
  const [etat, setEtat] = useState<Etat>({ phase: "saisie" });
  const [demande, setDemande] = useState("");
  const [erreurSaisie, setErreurSaisie] = useState<string | null>(null);
  const [erreur, setErreur] = useState<{ e: ErreurApi; reessayer?: () => void } | null>(null);
  const derniereReponse = useRef<Record<string, string | null>>({});
  const zone = useRef<HTMLDivElement>(null);

  // À chaque changement d'étape, le focus va au titre de la nouvelle étape
  // (lecteurs d'écran et clavier) et la page remonte en haut sur mobile.
  const tourClarification = etat.phase === "clarification" ? etat.vue.tour : 0;
  useEffect(() => {
    const titre = zone.current?.querySelector<HTMLElement>("h2[tabindex='-1']");
    if (titre && etat.phase !== "saisie") {
      titre.focus({ preventScroll: true });
      titre.scrollIntoView?.({ block: "start", behavior: "auto" });
    }
  }, [etat.phase, tourClarification]);

  async function lancerOuverture(texte: string) {
    setErreur(null);
    setEtat({ phase: "ouverture" });
    const r = await ouvrirDossier(texte);
    if (!r.ok) {
      setEtat({ phase: "saisie" });
      setErreur({ e: r.erreur, reessayer: () => void lancerOuverture(texte) });
      return;
    }
    if (r.data.etape === "clarification") {
      setEtat({ phase: "clarification", vue: r.data, envoi: false });
    } else if (r.data.etape === "aiguillage") {
      setEtat({ phase: "aiguillage", vue: r.data, envoi: false });
    } else {
      setEtat({ phase: "fin", ouverture: r.data, reponse: null });
    }
  }

  function soumettreDemande(e: FormEvent) {
    e.preventDefault();
    const v = validerDemande(demande);
    if (!v.ok) {
      setErreurSaisie(v.message);
      return;
    }
    setErreurSaisie(null);
    void lancerOuverture(v.valeur);
  }

  async function lancerReponses(
    vue: VueClarification | VueAiguillage,
    reponses: Record<string, string | null>,
  ) {
    derniereReponse.current = reponses;
    setErreur(null);
    setEtat(
      vue.etape === "aiguillage"
        ? { phase: "aiguillage", vue, envoi: true }
        : { phase: "clarification", vue, envoi: true },
    );
    const r = await envoyerReponses(reponses);
    if (!r.ok) {
      setEtat(
        vue.etape === "aiguillage"
          ? { phase: "aiguillage", vue, envoi: false }
          : { phase: "clarification", vue, envoi: false },
      );
      setErreur({ e: r.erreur, reessayer: () => void lancerReponses(vue, derniereReponse.current) });
      return;
    }
    if (r.data.etape === "aiguillage") {
      // Sélection invalide : on repose la question, sans conclure.
      setEtat({ phase: "aiguillage", vue: r.data, envoi: false });
      return;
    }
    if (r.data.etape === "clarification") {
      // Tour suivant : de nouvelles questions (réponse contraire au récit, ou
      // question ouverte par une réponse précédente).
      setEtat({ phase: "clarification", vue: r.data, envoi: false });
      return;
    }
    setEtat({ phase: "fin", ouverture: vue, reponse: r.data });
  }

  function recommencer() {
    setErreur(null);
    setErreurSaisie(null);
    setDemande("");
    setEtat({ phase: "saisie" });
  }

  const etapeActive: 0 | 1 | 2 =
    etat.phase === "saisie" || etat.phase === "ouverture" ? 0 : etat.phase === "clarification" ? 1 : 2;

  return (
    <div className="parcours" ref={zone}>
      <Etapes active={etapeActive} />

      {erreur ? (
        <MessageErreur erreur={erreur.e} onReessayer={erreur.reessayer} onRecommencer={recommencer} />
      ) : null}

      {etat.phase === "saisie" || etat.phase === "ouverture" ? (
        <form className="formulaire" onSubmit={soumettreDemande} noValidate aria-busy={etat.phase === "ouverture"}>
          <h1 className="titre-etape">Décrivez votre situation</h1>
          <label htmlFor="demande" className="formulaire__label">
            Expliquez avec vos mots ce qui vous arrive
          </label>
          <p id="aide-demande" className="formulaire__aide">
            Qui est concerné, ce qui s&apos;est passé, depuis quand. Inutile d&apos;indiquer votre nom,
            votre numéro de téléphone ou votre adresse : ils ne servent pas à l&apos;analyse.
          </p>
          {etat.phase === "saisie" ? (
            <div className="amorces">
              <p className="amorces__titre">Pour commencer, vous pouvez partir d&apos;un exemple :</p>
              <ul>
                {AMORCES.map((a) => (
                  <li key={a}>
                    <button
                      type="button"
                      className="amorce"
                      onClick={() => {
                        setDemande(a);
                        setErreurSaisie(null);
                        document.getElementById("demande")?.focus();
                      }}
                    >
                      {a}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
          <textarea
            id="demande"
            name="demande"
            rows={7}
            value={demande}
            maxLength={LONGUEUR_MAX_DEMANDE}
            onChange={(e) => setDemande(e.target.value)}
            aria-describedby={`aide-demande compteur-demande${erreurSaisie ? " erreur-demande" : ""}`}
            aria-invalid={erreurSaisie ? true : undefined}
            disabled={etat.phase === "ouverture"}
            placeholder="Exemple : mon bailleur refuse de me rendre ma caution depuis que j'ai quitté l'appartement il y a deux mois."
          />
          <div className="formulaire__pied">
            <span id="compteur-demande" className="compteur">
              {demande.length} / {LONGUEUR_MAX_DEMANDE} caractères
            </span>
          </div>
          {erreurSaisie ? (
            <p id="erreur-demande" className="formulaire__erreur" role="alert">
              {erreurSaisie}
            </p>
          ) : null}
          {etat.phase === "ouverture" ? (
            <Chargement
              message={
                demo
                  ? "Chargement du scénario de démonstration…"
                  : "Recherche des textes qui correspondent à votre situation…"
              }
            />
          ) : (
            <div className="actions">
              <button type="submit" className="bouton">
                Analyser ma situation
              </button>
            </div>
          )}
          {demo ? (
            <p className="formulaire__confidentialite">
              <strong>Démonstration publique :</strong> votre saisie sert uniquement à parcourir un
              scénario fictif. Aucune analyse juridique réelle n&apos;est effectuée. N&apos;entrez
              aucune information personnelle ou confidentielle.
            </p>
          ) : (
            // Couche de langage active : aucun avis affiché sous le formulaire
            // (décision du propriétaire). L'ancien avis « aucune IA » serait faux.
            iaExterne ? null : (
              <p className="formulaire__confidentialite" data-confidentialite="moteur-seul">
                Votre description est transmise au moteur juridique de Mon Recours CI uniquement, qui en
                garde une trace sur son serveur pour pouvoir justifier sa réponse. Elle n&apos;est envoyée
                à aucun service tiers ni à aucun modèle d&apos;intelligence artificielle.
              </p>
            )
          )}
        </form>
      ) : null}

      {etat.phase === "clarification" ? (
        <>
          <Clarification
            key={etat.vue.tour}
            vue={etat.vue}
            envoi={etat.envoi}
            onEnvoyer={(reponses) => void lancerReponses(etat.vue, reponses)}
          />
          {etat.envoi ? (
            <Chargement
              message={
                demo
                  ? "Chargement de la suite du scénario de démonstration…"
                  : "Le moteur vérifie les textes et prépare le résultat…"
              }
            />
          ) : null}
        </>
      ) : null}

      {etat.phase === "aiguillage" ? (
        <>
          <ChoixSituation
            vue={etat.vue}
            envoi={etat.envoi}
            onChoisir={(cle) => void lancerReponses(etat.vue, { aiguillage: cle })}
          />
          {etat.envoi ? (
            <Chargement message="Le moteur reprend avec la situation que vous avez indiquée…" />
          ) : null}
        </>
      ) : null}

      {etat.phase === "fin" ? (
        <>
          {etat.reponse ? (
            <VueResultat
              vue={etat.reponse}
              urgence={etat.ouverture.etape === "clarification" ? etat.ouverture.urgence : null}
            />
          ) : etat.ouverture.etape === "hors_catalogue" ? (
            <VueSansFiche vue={etat.ouverture} />
          ) : etat.ouverture.etape === "refus" ? (
            <VueRefusee vue={etat.ouverture} />
          ) : null}
          <ActionsConsultation reponse={etat.reponse} />
          <div className="actions actions--fin">
            <button type="button" className="bouton" onClick={recommencer}>
              Nouvelle demande
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}
