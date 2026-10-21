import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Mot de passe oublié",
};

/**
 * Pas de lien de réinitialisation par e-mail : aucun service d'envoi n'est
 * configuré, et un formulaire qui changerait un mot de passe sans prouver
 * l'identité de la personne serait une porte dérobée. La procédure passe donc
 * par une personne qui administre déjà le serveur.
 */
export default function PageMotDePasseOublie() {
  return (
    <section className="connexion">
      <div className="connexion__carte">
        <p className="connexion__surtitre">Espace réservé</p>
        <h1 className="titre-etape">Mot de passe oublié</h1>
        <p>
          Pour des raisons de sécurité, le mot de passe ne peut pas être réinitialisé depuis cette page :
          aucun lien n&apos;est envoyé par e-mail, et aucun code ne contourne la vérification de votre
          identité.
        </p>
        <h2 className="connexion__sous-titre">Que faire ?</h2>
        <ol className="connexion__etapes">
          <li>Contactez la personne qui administre le serveur de Mon Recours CI.</li>
          <li>Après avoir vérifié votre identité, elle génère pour vous une nouvelle empreinte de mot de passe.</li>
          <li>
            Dès que la nouvelle empreinte est en place, l&apos;ancien mot de passe ne fonctionne plus et
            toutes les sessions ouvertes avec lui sont fermées.
          </li>
        </ol>
        <p className="actions">
          <a href="/connexion" className="bouton bouton--secondaire">
            Retour à la connexion
          </a>
        </p>
      </div>
    </section>
  );
}
