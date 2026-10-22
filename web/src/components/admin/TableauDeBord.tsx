/**
 * Tableau de bord d'administration — composant de présentation pur.
 *
 * Il n'affiche QUE ce que le serveur lui transmet. Toute donnée absente est
 * dite absente (« Non disponible », « Non connecté ») : aucun chiffre n'est
 * inventé, aucune valeur secrète n'est reçue ni affichée.
 */

import type { VueSante } from "@/lib/types";

export interface LigneJournal {
  horodatage: string;
  evenement: string;
  compte?: string;
  empreinteSaisie?: string;
  detail?: string;
}

export interface DonneesTableauDeBord {
  compte: { email: string; role: string };
  plateforme: {
    mode: "demonstration" | "reel";
    moteur: "joignable" | "injoignable" | "non_configure";
    langageActif: boolean | null;
    versionInterface: string;
  };
  sante: VueSante | null;
  comptes: { email: string; role: string }[];
  comptesIgnores: number;
  audit: LigneJournal[] | null;
  parametres: { libelle: string; valeur: string; note?: string }[];
}

const NON_DISPONIBLE = "Non disponible";

const LIBELLES_EVENEMENTS: Record<string, string> = {
  connexion_reussie: "Connexion réussie",
  connexion_refusee: "Connexion refusée",
  connexion_limitee: "Tentatives limitées",
  deconnexion: "Déconnexion",
  acces_administration: "Consultation de l'administration",
  acces_administration_refuse: "Accès à l'administration refusé",
  authentification_fermee: "Connexion fermée (configuration)",
};

function Etiquette({ ton, children }: { ton: "ok" | "alerte" | "neutre"; children: React.ReactNode }) {
  return <span className={`admin-etiquette admin-etiquette--${ton}`}>{children}</span>;
}

function Indicateur({ libelle, valeur, ton = "neutre" }: { libelle: string; valeur: string; ton?: "ok" | "alerte" | "neutre" }) {
  return (
    <div className="admin-indicateur">
      <dt>{libelle}</dt>
      <dd>
        <Etiquette ton={ton}>{valeur}</Etiquette>
      </dd>
    </div>
  );
}

function nombre(n: number | null | undefined): string {
  return typeof n === "number" ? new Intl.NumberFormat("fr-FR").format(n) : NON_DISPONIBLE;
}

function date(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime())
    ? iso
    : new Intl.DateTimeFormat("fr-FR", { dateStyle: "short", timeStyle: "medium", timeZone: "UTC" }).format(d) + " UTC";
}

