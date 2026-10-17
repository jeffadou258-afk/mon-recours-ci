export function EnTete() {
  return (
    <header className="entete">
      <div className="entete__interieur">
        <a href="/" className="marque" aria-label="Mon Recours CI, accueil">
          <span className="marque__sceau" aria-hidden="true">§</span>
          <span className="marque__nom">Mon Recours CI</span>
        </a>
        <a href="/consultation" className="entete__action">
          Décrire mon problème
        </a>
      </div>
    </header>
  );
}

export function PiedDePage() {
  return (
    <footer className="pied">
      <div className="pied__interieur">
        <p className="pied__marque">
          <span className="marque__sceau" aria-hidden="true">§</span> Mon Recours CI
        </p>
        <div className="pied__texte">
          <p>
            Service d&apos;information juridique sur le droit ivoirien. Il ne remplace pas un avocat et
            ne garantit aucune décision de justice.
          </p>
          <p>
            Textes issus de documents officiels téléchargés en octobre 2026. Leur version en vigueur
            n&apos;est pas garantie au-delà de cette date.
          </p>
        </div>
        <nav aria-label="Pied de page" className="pied__nav">
          <a href="/consultation">Décrire mon problème</a>
          <a href="/comprendre">Comprendre les résultats</a>
        </nav>
      </div>
    </footer>
  );
}
