/**
 * Vidéo de présentation (30 s, verticale). Pas de lecture automatique : sur un
 * forfait mobile, télécharger 3 Mo sans le demander n'est pas acceptable. Seule
 * l'image d'aperçu est chargée tant que la personne n'appuie pas sur lecture.
 */
export function VideoPresentation() {
  return (
    <section className="section video-presentation" aria-labelledby="titre-video">
      <div className="section__interieur video-presentation__interieur">
        <div className="video-presentation__texte" data-apparition="">
          <p className="heros__marque">En 30 secondes</p>
          <h2 id="titre-video">Comment Mon Recours CI vous aide</h2>
          <p>
            Une lettre qui inquiète, des lois difficiles à lire, des démarches floues : le service
            retrouve les textes qui s&apos;appliquent, vous pose les bonnes questions et prépare votre
            courrier.
          </p>
        </div>
        <div className="video-presentation__cadre" data-apparition="" style={{ ["--delai" as string]: "120ms" }}>
          <video
            className="video-presentation__video"
            controls
            playsInline
            preload="none"
            poster="/video/presentation-apercu.jpg"
            width={360}
            height={640}
          >
            <source src="/video/presentation.mp4" type="video/mp4" />
            Votre navigateur ne peut pas lire cette vidéo.
          </video>
        </div>
      </div>
    </section>
  );
}
