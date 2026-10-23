import type { VueSante } from "@/lib/types";
import { libelleDomaine } from "@/lib/libelles";
import { IconeDomaine } from "./Icones";
import { Apparitions } from "./anime/Apparitions";
import { Compteur } from "./anime/Compteur";
import { IllustrationHeros } from "./anime/IllustrationHeros";
import { Faq } from "./Faq";
import { PartageWhatsApp } from "./PartageWhatsApp";
import { VideoPresentation } from "./VideoPresentation";

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
  for (const [domaine, liste] of fiches) {
    if (!cartes.some((c) => c.domaine === domaine)) cartes.push({ domaine, statut: "", fiches: liste });
  }
  return cartes.sort((a, b) => b.fiches.length - a.fiches.length);
}

const ETAPES = [
  {
    titre: "Vous décrivez votre problème",
    texte: "En quelques phrases, avec vos mots. Sans nom, sans numéro de téléphone, sans compte à créer.",
  },
  {
    titre: "Le service vous pose des questions",
    texte: "Seulement celles qui déterminent si un texte de loi s'applique à votre situation.",
  },
  {
    titre: "Vous lisez l'analyse et ses sources",
    texte: "Chaque article est cité mot pour mot, avec le texte officiel dont il provient et son niveau de vérification.",
  },
  {
    titre: "Vous téléchargez votre courrier",
    texte: "Lorsque le moteur peut en produire un : un document prêt à envoyer, avec les références qui le fondent.",
  },
];

/**
 * Page d'accueil du citoyen.
 *
 * La couverture vient de GET /sante, en direct : si le moteur ne répond pas, la
 * page le dit au lieu d'afficher une promesse creuse.
 *
 * Le parcours citoyen et l'administration sont séparés : le seul lien vers
 * l'administration est discret, en pied de page, et mène à /connexion.
 */
