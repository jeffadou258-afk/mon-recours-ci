"use client";

import { useEffect, useRef, useState } from "react";

/** Sous-ensemble de l'API Web Speech dont on a besoin (non typée par TypeScript). */
interface ResultatReconnaissance {
  readonly isFinal: boolean;
  readonly 0: { readonly transcript: string };
}
interface EvenementReconnaissance {
  readonly resultIndex: number;
  readonly results: { readonly length: number; readonly [i: number]: ResultatReconnaissance };
}
interface Reconnaissance {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  onresult: ((e: EvenementReconnaissance) => void) | null;
  onerror: ((e: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
}
type ConstructeurReconnaissance = new () => Reconnaissance;

function constructeur(): ConstructeurReconnaissance | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: ConstructeurReconnaissance;
    webkitSpeechRecognition?: ConstructeurReconnaissance;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

const MESSAGES: Record<string, string> = {
  "not-allowed": "Le micro est refusé. Autorisez-le dans les réglages du navigateur, ou écrivez votre texte.",
  "service-not-allowed": "La dictée n'est pas autorisée sur cet appareil. Écrivez votre texte.",
  "no-speech": "Aucune parole entendue. Appuyez de nouveau et parlez près du téléphone.",
  network: "La dictée a besoin d'une connexion internet. Écrivez votre texte.",
  "audio-capture": "Aucun micro détecté sur cet appareil.",
};

/**
 * Dictée vocale : la personne parle, le texte reconnu s'ajoute à sa
 * description, qu'elle peut relire et corriger avant d'envoyer.
 *
 * Elle utilise la reconnaissance vocale INTÉGRÉE au navigateur. Le bouton
 * n'apparaît que si le navigateur la propose : sinon, rien ne change.
 */
export function BoutonDictee({ onTexte, desactive = false }: { onTexte: (texte: string) => void; desactive?: boolean }) {
  const [disponible, setDisponible] = useState(false);
  const [ecoute, setEcoute] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const reco = useRef<Reconnaissance | null>(null);

  useEffect(() => {
    setDisponible(constructeur() !== null);
    return () => reco.current?.stop();
  }, []);

  if (!disponible) return null;

  function basculer() {
    if (ecoute) {
      reco.current?.stop();
      return;
    }
    const C = constructeur();
    if (!C) return;
    const r = new C();
    r.lang = "fr-FR";
    r.continuous = true;
    r.interimResults = false;
    r.onresult = (e) => {
      let texte = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const res = e.results[i];
        if (res?.isFinal) texte += res[0].transcript;
      }
      if (texte.trim()) onTexte(texte.trim());
    };
    r.onerror = (e) => setMessage(MESSAGES[e.error] ?? "La dictée s'est interrompue. Vous pouvez réessayer ou écrire.");
    r.onend = () => setEcoute(false);
    reco.current = r;
    setMessage(null);
    try {
      r.start();
      setEcoute(true);
    } catch {
      setMessage("La dictée n'a pas pu démarrer. Écrivez votre texte.");
    }
  }

  return (
    <div className="dictee">
      <button
        type="button"
        className={`dictee__bouton${ecoute ? " dictee__bouton--actif" : ""}`}
        onClick={basculer}
        disabled={desactive}
        aria-pressed={ecoute}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
          <path
            fill="currentColor"
            d="M12 15a3 3 0 0 0 3-3V6a3 3 0 1 0-6 0v6a3 3 0 0 0 3 3Zm5-3a5 5 0 0 1-10 0H5a7 7 0 0 0 6 6.9V21h2v-2.1a7 7 0 0 0 6-6.9h-2Z"
          />
        </svg>
        {ecoute ? "J'écoute… appuyez pour arrêter" : "Dicter au lieu d'écrire"}
      </button>
      {ecoute ? <span className="dictee__onde" aria-hidden="true"><i /><i /><i /><i /></span> : null}
      <p className="dictee__note" role={message ? "alert" : undefined}>
        {message ?? "Parlez naturellement, puis relisez le texte avant d'envoyer."}
      </p>
    </div>
  );
}
