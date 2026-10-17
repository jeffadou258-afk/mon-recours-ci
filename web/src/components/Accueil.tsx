import type { VueSante } from "@/lib/types";
import { libelleDomaine, libelleStatutDomaine } from "@/lib/libelles";
import { ListeCouverture } from "./Resultats";

/**
 * Page d'accueil. La couverture affichée vient de GET /sante, en direct : si le
 * moteur ne répond pas, la page le dit au lieu d'afficher une liste figée.
 */
export function Accueil({ sante }: { sante: VueSante | null }) {
  const sansTextes = sante?.domaines.filter((d) => d.statut === "BLOQUE_SOURCE") ?? [];
  const partiels = sante?.domaines.filter((d) => d.statut === "CORPUS_PARTIEL") ?? [];

  return (
    <>
      <section className="accueil-une" aria-labelledby="titre-accueil">
        <h1 id="titre-accueil" className="accueil-une__titre">
          Vos droits en Côte d&apos;Ivoire, avec le texte de loi sous les yeux.
        </h1>
        <p className="accueil-une__chapo">
          Décrivez votre problème avec vos mots. Mon Recours CI cherche les articles de loi qui s&apos;y
          rapportent, vous les cite mot pour mot avec leur source officielle, et vous dit clairement
          quand il ne sait pas.
        </p>
        <div className="actions">
          <a href="/consultation" className="bouton bouton--grand">
            Décrire mon problème
          </a>
        </div>
        <p className="accueil-une__garanties">
          Sans compte ni inscription. Aucune donnée n&apos;est transmise à un service tiers.
        </p>
      </section>

      <section className="section" aria-labelledby="titre-couverture-accueil">
        <h2 id="titre-couverture-accueil">Ce que le service sait traiter aujourd&apos;hui</h2>
        {sante ? (
          <>
            <p>
              {sante.catalogue.fiches} situations sont couvertes, chacune rattachée à un article de loi
              précis. Pour tout autre sujet, le service vous dira qu&apos;il ne peut pas conclure.
            </p>
            <ListeCouverture couverture={sante.catalogue.parDomaine} />
            {partiels.length + sansTextes.length > 0 ? (
              <div className="limites-domaines">
                <h3>Domaines pas encore couverts</h3>
                <ul>
                  {[...partiels, ...sansTextes].map((d) => (
                    <li key={d.domaine}>
                      <span>{libelleDomaine(d.domaine)}</span>
                      <span className="limites-domaines__statut">{libelleStatutDomaine(d.statut)}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null}
          </>
        ) : (
          <p className="info" role="status">
            Le moteur juridique ne répond pas pour le moment : la liste des sujets couverts ne peut pas
            être affichée. Réessayez dans quelques minutes.
          </p>
        )}
      </section>

      <section className="section" aria-labelledby="titre-fonctionnement">
        <h2 id="titre-fonctionnement">Comment ça marche</h2>
        <ol className="fonctionnement">
          <li>
            <h3>Vous décrivez votre situation</h3>
            <p>En quelques phrases, sans données personnelles.</p>
          </li>
          <li>
            <h3>Le service vous pose des questions</h3>
            <p>Seulement celles qui permettent de savoir si un texte s&apos;applique à vous.</p>
          </li>
          <li>
            <h3>Vous recevez les textes et des pistes</h3>
            <p>
              Chaque article est cité mot pour mot, avec son document officiel et son niveau de
              vérification.
            </p>
          </li>
        </ol>
      </section>

      <section className="section section--limites" aria-labelledby="titre-limites">
        <h2 id="titre-limites">Ce que ce service n&apos;est pas</h2>
        <ul>
          <li>Ce n&apos;est pas un avocat : il ne vous représente pas et ne garantit aucun résultat.</li>
          <li>Il ne connaît que les textes de son corpus, qui est incomplet.</li>
          <li>Aucun article n&apos;a encore été relu par un juriste.</li>
          <li>Il n&apos;envoie jamais de courrier ni de démarche à votre place.</li>
        </ul>
        {sante?.avertissement ? <p className="bloc__note">{sante.avertissement}</p> : null}
      </section>
    </>
  );
}
