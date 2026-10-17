import type { VueRegleDroit, VueSource } from "@/lib/types";
import { libelleOrigineTexte, presentationVerification } from "@/lib/libelles";
import { BadgeVerification } from "./Badges";

interface Props {
  regle: VueRegleDroit;
  source: VueSource | null;
}

/**
 * Le moteur transmet des extraits limités (environ 180 caractères) qui peuvent
 * s'arrêter au milieu d'un mot. On ne touche pas au texte : on signale la coupure
 * par « […] », hors de la chaîne fournie, selon l'usage typographique.
 */
export function semblerTronquee(citation: string): boolean {
  return !/[.;:!?»)"]\s*$/.test(citation.trim());
}

function empreinteCourte(sha: string): string {
  const brut = sha.replace(/^sha256:/, "");
  return brut.length > 16 ? `${brut.slice(0, 8)}…${brut.slice(-8)}` : brut;
}

/**
 * Citation d'un article, telle que le moteur la fournit.
 * Le texte entre guillemets est reproduit sans aucune retouche ; la « lecture »
 * est présentée séparément comme une reformulation, jamais comme le texte.
 */
export function CarteCitation({ regle, source }: Props) {
  const etat = source?.etatVerification ?? "NON_VERIFIE";
  const origine = source?.origineTexte ?? null;
  const recoupe = source?.recoupe ?? false;
  const niveau = presentationVerification(etat, origine, recoupe).niveau;
  const tronquee = semblerTronquee(regle.citation);
  const idTitre = `citation-${regle.numeroTexte ?? "x"}-${regle.article}`.replace(/[^a-zA-Z0-9-]/g, "-");

  return (
    <article className={`citation citation--${niveau}`} aria-labelledby={idTitre}>
      <header className="citation__entete">
        <h3 id={idTitre} className="citation__titre">
          <span className="citation__article">Art. {regle.article}</span>
          <span className="citation__sujet">{regle.titre}</span>
        </h3>
        <BadgeVerification etat={etat} origine={origine} recoupe={recoupe} />
      </header>

      <p className="citation__texte-officiel">
        {source?.reference ?? (regle.numeroTexte ? `Texte n° ${regle.numeroTexte}` : "Texte non identifié")}
      </p>

      <figure className="citation__extrait">
        <blockquote lang="fr">
          <p>
            « {regle.citation}
            {tronquee ? (
              <span className="citation__coupure" aria-label="extrait interrompu">
                {" "}
                […]
              </span>
            ) : null}{" "}
            »
          </p>
        </blockquote>
        <figcaption>
          {tronquee
            ? "Début de l'article, reproduit mot pour mot. Le texte complet figure dans le document officiel."
            : "Extrait reproduit mot pour mot depuis le corpus du service."}
        </figcaption>
      </figure>

      {regle.noteLecture ? <p className="citation__note">{regle.noteLecture}</p> : null}

      {regle.lecture ? (
        <div className="citation__lecture">
          <h4>En termes simples</h4>
          <p>{regle.lecture}</p>
          <p className="citation__lecture-avert">Reformulation : seul le texte cité ci-dessus fait foi.</p>
        </div>
      ) : null}

      <details className="citation__provenance">
        <summary>Provenance du texte</summary>
        {source ? (
          <dl>
            <div>
              <dt>Vérification</dt>
              <dd>{presentationVerification(etat, origine, recoupe).detail}</dd>
            </div>
            <div>
              <dt>Lecture</dt>
              <dd>{libelleOrigineTexte(origine, recoupe, source.confianceOcr)}</dd>
            </div>
            {source.sha256 ? (
              <div>
                <dt>Empreinte</dt>
                <dd>
                  <code title={source.sha256}>{empreinteCourte(source.sha256)}</code>
                </dd>
              </div>
            ) : null}
            <div>
              <dt>Document</dt>
              <dd>
                {source.urlSource ? (
                  <a href={source.urlSource} target="_blank" rel="noopener noreferrer">
                    Ouvrir le document officiel
                    <span className="visuellement-cache"> (nouvel onglet)</span>
                  </a>
                ) : (
                  "Adresse du document non fournie"
                )}
              </dd>
            </div>
            {source.limites ? (
              <div>
                <dt>Limites</dt>
                <dd>{source.limites}</dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <p>Le moteur n&apos;a pas transmis la provenance de ce texte : considérez-le comme non vérifié.</p>
        )}
      </details>
    </article>
  );
}

/** Associe chaque règle à sa source (même article et même numéro de texte). */
export function trouverSource(regle: VueRegleDroit, sources: VueSource[]): VueSource | null {
  return (
    sources.find(
      (s) => s.article === regle.article && (s.numeroTexte ?? null) === (regle.numeroTexte ?? null),
    ) ?? null
  );
}
