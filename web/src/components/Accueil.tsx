import type { VueSante } from "@/lib/types";
import { libelleDomaine, libelleStatutDomaine } from "@/lib/libelles";
import { IconeDomaine } from "./Icones";

interface CarteDomaine {
  domaine: string;
  fiches: string[];
  statut: string;
}

/** Réunit la couverture du catalogue et l'état des domaines, tels que /sante les renvoie. */
function cartesDomaines(sante: VueSante): CarteDomaine[] {
  const fiches = new Map(sante.catalogue.parDomaine.map((d) => [d.domaine, d.fiches]));
  const cartes: CarteDomaine[] = sante.domaines.map((d) => ({
    domaine: d.domaine,
    statut: d.statut,
    fiches: fiches.get(d.domaine) ?? [],
  }));
  // Domaines du catalogue absents de l'inventaire : affichés quand même.
  for (const [domaine, liste] of fiches) {
    if (!cartes.some((c) => c.domaine === domaine)) cartes.push({ domaine, statut: "", fiches: liste });
  }
  return cartes.sort((a, b) => b.fiches.length - a.fiches.length);
}

/**
 * Page d'accueil. La couverture et le bandeau défilant viennent de GET /sante,
 * en direct : si le moteur ne répond pas, la page le dit.
 */
export function Accueil({ sante }: { sante: VueSante | null }) {
  const cartes = sante ? cartesDomaines(sante) : [];
  const situations = sante ? sante.catalogue.parDomaine.flatMap((d) => d.fiches) : [];

  return (
    <div className="accueil">
      <section className="une" aria-labelledby="titre-accueil">
        <div className="une__interieur">
          <span className="une__paragraphe" aria-hidden="true">
            §
          </span>
          <h1 id="titre-accueil" className="une__titre">
            Vos droits en Côte d&apos;Ivoire, avec le texte de loi sous les yeux.
          </h1>
          <p className="une__chapo">
            Décrivez votre problème avec vos mots. Mon Recours CI cherche les articles de loi qui
            s&apos;y rapportent, vous les cite mot pour mot avec leur source officielle, et vous dit
            clairement quand il ne sait pas.
          </p>
          <div className="une__actions">
            <a href="/consultation" className="bouton bouton--grand">
              Décrire mon problème
            </a>
            <a href="/comprendre" className="lien-clair">
              Comment lire un résultat
            </a>
          </div>
          <p className="une__garanties">Sans compte ni inscription. Aucune donnée transmise à un service tiers.</p>
        </div>
      </section>

      {situations.length > 0 ? (
        <div className="bandeau" aria-hidden="true">
          <div className="bandeau__piste">
            {[...situations, ...situations].map((s, i) => (
              <span key={i} className="bandeau__item">
                {s}
              </span>
            ))}
          </div>
        </div>
      ) : null}

      <section className="section" aria-labelledby="titre-couverture-accueil">
        <div className="section__interieur">
          <div className="section__entete">
            <h2 id="titre-couverture-accueil">Ce que le service sait traiter aujourd&apos;hui</h2>
            {sante ? (
              <p>
                {sante.catalogue.fiches} situations sont couvertes, chacune rattachée à un article de loi
                précis. Pour tout autre sujet, le service vous dira qu&apos;il ne peut pas conclure.
              </p>
            ) : null}
          </div>
          {sante ? (
            <ul className="domaines">
              {cartes.map((c) => {
                const couvert = c.fiches.length > 0;
                return (
                  <li key={c.domaine} className={`domaine ${couvert ? "domaine--couvert" : "domaine--attente"}`}>
                    <span className="domaine__icone">
                      <IconeDomaine domaine={c.domaine} />
                    </span>
                    <h3 className="domaine__nom">{libelleDomaine(c.domaine)}</h3>
                    <p className="domaine__statut">
                      {couvert
                        ? `${c.fiches.length} situation${c.fiches.length > 1 ? "s" : ""}`
                        : libelleStatutDomaine(c.statut)}
                    </p>
                    {couvert ? (
                      <ul className="domaine__fiches">
                        {c.fiches.map((f) => (
                          <li key={f}>{f}</li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="info" role="status">
              Le moteur juridique ne répond pas pour le moment : la liste des sujets couverts ne peut pas
              être affichée. Réessayez dans quelques minutes.
            </p>
          )}
        </div>
      </section>

      <section className="section section--blanche" aria-labelledby="titre-fonctionnement">
        <div className="section__interieur">
          <div className="section__entete">
            <h2 id="titre-fonctionnement">Comment ça marche</h2>
          </div>
          <ol className="fonctionnement">
            <li>
              <h3>Vous décrivez votre situation</h3>
              <p>En quelques phrases, sans nom ni numéro de téléphone.</p>
            </li>
            <li>
              <h3>Le service vous pose des questions</h3>
              <p>Seulement celles qui permettent de savoir si un texte s&apos;applique à vous.</p>
            </li>
            <li>
              <h3>Vous recevez les textes et des pistes</h3>
              <p>Chaque article est cité mot pour mot, avec son document officiel et son niveau de vérification.</p>
            </li>
          </ol>
        </div>
      </section>

      <section className="section section--sombre" aria-labelledby="titre-limites">
        <div className="section__interieur">
          <div className="section__entete">
            <h2 id="titre-limites">Ce que ce service n&apos;est pas</h2>
          </div>
          <ul className="limites">
            <li>Ce n&apos;est pas un avocat : il ne vous représente pas et ne garantit aucun résultat.</li>
            <li>Il ne connaît que les textes de son corpus, qui est incomplet.</li>
            <li>Aucun article n&apos;a encore été relu par un juriste.</li>
            <li>Il n&apos;envoie jamais de courrier ni de démarche à votre place.</li>
          </ul>
          {sante?.avertissement ? <p className="limites__note">{sante.avertissement}</p> : null}
        </div>
      </section>

      <section className="appel" aria-labelledby="titre-appel">
        <div className="section__interieur appel__interieur">
          <h2 id="titre-appel">Un souci de logement, de bail ou de caution ?</h2>
          <a href="/consultation" className="bouton bouton--grand bouton--sombre">
            Décrire mon problème
          </a>
        </div>
      </section>
    </div>
  );
}
