import type { VueHorsCatalogue, VueRefus, VueReponse, VueUrgence } from "@/lib/types";
import { libelleDomaine, presentationStatut } from "@/lib/libelles";
import { BandeauUrgence, EncadreVerrous, OrientationHumaine } from "./Alertes";
import { FormulaireCourrier } from "./FormulaireCourrier";
import { CarteCitation, trouverSource } from "./CarteCitation";

function EnteteStatut({ statut, idTitre }: { statut: string; idTitre: string }) {
  const p = presentationStatut(statut);
  return (
    <header className={`statut statut--${p.ton}`} data-statut={statut}>
      <h2 id={idTitre} tabIndex={-1} className="statut__titre">
        {p.titre}
      </h2>
      <p className="statut__explication">{p.explication}</p>
    </header>
  );
}

function Avertissement({ texte }: { texte: string | null }) {
  if (!texte) return null;
  return <p className="avertissement-moteur">{texte}</p>;
}

// ---------------------------------------------------------------------------

export function VueResultat({ vue, urgence }: { vue: VueReponse; urgence: VueUrgence | null }) {
  const sourcesAssociees = new Set<number>();
  const regles = vue.droit.map((regle) => {
    const source = trouverSource(regle, vue.sources);
    if (source) sourcesAssociees.add(vue.sources.indexOf(source));
    return { regle, source };
  });
  const sourcesSeules = vue.sources.filter((_, i) => !sourcesAssociees.has(i));

  return (
    <section className="resultat" aria-labelledby="titre-resultat">
      <EnteteStatut statut={vue.statut} idTitre="titre-resultat" />

      {vue.dejaRepondu ? (
        <p className="info">Cette consultation avait déjà reçu sa réponse : elle est affichée à nouveau.</p>
      ) : null}

      <BandeauUrgence urgence={urgence} />
      <EncadreVerrous verrous={vue.verrous} />

      {vue.demande ? (
        <section className="bloc" aria-labelledby="titre-faits">
          <h2 id="titre-faits">Votre situation</h2>
          <p className="bloc__citation-utilisateur">{vue.demande}</p>
          {vue.noteFaits ? <p className="bloc__note">{vue.noteFaits}</p> : null}
        </section>
      ) : null}

      <section className="bloc" aria-labelledby="titre-droit">
        <h2 id="titre-droit">Ce que disent les textes</h2>
        {regles.length === 0 && sourcesSeules.length === 0 ? (
          <p className="vide">
            Aucun texte n&apos;est cité : le moteur n&apos;a retenu aucune source fiable pour cette
            consultation.
          </p>
        ) : (
          <div className="citations">
            {regles.map(({ regle, source }, i) => (
              <CarteCitation key={`${regle.numeroTexte}-${regle.article}-${i}`} regle={regle} source={source} />
            ))}
            {sourcesSeules.map((s, i) => (
              <CarteCitation
                key={`seule-${i}`}
                regle={{
                  titre: s.reference ?? "Texte",
                  article: s.article,
                  numeroTexte: s.numeroTexte,
                  citation: s.citation,
                  lecture: null,
                  noteLecture: s.noteLecture,
                }}
                source={s}
              />
            ))}
          </div>
        )}
      </section>

      {vue.application ? (
        <section className="bloc" aria-labelledby="titre-application">
          <h2 id="titre-application">Comment ces textes s&apos;appliquent</h2>
          <p>{vue.application}</p>
        </section>
      ) : null}

      {vue.applicationFaits && vue.applicationFaits.lignes.length > 0 ? (
        <section className="bloc" aria-labelledby="titre-application-faits">
          <h2 id="titre-application-faits">Au vu de vos réponses</h2>
          <ul className="lectures">
            {vue.applicationFaits.lignes.map((l, i) => (
              <li key={i} className={l.alerte ? "lecture lecture--alerte" : "lecture"}>
                <p className="lecture__question">
                  {l.question} <strong>{l.reponse === "oui" ? "Oui" : l.reponse === "non" ? "Non" : l.reponse}</strong>
                </p>
                <p className="lecture__texte">{l.lecture}</p>
                {l.articles.length > 0 ? (
                  <p className="lecture__ref">
                    {l.articles
                      .map((a) => `Article ${a.article}${a.numeroTexte ? ` (texte n° ${a.numeroTexte})` : ""}`)
                      .join(" · ")}
                  </p>
                ) : null}
              </li>
            ))}
          </ul>
          {vue.applicationFaits.note ? <p className="bloc__note">{vue.applicationFaits.note}</p> : null}
        </section>
      ) : null}

      {vue.demarches.length > 0 ? (
        <section className="bloc" aria-labelledby="titre-demarches">
          <h2 id="titre-demarches">Démarches envisageables</h2>
          <ol className="demarches">
            {vue.demarches.map((d, i) => (
              <li key={i}>{d}</li>
            ))}
          </ol>
        </section>
      ) : null}

      {vue.manquantes.length > 0 ? (
        <section className="bloc bloc--attention" aria-labelledby="titre-manquantes">
          <h2 id="titre-manquantes">Ce qui manque pour aller plus loin</h2>
          <ul>
            {vue.manquantes.map((m, i) => (
              <li key={i}>
                {m.question}
                {m.pourquoi ? <span className="manquante__pourquoi"> — {m.pourquoi}</span> : null}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {vue.aVerifier.length > 0 ? (
        <section className="bloc bloc--attention" aria-labelledby="titre-verifier">
          <h2 id="titre-verifier">Points à vérifier</h2>
          <ul>
            {vue.aVerifier.map((v, i) => (
              <li key={i}>{v}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {vue.brouillon ? (
        <section className="bloc" aria-labelledby="titre-brouillon">
          <h2 id="titre-brouillon">Brouillon de courrier</h2>
          {vue.brouillon.disponible && vue.brouillon.texte ? (
            <>
              <p>
                Un modèle de lettre de réclamation, préparé à partir de votre situation. Relisez-le, complétez
                les informations qui vous sont demandées, puis envoyez-le vous-même si vous le jugez utile.
              </p>
              <FormulaireCourrier brouillon={vue.brouillon} />
            </>
          ) : vue.brouillon.disponible ? (
            <p>
              Le moteur a préparé un brouillon ({vue.brouillon.note ?? "non envoyé"}), mais son contenu n&apos;a pas
              été transmis à l&apos;interface.
            </p>
          ) : (
            <p>Aucun brouillon disponible{vue.brouillon.raison ? ` : ${vue.brouillon.raison}` : "."}</p>
          )}
          <p className="bloc__note">Rien n&apos;est jamais envoyé à votre place.</p>
        </section>
      ) : null}

      <OrientationHumaine />
      <Avertissement texte={vue.avertissement} />
    </section>
  );
}

// ---------------------------------------------------------------------------

export function VueSansFiche({ vue }: { vue: VueHorsCatalogue }) {
  const articlesTrouves = vue.articlesSansFiche.filter((d) => d.articles.length > 0);
  return (
    <section className="resultat" aria-labelledby="titre-sans-fiche">
      <EnteteStatut statut={vue.statut} idTitre="titre-sans-fiche" />
      {/* L'urgence passe avant tout, même quand aucun texte ne répond. */}
      <BandeauUrgence urgence={vue.urgence} />
      <EncadreVerrous verrous={vue.verrous} />
      <p className="resultat__message">{vue.message}</p>

      {vue.domainesVision.length > 0 ? (
        <section className="bloc" aria-labelledby="titre-domaine-vision">
          <h2 id="titre-domaine-vision">Votre question relève probablement de</h2>
          <ul>
            {vue.domainesVision.map((d) => (
              <li key={d.code}>
                <strong>{d.libelle}</strong>
                {d.fichesDisponibles === 0
                  ? " — domaine pas encore couvert par le service : aucun texte vérifié ne permet d'y répondre."
                  : " — domaine partiellement couvert : votre situation ne correspond à aucune des fiches disponibles."}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      <OrientationHumaine />

      {vue.domaines.length > 0 ? (
        <section className="bloc" aria-labelledby="titre-domaines">
          <h2 id="titre-domaines">Domaine repéré</h2>
          <ul className="etiquettes">
            {vue.domaines.map((d) => (
              <li key={d}>{libelleDomaine(d)}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {vue.pistes.length > 0 ? (
        <section className="bloc" aria-labelledby="titre-pistes">
          <h2 id="titre-pistes">Sujets proches que le service sait traiter</h2>
          <ul>
            {vue.pistes.map((p) => (
              <li key={p}>{p}</li>
            ))}
          </ul>
        </section>
      ) : null}

      {vue.couverture.length > 0 ? (
        <section className="bloc" aria-labelledby="titre-couverture">
          <h2 id="titre-couverture">Ce que le service sait traiter aujourd&apos;hui</h2>
          <ListeCouverture couverture={vue.couverture} />
        </section>
      ) : null}

      {articlesTrouves.length > 0 ? (
        // Replié par défaut et sans badge « Référence vérifiée » : ces articles
        // ne répondent PAS à la question. Affichés en clair, ils passaient pour
        // une réponse (constaté avec un test réel : un litige de terrain
        // affichait l'article sur la caution d'un loyer).
        <details className="bloc bloc--discret textes-domaine">
          <summary>
            Voir les textes de ce domaine présents dans le service (aucun lien établi avec votre question)
          </summary>
          <p className="bloc__note">
            Ces articles existent dans les textes du service, mais aucune fiche ne permet de dire s&apos;ils
            s&apos;appliquent à votre situation. Ce n&apos;est pas une réponse : ne vous appuyez pas dessus sans
            l&apos;avis d&apos;une personne qualifiée.
          </p>
          {articlesTrouves.map((d) => (
            <div key={d.domaine}>
              <h3>{libelleDomaine(d.domaine)}</h3>
              <ul className="textes-domaine__liste">
                {d.articles.map((a, i) => (
                  <li key={i}>
                    Article {a.article}
                    {a.numeroTexte ? `, texte n° ${a.numeroTexte}` : ""}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </details>
      ) : null}

      <Avertissement texte={vue.avertissement} />
    </section>
  );
}

export function ListeCouverture({ couverture }: { couverture: { domaine: string; fiches: string[] }[] }) {
  return (
    <div className="couverture">
      {couverture.map((c) => (
        <div key={c.domaine} className="couverture__domaine">
          <h3>{libelleDomaine(c.domaine)}</h3>
          <ul>
            {c.fiches.map((f) => (
              <li key={f}>{f}</li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------

export function VueRefusee({ vue }: { vue: VueRefus }) {
  return (
    <section className="resultat" aria-labelledby="titre-refus">
      <EnteteStatut statut={vue.statut} idTitre="titre-refus" />
      {vue.raisons.length > 0 ? (
        <ul className="raisons-refus">
          {vue.raisons.map((r, i) => (
            <li key={i}>
              <p className="raisons-refus__libelle">{r.libelle}</p>
              {r.suite ? <p>{r.suite}</p> : null}
            </li>
          ))}
        </ul>
      ) : (
        <p>Le moteur n&apos;a pas précisé la raison du refus.</p>
      )}
      <Avertissement texte={vue.avertissement} />
    </section>
  );
}
