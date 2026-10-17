"use client";

import { useState } from "react";

/** Copie un texte dans le presse-papiers ; à défaut, sélectionne la zone ciblée. */
export function BoutonCopier({ texte, cible, libelle = "Copier le brouillon" }: { texte: string; cible: string; libelle?: string }) {
  const [etat, setEtat] = useState<"repos" | "copie" | "selection">("repos");

  function selectionner() {
    const zone = document.getElementById(cible);
    if (!zone) return;
    const plage = document.createRange();
    plage.selectNodeContents(zone);
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(plage);
    setEtat("selection");
  }

  async function copier() {
    try {
      await navigator.clipboard.writeText(texte);
      setEtat("copie");
    } catch {
      selectionner();
    }
  }

  return (
    <span className="copier">
      <button type="button" className="bouton bouton--secondaire" onClick={() => void copier()}>
        {libelle}
      </button>
      <span className="copier__etat" role="status" aria-live="polite">
        {etat === "copie" ? "Copié." : etat === "selection" ? "Texte sélectionné : copiez-le avec votre appareil." : ""}
      </span>
    </span>
  );
}
