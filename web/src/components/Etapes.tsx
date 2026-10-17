const ETAPES = ["Décrire", "Préciser", "Résultat"] as const;

/** Progression du parcours : c'est une vraie séquence, d'où la numérotation. */
export function Etapes({ active }: { active: 0 | 1 | 2 }) {
  return (
    <nav aria-label="Progression" className="etapes">
      <ol>
        {ETAPES.map((nom, i) => (
          <li
            key={nom}
            className={i < active ? "etapes__faite" : i === active ? "etapes__active" : undefined}
            aria-current={i === active ? "step" : undefined}
          >
            <span className="etapes__num" aria-hidden="true">
              {i + 1}
            </span>
            <span>{nom}</span>
            {i < active ? <span className="visuellement-cache"> (terminé)</span> : null}
          </li>
        ))}
      </ol>
    </nav>
  );
}
