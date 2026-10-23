/**
 * Questions fréquentes. Chaque réponse décrit le fonctionnement RÉEL du service
 * (rien n'est promis qu'il ne fasse pas). Repliées par défaut : <details>
 * fonctionne sans JavaScript et au clavier.
 */
const QUESTIONS: { q: string; r: string }[] = [
  {
    q: "Mon Recours CI remplace-t-il un avocat ?",
    r: "Non. C'est un service d'information : il vous montre les textes de loi qui se rapportent à votre situation et les démarches possibles. Il ne vous représente pas et ne garantit aucune décision. Pour une affaire importante, faites relire votre situation par un professionnel du droit.",
  },
  {
    q: "Dois-je créer un compte ou donner mon nom ?",
    r: "Non. Aucune inscription n'est demandée. Inutile d'indiquer votre nom, votre numéro de téléphone ou votre adresse : ils ne servent pas à l'analyse.",
  },
  {
    q: "D'où viennent les articles de loi cités ?",
    r: "De textes officiels ivoiriens et de l'OHADA, téléchargés en octobre 2026. Chaque article est cité mot pour mot, avec le document dont il provient et son niveau de vérification. Aucun article n'a encore été relu par un juriste.",
  },
  {
    q: "Que se passe-t-il si mon problème n'est pas couvert ?",
    r: "Le service vous le dit clairement et vous oriente, au lieu d'inventer une réponse. Aujourd'hui, il couvre surtout le logement, la famille, les dettes et contrats, et certaines questions pénales.",
  },
  {
    q: "Le service envoie-t-il le courrier à ma place ?",
    r: "Non, jamais. Il prépare un brouillon que vous relisez, complétez et envoyez vous-même si vous le décidez.",
  },
  {
    q: "Puis-je effacer ma consultation ?",
    r: "Oui. À la fin de la consultation, « Supprimer cette consultation du serveur » efface votre récit et vos réponses. Vous pouvez aussi enregistrer la synthèse sur votre téléphone avant de l'effacer.",
  },
  {
    q: "Les textes sont-ils à jour ?",
    r: "Ils correspondent aux documents officiels téléchargés en octobre 2026. Une loi modifiée après cette date peut ne pas être prise en compte : le service l'indique quand il le sait.",
  },
];

export function Faq() {
  return (
    <section className="section faq" aria-labelledby="titre-faq">
      <div className="section__interieur">
        <div className="section__entete" data-apparition="">
          <h2 id="titre-faq">Questions fréquentes</h2>
        </div>
        <div className="faq__liste">
          {QUESTIONS.map((item, i) => (
            <details key={item.q} className="faq__item" data-apparition="" style={{ ["--delai" as string]: `${i * 60}ms` }}>
              <summary>{item.q}</summary>
              <p>{item.r}</p>
            </details>
          ))}
        </div>
      </div>
    </section>
  );
}
