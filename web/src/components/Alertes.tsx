import type { VueUrgence, VueVerrou } from "@/lib/types";
import { NUMEROS_URGENCE } from "@/lib/libelles";

/** Bandeau d'urgence : affiché seulement si le moteur détecte une urgence. */
export function BandeauUrgence({ urgence }: { urgence: VueUrgence | null }) {
  if (!urgence || urgence.niveau === "NORMALE") return null;
  const critique = urgence.niveau === "CRITIQUE";
  return (
    <section
      className={`alerte ${critique ? "alerte--critique" : "alerte--elevee"}`}
      role={critique ? "alert" : "status"}
      aria-labelledby="titre-urgence"
    >
      <h2 id="titre-urgence" className="alerte__titre">
        {critique ? "Votre sécurité passe avant tout" : "Situation à traiter rapidement"}
      </h2>
      {/* `consigne` est une instruction interne au moteur : on affiche un texte destiné à la personne. */}
      <p>
        {critique
          ? "Si vous ou quelqu'un d'autre êtes en danger, contactez les secours maintenant. Les informations juridiques peuvent attendre."
          : "Votre description évoque une situation où un délai peut compter. Contactez rapidement une personne qualifiée."}
      </p>
      {urgence.declencheurs.length > 0 ? (
        <p className="alerte__detail">
          Repéré dans votre description :{" "}
          {urgence.declencheurs.map((d) => d.libelle).join(", ")}.
        </p>
      ) : null}
      {critique ? (
        <div className="alerte__numeros">
          <p>En cas de danger immédiat, appelez :</p>
          <ul>
            {NUMEROS_URGENCE.map((n) => (
              <li key={n.service}>
                <span>{n.service}</span>
                {n.numeros.map((num) => (
                  <a key={num} href={`tel:${num}`} className="alerte__tel">
                    {num}
                  </a>
                ))}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}

/**
 * Verrous humains : situations où le moteur exige une décision humaine avant
 * toute action. Encadré non masquable (CLAUDE_HANDOFF.md, recommandation 4).
 */
export function EncadreVerrous({ verrous }: { verrous: VueVerrou[] }) {
  if (verrous.length === 0) return null;
  return (
    <section className="verrous" aria-labelledby="titre-verrous">
      <h2 id="titre-verrous" className="verrous__titre">
        Un professionnel doit intervenir avant toute démarche
      </h2>
      <ul>
        {verrous.map((v, i) => (
          <li key={`${v.code ?? "v"}-${i}`}>{v.motif}</li>
        ))}
      </ul>
      <p className="verrous__rappel">
        {verrous.find((v) => v.rappel)?.rappel ??
          "Aucune action ne doit être engagée sans l'avis d'une personne qualifiée."}
      </p>
    </section>
  );
}

export function OrientationHumaine() {
  return (
    <aside className="orientation" aria-labelledby="titre-orientation">
      <h2 id="titre-orientation">Faire relire votre situation</h2>
      <p>
        Ce service vous aide à comprendre quels textes existent. Pour agir, faites relire votre
        situation par une personne qualifiée : avocat, huissier de justice, notaire, ou une structure
        d&apos;aide juridique près de chez vous. Apportez vos documents (contrat, reçus, courriers).
      </p>
    </aside>
  );
}
