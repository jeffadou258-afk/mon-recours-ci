"use client";

import { useRef, useState, type FormEvent } from "react";

/**
 * Formulaire de connexion. Il n'a aucune logique d'autorisation : il envoie
 * l'adresse et le mot de passe à POST /api/connexion, qui vérifie tout côté
 * serveur et pose le cookie de session (HttpOnly : illisible ici).
 */

export type DisponibiliteConnexion = "actif" | "desactive_demo" | "non_configure";

const MOTIF_EMAIL = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

interface ErreursChamps {
  email?: string;
  motDePasse?: string;
}

export function FormulaireConnexion({
  disponibilite,
  deconnecte = false,
}: {
  disponibilite: DisponibiliteConnexion;
  deconnecte?: boolean;
}) {
  const [email, setEmail] = useState("");
  const [motDePasse, setMotDePasse] = useState("");
  const [visible, setVisible] = useState(false);
  const [envoi, setEnvoi] = useState(false);
  const [erreurs, setErreurs] = useState<ErreursChamps>({});
  const [erreurGlobale, setErreurGlobale] = useState<string | null>(null);
  const refEmail = useRef<HTMLInputElement>(null);
  const refMotDePasse = useRef<HTMLInputElement>(null);
  const refErreur = useRef<HTMLDivElement>(null);

  const ferme = disponibilite !== "actif";

  async function soumettre(e: FormEvent) {
    e.preventDefault();
    if (ferme || envoi) return;
    const nouvelles: ErreursChamps = {};
    if (!MOTIF_EMAIL.test(email.trim())) nouvelles.email = "Saisissez une adresse e-mail valide.";
    if (!motDePasse) nouvelles.motDePasse = "Saisissez votre mot de passe.";
    setErreurs(nouvelles);
    setErreurGlobale(null);
    if (nouvelles.email) return refEmail.current?.focus();
    if (nouvelles.motDePasse) return refMotDePasse.current?.focus();

    setEnvoi(true);
    try {
      const reponse = await fetch("/api/connexion", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "same-origin",
        body: JSON.stringify({ email: email.trim(), motDePasse }),
      });
      const charge = (await reponse.json().catch(() => null)) as
        | { ok: true; data: { redirection: string } }
        | { ok: false; erreur: { message: string } }
        | null;
      if (charge && charge.ok) {
        setMotDePasse("");
        window.location.assign(charge.data.redirection === "/admin" ? "/admin" : "/");
        return;
      }
      setErreurGlobale(charge && !charge.ok ? charge.erreur.message : "La connexion a échoué. Réessayez.");
      setMotDePasse("");
    } catch {
      setErreurGlobale("Connexion impossible. Vérifiez votre accès à Internet puis réessayez.");
    } finally {
      setEnvoi(false);
    }
    requestAnimationFrame(() => refErreur.current?.focus());
  }

  return (
    <form className="formulaire connexion__formulaire" onSubmit={soumettre} noValidate aria-busy={envoi}>
      {deconnecte ? (
        <p className="connexion__info" role="status">
          Vous êtes déconnecté.
        </p>
      ) : null}

      {ferme ? (
        <div className="connexion__ferme" role="status">
          <p>
            <strong>
              {disponibilite === "desactive_demo"
                ? "L'espace d'administration est désactivé dans la démonstration publique."
                : "La connexion n'est pas disponible sur cette instance."}
            </strong>
          </p>
          <p>
            {disponibilite === "desactive_demo"
              ? "Cette démonstration ne contient aucun compte et n'ouvre aucun accès d'administration."
              : "Aucun compte n'est configuré sur ce serveur. Aucune connexion n'est possible tant qu'un administrateur ne l'a pas fait."}
          </p>
        </div>
      ) : null}

      <div
        ref={refErreur}
        tabIndex={-1}
        className={erreurGlobale ? "connexion__erreur" : undefined}
        role="alert"
        aria-live="assertive"
      >
        {erreurGlobale}
      </div>

      <div className="connexion__champ">
        <label htmlFor="connexion-email" className="formulaire__label">
          Adresse e-mail
        </label>
        <input
          ref={refEmail}
          id="connexion-email"
          name="email"
          type="email"
          inputMode="email"
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          required
          className="champ"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          disabled={ferme || envoi}
          aria-invalid={erreurs.email ? true : undefined}
          aria-describedby={erreurs.email ? "connexion-email-erreur" : undefined}
        />
        {erreurs.email ? (
          <p id="connexion-email-erreur" className="formulaire__erreur">
            {erreurs.email}
          </p>
        ) : null}
      </div>

      <div className="connexion__champ">
        <div className="connexion__ligne-label">
          <label htmlFor="connexion-mot-de-passe" className="formulaire__label">
            Mot de passe
          </label>
          <a href="/connexion/mot-de-passe-oublie" className="connexion__lien">
            Mot de passe oublié ?
          </a>
        </div>
        <div className="connexion__mot-de-passe">
          <input
            ref={refMotDePasse}
            id="connexion-mot-de-passe"
            name="motDePasse"
            type={visible ? "text" : "password"}
            autoComplete="current-password"
            required
            maxLength={1024}
            className="champ"
            value={motDePasse}
            onChange={(e) => setMotDePasse(e.target.value)}
            disabled={ferme || envoi}
            aria-invalid={erreurs.motDePasse ? true : undefined}
            aria-describedby={erreurs.motDePasse ? "connexion-mdp-erreur" : undefined}
          />
          <button
            type="button"
            className="connexion__afficher"
            onClick={() => setVisible((v) => !v)}
            aria-pressed={visible}
            aria-controls="connexion-mot-de-passe"
            disabled={ferme}
          >
            {visible ? "Masquer" : "Afficher"}
            <span className="visuellement-cache"> le mot de passe</span>
          </button>
        </div>
        {erreurs.motDePasse ? (
          <p id="connexion-mdp-erreur" className="formulaire__erreur">
            {erreurs.motDePasse}
          </p>
        ) : null}
      </div>

      <div className="actions">
        <button type="submit" className="bouton bouton--grand connexion__bouton" disabled={ferme || envoi}>
          {envoi ? (
            <>
              <span className="connexion__roue" aria-hidden="true" />
              Connexion en cours…
            </>
          ) : (
            "Se connecter"
          )}
        </button>
      </div>
    </form>
  );
}