export function TableauDeBord({ donnees }: { donnees: DonneesTableauDeBord }) {
  const { plateforme, sante } = donnees;
  const corpusConnecte = sante !== null && sante.corpus.integrite !== "NON_CONNECTE";
  const incident = sante?.incidentLangage ?? null;

  return (
    <div className="admin">
      {incident ? (
        <section
          className="bloc bloc--attention"
          role="alert"
          aria-labelledby="titre-incident-langage"
          data-incident="credits-epuises"
        >
          <h2 id="titre-incident-langage" className="bloc__titre">
            {incident.objet ?? "Crédits du fournisseur épuisés — Mon Recours CI"}
          </h2>
          <p>
            <strong>DeepSeek indisponible — crédits épuisés.</strong> Le moteur de secours
            fonctionne. Vérifiez le solde du fournisseur.
          </p>
          <ul>
            {incident.detecteLe ? <li>Détecté le {incident.detecteLe}</li> : null}
            {incident.fournisseur ? <li>Fournisseur : {incident.fournisseur}</li> : null}
            {incident.consequence ? <li>{incident.consequence}</li> : null}
            {incident.actionAttendue ? <li>{incident.actionAttendue}</li> : null}
          </ul>
        </section>
      ) : null}

      <header className="admin__entete">
        <div>
          <p className="connexion__surtitre">Administration</p>
          <h1 className="titre-etape">Tableau de bord</h1>
          <p className="formulaire__aide">
            Connecté en tant que <strong>{donnees.compte.email}</strong> ({donnees.compte.role}).
          </p>
        </div>
        <form method="post" action="/api/deconnexion">
          <button type="submit" className="bouton bouton--secondaire">
            Se déconnecter
          </button>
        </form>
      </header>

      <nav className="admin__sommaire" aria-label="Sections du tableau de bord">
        <a href="#vue-ensemble">Vue d&apos;ensemble</a>
        <a href="#corpus">Corpus</a>
        <a href="#erreurs">Erreurs</a>
        <a href="#utilisateurs">Utilisateurs</a>
        <a href="#audit">Journal d&apos;audit</a>
        <a href="#parametres">Paramètres</a>
      </nav>

      <section id="vue-ensemble" className="admin-carte" aria-labelledby="titre-vue">
        <h2 id="titre-vue">Vue d&apos;ensemble</h2>
        <dl className="admin-grille">
          <Indicateur
            libelle="Mode"
            valeur={plateforme.mode === "demonstration" ? "Démonstration" : "Service réel"}
            ton={plateforme.mode === "demonstration" ? "alerte" : "ok"}
          />
          <Indicateur
            libelle="Moteur juridique"
            valeur={
              plateforme.moteur === "joignable"
                ? "Joignable"
                : plateforme.moteur === "injoignable"
                  ? "Injoignable"
                  : "Non configuré"
            }
            ton={plateforme.moteur === "joignable" ? "ok" : "alerte"}
          />
          <Indicateur
            libelle="Modèle de langage"
            valeur={plateforme.langageActif === null ? NON_DISPONIBLE : plateforme.langageActif ? "Activé" : "Désactivé"}
            ton={plateforme.langageActif ? "alerte" : "neutre"}
          />
          <Indicateur libelle="Version de l'interface" valeur={plateforme.versionInterface} />
        </dl>
        <p className="formulaire__aide">
          Fréquentation et nombre de consultations : {NON_DISPONIBLE}. L&apos;interface ne conserve aucune
          consultation ni statistique de visite.
        </p>
      </section>

      <section id="corpus" className="admin-carte" aria-labelledby="titre-corpus">
        <h2 id="titre-corpus">État du corpus juridique</h2>
        {sante === null ? (
          <p>
            <Etiquette ton="alerte">Non connecté</Etiquette> Le moteur juridique ne répond pas ou n&apos;est pas
            configuré : l&apos;état du corpus ne peut pas être lu.
          </p>
        ) : (
          <>
            <dl className="admin-grille">
              <Indicateur
                libelle="Intégrité"
                valeur={sante.corpus.integrite ?? NON_DISPONIBLE}
                ton={corpusConnecte && sante.corpus.integrite === "INTEGRE" ? "ok" : "alerte"}
              />
              <Indicateur libelle="Documents" valeur={nombre(sante.corpus.documents)} />
              <Indicateur libelle="Articles" valeur={nombre(sante.corpus.articles)} />
              <Indicateur libelle="Fiches au catalogue" valeur={nombre(sante.catalogue.fiches)} />
            </dl>
            {sante.domaines.length ? (
              <div className="admin-tableau-conteneur">
                <table className="admin-tableau">
                  <caption className="visuellement-cache">Statut du corpus par domaine</caption>
                  <thead>
                    <tr>
                      <th scope="col">Domaine</th>
                      <th scope="col">Statut</th>
                      <th scope="col">Complétude</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sante.domaines.map((d) => (
                      <tr key={d.domaine}>
                        <th scope="row">{d.domaine}</th>
                        <td>{d.statut}</td>
                        <td>{d.completude}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
            {sante.avertissement ? <p className="formulaire__aide">{sante.avertissement}</p> : null}
          </>
        )}
      </section>

      <section id="erreurs" className="admin-carte" aria-labelledby="titre-erreurs">
        <h2 id="titre-erreurs">Suivi des erreurs techniques</h2>
        <p>
          <Etiquette ton="neutre">Non connecté</Etiquette> Les erreurs sont écrites dans le journal du serveur
          (sortie standard), sans contenu de consultation. Aucun service de suivi consultable depuis cette page
          n&apos;est configuré.
        </p>
      </section>

      <section id="utilisateurs" className="admin-carte" aria-labelledby="titre-utilisateurs">
        <h2 id="titre-utilisateurs">Utilisateurs et rôles</h2>
        <p className="formulaire__aide">
          Les comptes sont définis dans la configuration du serveur. Leur création, leur modification et
          l&apos;attribution des rôles depuis cette page : {NON_DISPONIBLE}.
        </p>
        <div className="admin-tableau-conteneur">
          <table className="admin-tableau">
            <caption className="visuellement-cache">Comptes configurés</caption>
            <thead>
              <tr>
                <th scope="col">Adresse e-mail</th>
                <th scope="col">Rôle</th>
              </tr>
            </thead>
            <tbody>
              {donnees.comptes.map((c) => (
                <tr key={c.email}>
                  <th scope="row">{c.email}</th>
                  <td>{c.role}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {donnees.comptesIgnores > 0 ? (
          <p className="admin-alerte" role="status">
            {donnees.comptesIgnores} entrée(s) de la configuration ont été ignorées (format, rôle ou empreinte
            invalide, ou doublon).
          </p>
        ) : null}
      </section>

      <section id="audit" className="admin-carte" aria-labelledby="titre-audit">
        <h2 id="titre-audit">Journal d&apos;audit</h2>
        {donnees.audit === null ? (
          <p>
            <Etiquette ton="neutre">Non connecté</Etiquette> Aucun fichier d&apos;audit n&apos;est configuré : les
            événements sont seulement écrits dans le journal du serveur.
          </p>
        ) : donnees.audit.length === 0 ? (
          <p>Aucun événement enregistré pour l&apos;instant.</p>
        ) : (
          <div className="admin-tableau-conteneur">
            <table className="admin-tableau">
              <caption className="visuellement-cache">Derniers événements, du plus récent au plus ancien</caption>
              <thead>
                <tr>
                  <th scope="col">Date</th>
                  <th scope="col">Événement</th>
                  <th scope="col">Compte</th>
                </tr>
              </thead>
              <tbody>
                {donnees.audit.map((l, i) => (
                  <tr key={`${l.horodatage}-${i}`}>
                    <td>{date(l.horodatage)}</td>
                    <td>{LIBELLES_EVENEMENTS[l.evenement] ?? l.evenement}</td>
                    <td>{l.compte ?? (l.empreinteSaisie ? `adresse saisie n° ${l.empreinteSaisie}` : "—")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section id="parametres" className="admin-carte" aria-labelledby="titre-parametres">
        <h2 id="titre-parametres">Paramètres de configuration</h2>
        <p className="formulaire__aide">
          Lecture seule. Ces paramètres se modifient uniquement dans la configuration du serveur ; les valeurs
          secrètes ne sont jamais affichées.
        </p>
        <dl className="admin-liste">
          {donnees.parametres.map((p) => (
            <div key={p.libelle}>
              <dt>{p.libelle}</dt>
              <dd>
                {p.valeur}
                {p.note ? <span className="formulaire__aide"> — {p.note}</span> : null}
              </dd>
            </div>
          ))}
        </dl>
      </section>
    </div>
  );
}

export function AccesRefuse({ email }: { email: string }) {
  return (
    <section className="connexion">
      <div className="connexion__carte">
        <p className="connexion__surtitre">Accès refusé</p>
        <h1 className="titre-etape">Espace réservé aux administrateurs</h1>
        <p>
          Le compte <strong>{email}</strong> n&apos;a pas le rôle administrateur. Aucune donnée
          d&apos;administration n&apos;est affichée.
        </p>
        <form method="post" action="/api/deconnexion" className="actions">
          <button type="submit" className="bouton bouton--secondaire">
            Se déconnecter
          </button>
        </form>
      </div>
    </section>
  );
}
