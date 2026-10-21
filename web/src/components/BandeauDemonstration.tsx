/**
 * Bandeau de démonstration — affiché quand `MONRECOURS_MODE=demo`.
 *
 * Il n'est pas décoratif : sans lui, une réponse figée passerait pour une
 * réponse juridique calculée. Le texte dit ce qui est faux (aucun moteur, aucune
 * donnée enregistrée) et ce qui reste vrai (les captures viennent du moteur réel,
 * sur une demande fictive).
 */

export function BandeauDemonstration() {
  return (
    <div
      role="status"
      aria-live="polite"
      style={{
        background: "var(--ambre-pale, #fff6e0)",
        borderBottom: "2px solid var(--ambre, #a86400)",
        color: "var(--encre, #1b1b1b)",
        padding: "0.65rem 1rem",
        fontSize: "0.9rem",
        lineHeight: 1.45,
        textAlign: "center",
      }}
    >
      <strong>DÉMONSTRATION PUBLIQUE</strong> — les réponses sont des{" "}
      <strong>exemples figés</strong>, enregistrés sur une demande fictive. Aucun
      moteur juridique n&apos;est interrogé, aucune donnée n&apos;est enregistrée,
      aucun document n&apos;est produit pour vous.{" "}
      <strong>Le corpus juridique complet n&apos;est pas connecté.</strong> Ceci
      n&apos;est pas un conseil juridique.
    </div>
  );
}
