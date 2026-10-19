/**
 * Mise en texte d'un résultat pour l'enregistrer sur l'appareil (fichier .txt).
 *
 * AUCUNE logique juridique : le texte reprend, sans les modifier, les éléments
 * déjà affichés (citations mot pour mot, références, lectures signalées comme
 * telles, démarches, points à vérifier). Rien n'est envoyé : le fichier est
 * fabriqué dans le navigateur.
 */

import type { VueReponse } from "./types";

const TRAIT = "-".repeat(60);

export function syntheseTexte(vue: VueReponse, date: Date = new Date()): string {
  const l: string[] = [];
  l.push("MON RECOURS CI — SYNTHÈSE DE CONSULTATION");
  l.push(`Enregistrée le ${date.toLocaleDateString("fr-FR")} — statut : ${vue.statut}`);
  l.push("Information juridique automatisée : ne remplace pas un avocat.");
  l.push(TRAIT);
  if (vue.demande) {
    l.push("VOTRE SITUATION (telle que vous l'avez décrite)");
    l.push(vue.demande);
    l.push(TRAIT);
  }
  if (vue.droit.length > 0) {
    l.push("CE QUE DISENT LES TEXTES (citations mot pour mot)");
    for (const r of vue.droit) {
      const source = vue.sources.find((s) => s.article === r.article && s.numeroTexte === r.numeroTexte);
      l.push(`• ${r.titre} — article ${r.article}${r.numeroTexte ? `, texte n° ${r.numeroTexte}` : ""}`);
      l.push(`  « ${r.citation} »`);
      if (r.lecture) l.push(`  En clair : ${r.lecture}`);
      if (source?.etatVerification) l.push(`  Vérification de la référence : ${source.etatVerification}`);
      if (source?.urlSource) l.push(`  Document officiel : ${source.urlSource}`);
    }
    l.push(TRAIT);
  }
  if (vue.applicationFaits && vue.applicationFaits.lignes.length > 0) {
    l.push("AU VU DE VOS RÉPONSES (lectures, pas des citations)");
    for (const x of vue.applicationFaits.lignes) {
      l.push(`• ${x.question} ${x.reponse === "oui" ? "Oui" : x.reponse === "non" ? "Non" : x.reponse}`);
      l.push(`  ${x.alerte ? "ATTENTION — " : ""}${x.lecture}`);
    }
    if (vue.applicationFaits.note) l.push(vue.applicationFaits.note);
    l.push(TRAIT);
  }
  if (vue.demarches.length > 0) {
    l.push("DÉMARCHES ENVISAGEABLES");
    vue.demarches.forEach((d, i) => l.push(`${i + 1}. ${d}`));
    l.push(TRAIT);
  }
  const verifier = [...vue.aVerifier];
  if (verifier.length > 0) {
    l.push("POINTS À VÉRIFIER");
    for (const v of verifier) l.push(`• ${v}`);
    l.push(TRAIT);
  }
  if (vue.verrous.length > 0) {
    l.push("UN PROFESSIONNEL DOIT INTERVENIR");
    for (const v of vue.verrous) l.push(`• ${v.motif}`);
    l.push(TRAIT);
  }
  if (vue.avertissement) l.push(vue.avertissement);
  return l.join("\n") + "\n";
}

/** Déclenche l'enregistrement d'un texte sur l'appareil, sans aucun envoi réseau. */
export function enregistrerTexte(nomFichier: string, contenu: string): void {
  const blob = new Blob([contenu], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const lien = document.createElement("a");
  lien.href = url;
  lien.download = nomFichier;
  document.body.appendChild(lien);
  lien.click();
  lien.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
