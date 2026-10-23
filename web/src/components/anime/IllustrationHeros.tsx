/**
 * Animation de l'accueil : une situation dite avec ses mots devient une fiche
 * appuyée sur un texte de loi. Trois scènes se succèdent en boucle.
 *
 * Les intitulés sont ceux de fiches RÉELLES du catalogue ; aucun numéro
 * d'article n'est affiché (rien d'inventé). Purement décorative : masquée aux
 * lecteurs d'écran, figée sur la première scène si les mouvements sont réduits.
 */
export const SCENES = [
  { recit: "Mon bailleur refuse de me rendre ma caution.", fiche: "Dépôt de garantie (caution)", domaine: "Logement" },
  {
    recit: "Le père de mon enfant ne paie plus la pension.",
    fiche: "Pension alimentaire fixée par le juge et non payée",
    domaine: "Famille",
  },
  { recit: "On me réclame une dette que je conteste.", fiche: "Injonction de payer : délai d'opposition", domaine: "Dettes" },
];

export function IllustrationHeros() {
  return (
    <div className="illus" aria-hidden="true">
      {SCENES.map((s, i) => (
        <div key={s.fiche} className="illus__scene" style={{ ["--i" as string]: String(i) }}>
          <div className="illus__bulle">
            <span className="illus__qui">Vous</span>
            <p>« {s.recit} »</p>
          </div>
          <div className="illus__fleche">
            <span />
          </div>
          <div className="illus__carte">
            <span className="illus__para">§</span>
            <span className="illus__domaine">{s.domaine}</span>
            <strong className="illus__fiche">{s.fiche}</strong>
            <span className="illus__lignes">
              <i />
              <i />
              <i />
            </span>
            <span className="illus__badge">Texte officiel cité mot pour mot</span>
          </div>
        </div>
      ))}
    </div>
  );
}