export function Accueil({
  sante,
  demo = false,
  nonConfigure = false,
}: {
  sante: VueSante | null;
  demo?: boolean;
  nonConfigure?: boolean;
}) {
  const cartes = sante ? cartesDomaines(sante) : [];
  const couverts = cartes.filter((c) => c.fiches.length > 0);
  const enAttente = cartes.filter((c) => c.fiches.length === 0);
  const totalSituations = couverts.reduce((n, c) => n + c.fiches.length, 0);
  const articles = sante?.corpus?.articles ?? null;
  const textes = sante?.corpus?.documents ?? null;

  return (
    <div className="accueil-citoyen">
      <Apparitions />
      <section className="heros" aria-labelledby="titre-accueil">
        <div className="heros__interieur heros__interieur--grille">
          <div className="heros__texte">
          <p className="heros__marque">Information juridique · Côte d&apos;Ivoire</p>
          <h1 id="titre-accueil" className="heros__titre">
            Comprenez vos droits, avec le texte de loi sous les yeux.
          </h1>
          <p className="heros__chapo">
            Décrivez votre problème avec vos mots. Mon Recours CI retrouve les articles de loi qui
            s&apos;y rapportent, les cite mot pour mot avec leur source officielle, et vous dit
            clairement quand il ne peut pas répondre.
          </p>
          <div className="heros__actions">
            <a href="/consultation" className="bouton bouton--grand heros__cta">
              Commencer ma consultation
            </a>
            <a href="#etapes" className="heros__lien">
              Voir comment ça marche
            </a>
          </div>
          <p className="heros__garanties">
            {sante && sante.langageActif === false
              ? "Sans compte ni inscription · Aucune donnée transmise à un tiers · Vous pouvez effacer votre consultation à tout moment"
              : "Sans compte ni inscription · Vous pouvez effacer votre consultation à tout moment"}
          </p>
          </div>
          <IllustrationHeros />
        </div>
        {sante && totalSituations > 0 ? (
          <dl className="chiffres">
            <div className="chiffres__item">
              <dt>situations traitées</dt>
              <dd>
                <Compteur valeur={totalSituations} />
              </dd>
            </div>
            <div className="chiffres__item">
              <dt>domaines du droit</dt>
              <dd>
                <Compteur valeur={couverts.length} duree={900} />
              </dd>
            </div>
            {articles ? (
              <div className="chiffres__item">
                <dt>articles de loi</dt>
                <dd>
                  <Compteur valeur={articles} duree={1800} />
                </dd>
              </div>
            ) : null}
            {textes ? (
              <div className="chiffres__item">
                <dt>textes officiels</dt>
                <dd>
                  <Compteur valeur={textes} duree={1200} />
                </dd>
              </div>
            ) : null}
          </dl>
        ) : null}
      </section>

      {nonConfigure ? (
        <div className="alerte-instance" role="alert">
          <strong>Cette instance n&apos;est pas configurée.</strong> Aucun moteur juridique
          n&apos;est connecté : rien ne peut être répondu. Ce n&apos;est pas le service en
          production.
        </div>
      ) : null}

      <section className="etapes-citoyen" id="etapes" aria-labelledby="titre-etapes">
        <div className="section__interieur">
          <div className="section__entete" data-apparition="">
            <h2 id="titre-etapes">Comment ça marche</h2>
            <p>Quatre étapes, aucune inscription, environ cinq minutes.</p>
          </div>
          <ol className="etapes-citoyen__liste">
            {ETAPES.map((e, i) => (
              <li
                key={e.titre}
                className="etape-carte"
                data-apparition=""
                style={{ ["--delai" as string]: `${i * 120}ms` }}
              >
                <span className="etape-carte__numero" aria-hidden="true">
                  {i + 1}
                </span>
                <h3 className="etape-carte__titre">{e.titre}</h3>
                <p className="etape-carte__texte">{e.texte}</p>
              </li>
            ))}
          </ol>
          <p className="etapes-citoyen__action">
            <a href="/consultation" className="bouton bouton--grand">
              Commencer ma consultation
            </a>
          </p>
        </div>
      </section>

      <VideoPresentation />

      <section className="section section--blanche" aria-labelledby="titre-domaines">
        <div className="section__interieur">
          <div className="section__entete">
            <h2 id="titre-domaines">Ce que le service sait traiter aujourd&apos;hui</h2>
            {sante ? (
              <p>
                <strong>
                  <Compteur valeur={totalSituations} /> situations, dans{" "}
                  <Compteur valeur={couverts.length} duree={900} /> domaines
                </strong>{" "}
                — chacune rattachée à un article de loi précis. Pour tout autre sujet, le service
                vous dira qu&apos;il ne peut pas conclure.
              </p>
            ) : (
              <p className="info" role="status">
                Le moteur juridique ne répond pas pour le moment : la liste des sujets couverts ne
                peut pas être affichée. Réessayez dans quelques minutes.
              </p>
            )}
            {sante && demo ? (
              <p className="info">
                <strong>Démonstration :</strong> les sujets ci-dessous sont ceux du produit
                complet. Ici, aucune réponse n&apos;est calculée.
              </p>
            ) : null}
          </div>

          {sante ? (
            <ul className="domaines-citoyen">
              {couverts.map((c, i) => (
                <li
                  key={c.domaine}
                  className="domaine-citoyen"
                  data-apparition=""
                  style={{ ["--delai" as string]: `${i * 90}ms` }}
                >
                  <div className="domaine-citoyen__entete">
                    <span className="domaine-citoyen__icone">
                      <IconeDomaine domaine={c.domaine} />
                    </span>
                    <div>
                      <h3 className="domaine-citoyen__nom">{libelleDomaine(c.domaine)}</h3>
                      <p className="domaine-citoyen__compte">
                        {c.fiches.length} situation{c.fiches.length > 1 ? "s" : ""}
                      </p>
                    </div>
                  </div>
                  {c.fiches.length > 3 ? (
                    <details className="domaine-citoyen__details">
                      <summary>Voir les sujets</summary>
                      <ul>
                        {c.fiches.map((f) => (
                          <li key={f}>{f}</li>
                        ))}
                      </ul>
                    </details>
                  ) : (
                    <ul className="domaine-citoyen__liste">
                      {c.fiches.map((f) => (
                        <li key={f}>{f}</li>
                      ))}
                    </ul>
                  )}
                </li>
              ))}
            </ul>
          ) : null}

          {sante && enAttente.length > 0 ? (
            <div className="domaines-attente">
              {enAttente.some((c) => c.statut === "CORPUS_PARTIEL" || c.statut === "TERMINE_TECHNIQUEMENT") ? (
                <p>
                  <strong>Textes collectés, pas encore de fiche de référence :</strong>{" "}
                  {enAttente
                    .filter((c) => c.statut === "CORPUS_PARTIEL" || c.statut === "TERMINE_TECHNIQUEMENT")
                    .map((c) => libelleDomaine(c.domaine))
                    .join(", ")}
                  . Le service ne peut pas encore conclure sur ces sujets.
                </p>
              ) : null}
              {enAttente.some((c) => c.statut !== "CORPUS_PARTIEL" && c.statut !== "TERMINE_TECHNIQUEMENT") ? (
                <p>
                  <strong>Aucun texte disponible à ce jour :</strong>{" "}
                  {enAttente
                    .filter((c) => c.statut !== "CORPUS_PARTIEL" && c.statut !== "TERMINE_TECHNIQUEMENT")
                    .map((c) => libelleDomaine(c.domaine))
                    .join(", ")}
                  . Sur ces sujets, le service vous orientera au lieu de répondre.
                </p>
              ) : null}
            </div>
          ) : null}
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
          <p className="etapes-citoyen__action">
            <a href="/comprendre" className="lien-clair">
              Comprendre comment lire un résultat
            </a>
          </p>
        </div>
      </section>

      <Faq />

      <section className="appel" aria-labelledby="titre-appel">
        <div className="section__interieur appel__interieur">
          <h2 id="titre-appel">Un souci de logement, de famille ou de dette ?</h2>
          <div className="appel__actions">
            <a href="/consultation" className="bouton bouton--grand bouton--sombre">
              Commencer ma consultation
            </a>
            <PartageWhatsApp variante="sombre" />
          </div>
        </div>
      </section>
    </div>
  );
}
