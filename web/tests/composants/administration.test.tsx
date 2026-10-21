import { test } from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { FormulaireConnexion } from "../../src/components/FormulaireConnexion";
import { AccesRefuse, TableauDeBord, type DonneesTableauDeBord } from "../../src/components/admin/TableauDeBord";

test("connexion : champs étiquetés, mot de passe masqué, lien « mot de passe oublié »", () => {
  const html = renderToStaticMarkup(<FormulaireConnexion disponibilite="actif" />);
  assert.match(html, /<label for="connexion-email"[^>]*>Adresse e-mail<\/label>/);
  assert.match(html, /<label for="connexion-mot-de-passe"[^>]*>Mot de passe<\/label>/);
  assert.match(html, /id="connexion-mot-de-passe"[^>]*type="password"/);
  assert.match(html, /autoComplete="current-password"|autocomplete="current-password"/i);
  assert.match(html, /aria-pressed="false"[^>]*aria-controls="connexion-mot-de-passe"/);
  assert.match(html, /href="\/connexion\/mot-de-passe-oublie"/);
  assert.match(html, /role="alert"/);
  assert.match(html, /Se connecter/);
  assert.doesNotMatch(html, /MONRECOURS_/);
});

test("connexion : désactivée en démonstration, avec une explication, sans champ actif", () => {
  const html = renderToStaticMarkup(<FormulaireConnexion disponibilite="desactive_demo" />);
  assert.match(html, /désactivé dans la démonstration publique/);
  assert.match(html, /id="connexion-email"[^>]*disabled/);
  assert.match(html, /type="submit"[^>]*disabled/);
  const nonConfigure = renderToStaticMarkup(<FormulaireConnexion disponibilite="non_configure" />);
  assert.match(nonConfigure, /Aucun compte n&#x27;est configuré|Aucun compte n'est configuré/);
});

const DONNEES: DonneesTableauDeBord = {
  compte: { email: "admin@exemple.ci", role: "administrateur" },
  plateforme: { mode: "reel", moteur: "injoignable", langageActif: null, versionInterface: "0.1.2" },
  sante: null,
  comptes: [
    { email: "admin@exemple.ci", role: "administrateur" },
    { email: "lecteur@exemple.ci", role: "lecteur" },
  ],
  comptesIgnores: 1,
  audit: null,
  parametres: [{ libelle: "Clé d'accès au moteur", valeur: "Configurée" }],
};

test("tableau de bord : rien d'inventé quand les données manquent", () => {
  const html = renderToStaticMarkup(<TableauDeBord donnees={DONNEES} />);
  for (const section of ["Vue d&#x27;ensemble", "État du corpus juridique", "Suivi des erreurs techniques", "Utilisateurs et rôles", "Journal d&#x27;audit", "Paramètres de configuration"]) {
    assert.ok(html.includes(section), `section absente : ${section}`);
  }
  assert.match(html, /Injoignable/);
  assert.ok((html.match(/Non connecté/g) ?? []).length >= 3, "corpus, erreurs et audit doivent être « Non connecté »");
  assert.match(html, /Non disponible/);
  assert.match(html, /1 entrée\(s\) de la configuration ont été ignorées/);
  assert.match(html, /action="\/api\/deconnexion"/);
  assert.doesNotMatch(html, /scrypt\$/);
});

test("accès refusé : aucune donnée d'administration pour un compte non administrateur", () => {
  const html = renderToStaticMarkup(<AccesRefuse email="lecteur@exemple.ci" />);
  assert.match(html, /Espace réservé aux administrateurs/);
  assert.doesNotMatch(html, /Tableau de bord|corpus|Journal/);
});
