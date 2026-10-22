import type { Metadata } from "next";
import { BadgeVerification } from "@/components/Badges";
import { presentationStatut } from "@/lib/libelles";

export const metadata: Metadata = {
  title: "Comprendre les résultats",
};

const STATUTS = ["ANALYSE_CONFORME", "CONCLUSION_IMPOSSIBLE", "ANALYSE_REFUSEE", "REFUS"] as const;

export default function PageComprendre() {
  return (
    <article className="prose">
      <h1>Comprendre les résultats</h1>
      <p>
        Mon Recours CI ne fait pas de suppositions. Chaque résultat indique clairement ce qui est
        appuyé par un texte, et ce qui ne l&apos;est pas.
      </p>

      <h2>Les quatre résultats possibles</h2>
      <dl className="definitions">
        {STATUTS.map((s) => {
          const p = presentationStatut(s);
          return (
            <div key={s}>
              <dt>{p.titre}</dt>
              <dd>{p.explication}</dd>
            </div>
          );
        })}
      </dl>

      <h2>Le niveau de vérification d&apos;un texte</h2>
      <p>Chaque article cité porte une étiquette. Elle vient du moteur, jamais de l&apos;interface.</p>
      <dl className="definitions">
        <div>
          <dt>
            <BadgeVerification etat="VERIFIE" origine="CALQUE_TEXTE" />
          </dt>
          <dd>
            Le texte a été extrait du document officiel identifié par son empreinte numérique. Cela ne
            veut pas dire qu&apos;un juriste l&apos;a relu.
          </dd>
        </div>
        <div>
          <dt>
            <BadgeVerification etat="VERIFIE" origine="OCR_AUTO" recoupe={false} />
          </dt>
          <dd>
            Le document a été scanné puis lu automatiquement. Des erreurs de lecture sont possibles :
            comparez avec le document officiel avant de vous en servir.
          </dd>
        </div>
        <div>
          <dt>
            <BadgeVerification etat="PARTIELLEMENT_VERIFIE" />
          </dt>
          <dd>Une partie seulement des informations sur ce texte a été confirmée.</dd>
        </div>
        <div>
          <dt>
            <BadgeVerification etat="NON_VERIFIE" />
          </dt>
          <dd>Ne vous appuyez pas sur ce texte sans l&apos;avoir contrôlé.</dd>
        </div>
      </dl>

      <h2>Texte cité et explication</h2>
      <p>
        Le texte entre guillemets est reproduit mot pour mot. La partie « En termes simples » est une
        reformulation pour vous aider à lire : seul le texte cité fait foi.
      </p>

      <h2>Combien de temps votre consultation est conservée</h2>
      <p>
        Une consultation est <strong>temporaire</strong>. Votre récit, vos réponses, les informations du
        courrier et le courrier lui-même sont supprimés du serveur <strong>24 heures au plus</strong> après le
        début de la consultation. Passé ce délai, ils ne sont plus affichés, même si la suppression technique
        n&apos;a pas encore eu lieu, et ils ne peuvent pas être retrouvés. Vous pouvez aussi supprimer votre
        consultation vous-même, à tout moment, depuis la page de résultats.
      </p>
      <p>
        Les fichiers que vous enregistrez sur votre téléphone ou votre ordinateur restent chez vous : ils ne sont
        pas concernés par cette suppression.
      </p>

      <h2>Quand un professionnel doit intervenir</h2>
      <p>
        Si votre situation comporte un risque important (expulsion, procédure en justice, délai
        critique), un encadré vous le signale. Le service ne doit alors servir qu&apos;à préparer votre
        rendez-vous avec une personne qualifiée.
      </p>
    </article>
  );
}
