import { test } from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { assainirOuverture, assainirReponse, reponseAnalyseRefusee } from "../../src/lib/server/assainir";
import { VueRefusee, VueResultat, VueSansFiche } from "../../src/components/Resultats";
import { Clarification, composerReponse } from "../../src/components/Clarification";
import { BandeauUrgence, EncadreVerrous } from "../../src/components/Alertes";
import { Accueil } from "../../src/components/Accueil";
import { MessageErreur } from "../../src/components/MessageErreur";
import { assainirSante } from "../../src/lib/server/assainir";
import type { VueClarification, VueReponse } from "../../src/lib/types";
import { fixture } from "../aides";

function texteVisible(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x27;|&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ");
}

const reponseCaution = () => assainirReponse(fixture("repondre_caution").data);

test("citations : texte reproduit mot pour mot, avec badge et lien officiel", () => {
  const vue = reponseCaution();
  const html = renderToStaticMarkup(<VueResultat vue={vue} urgence={null} />);
  const visible = texteVisible(html);
  for (const source of vue.sources) {
    assert.ok(visible.includes(`« ${source.citation}`), `citation absente : ${source.citation.slice(0, 40)}`);
  }
  // Les extraits du moteur sont coupés (≈180 caractères) : la coupure est signalée.
  assert.ok(visible.includes("en fin de cont […] »"));
  assert.match(visible, /Le texte complet figure dans le document officiel/);
  assert.ok(visible.includes("Art. 416"));
  assert.ok(visible.includes("Référence vérifiée"));
  assert.ok(html.includes('href="https://www.dgi.gouv.ci/'));
  assert.ok(html.includes('rel="noopener noreferrer"'));
  assert.ok(visible.includes("Reformulation : seul le texte cité ci-dessus fait foi."));
  assert.ok(visible.includes("Des textes du corpus correspondent à votre situation"));
  assert.ok(!visible.includes("/home/"), "aucun chemin serveur ne doit apparaître");
});

test("le statut ANALYSE_CONFORME n'est jamais présenté comme une garantie", () => {
  const visible = texteVisible(renderToStaticMarkup(<VueResultat vue={reponseCaution()} urgence={null} />));
  assert.match(visible, /seulement si les faits que vous avez déclarés sont exacts/);
  assert.doesNotMatch(visible, /vous avez gagné|garanti que|vous obtiendrez/i);
});

test("texte OCR non recoupé (variante dérivée) : jamais affiché comme vérifié", () => {
  const vue: VueReponse = reponseCaution();
  const variante: VueReponse = {
    ...vue,
    sources: vue.sources.map((s, i) => (i === 0 ? { ...s, origineTexte: "OCR_AUTO", recoupe: false, confianceOcr: 0.81 } : s)),
  };
  const html = renderToStaticMarkup(<VueResultat vue={variante} urgence={null} />);
  const premiereCarte = html.split("<article")[1]!;
  assert.match(premiereCarte, /citation--a_verifier/);
  assert.match(texteVisible(premiereCarte), /À vérifier : lecture automatique/);
  assert.doesNotMatch(texteVisible(premiereCarte), /Référence vérifiée/);
  assert.match(texteVisible(premiereCarte), /reconnaissance optique \(confiance 0,81\), non recoupé/);
});

test("référence NON_VERIFIE (variante dérivée) : signalée comme non fiable", () => {
  const vue = reponseCaution();
  const variante: VueReponse = {
    ...vue,
    sources: vue.sources.map((s) => ({ ...s, etatVerification: "NON_VERIFIE" })),
  };
  const visible = texteVisible(renderToStaticMarkup(<VueResultat vue={variante} urgence={null} />));
  assert.match(visible, /Non vérifiée/);
  assert.doesNotMatch(visible, /Référence vérifiée/);
});

test("réponse sans source : l'absence est dite clairement", () => {
  const visible = texteVisible(renderToStaticMarkup(<VueResultat vue={reponseAnalyseRefusee()} urgence={null} />));
  assert.match(visible, /Le moteur a refusé de conclure/);
  assert.match(visible, /Aucun texte n'est cité : le moteur n'a retenu aucune source fiable/);
});

test("hors catalogue : CONCLUSION_IMPOSSIBLE et couverture réelle, aucune citation", () => {
  const vue = assainirOuverture(fixture("ouvrir_hors").data);
  if (vue.etape !== "hors_catalogue") throw new Error("fixture inattendue");
  const html = renderToStaticMarkup(<VueSansFiche vue={vue} />);
  const visible = texteVisible(html);
  assert.match(visible, /Aucune conclusion possible avec les textes disponibles/);
  assert.match(visible, /Travail/);
  assert.match(visible, /Dépôt de garantie \(caution\)/);
  assert.ok(!html.includes("<blockquote"), "aucune citation ne doit être affichée");
  assert.match(visible, /Faire relire votre situation/);
});

test("refus : raison et alternative sûre affichées", () => {
  const vue = assainirOuverture(fixture("ouvrir_refus").data);
  if (vue.etape !== "refus") throw new Error("fixture inattendue");
  const visible = texteVisible(renderToStaticMarkup(<VueRefusee vue={vue} />));
  assert.match(visible, /Demande refusée/);
  assert.match(visible, /Je ne peux pas fabriquer ni falsifier une preuve/);
});

test("urgence élevée et verrous humains : encadrés visibles et non masquables", () => {
  const vue = assainirOuverture(fixture("ouvrir_urgence").data) as VueClarification;
  const html = renderToStaticMarkup(
    <>
      <BandeauUrgence urgence={vue.urgence} />
      <EncadreVerrous verrous={vue.verrous} />
    </>,
  );
  const visible = texteVisible(html);
  assert.match(visible, /Situation à traiter rapidement/);
  assert.match(visible, /procedure d'expulsion/);
  assert.match(visible, /Un professionnel doit intervenir avant toute démarche/);
  assert.match(visible, /Risque d'expulsion/);
  assert.ok(!html.includes("<button"), "aucun bouton de fermeture");
  assert.ok(!html.includes("tel:"), "pas de numéros d'urgence pour un niveau ÉLEVÉ");
});

test("urgence critique : numéros d'appel cliquables", () => {
  const html = renderToStaticMarkup(
    <BandeauUrgence urgence={{ niveau: "CRITIQUE", consigne: "Sécurité d'abord.", declencheurs: [] }} />,
  );
  assert.match(html, /role="alert"/);
  for (const n of ["170", "180", "185"]) assert.ok(html.includes(`href="tel:${n}"`));
});

test("urgence normale : aucun bandeau", () => {
  assert.equal(renderToStaticMarkup(<BandeauUrgence urgence={{ niveau: "NORMALE", consigne: null, declencheurs: [] }} />), "");
});

test("clarification : questions et choix « Je ne sais pas »", () => {
  const vue = assainirOuverture(fixture("ouvrir_caution").data) as VueClarification;
  const html = renderToStaticMarkup(<Clarification vue={vue} envoi={false} onEnvoyer={() => undefined} />);
  const visible = texteVisible(html);
  assert.match(visible, /S'agit-il d'un bail à usage d'habitation \?/);
  assert.match(visible, /Je ne sais pas/);
  assert.match(visible, /Dépôt de garantie \(caution\)/);
  assert.match(html, /<legend>/);
});

test("composition des réponses : « je ne sais pas » envoie null", () => {
  assert.equal(composerReponse({ choix: "oui", precision: "" }), "oui");
  assert.equal(composerReponse({ choix: "non", precision: "bail commercial" }), "non, bail commercial");
  assert.equal(composerReponse({ choix: "inconnu", precision: "" }), null);
  assert.equal(composerReponse({ choix: "", precision: "  " }), null);
  assert.equal(composerReponse({ choix: "inconnu", precision: "je crois que oui" }), "je crois que oui");
});

test("accueil : couverture lue sur le moteur, ou indisponibilité annoncée", () => {
  const avec = texteVisible(renderToStaticMarkup(<Accueil sante={assainirSante(fixture("sante").data)} />));
  assert.match(avec, /13 situations sont couvertes/);
  assert.match(avec, /Textes non disponibles/);
  const sans = texteVisible(renderToStaticMarkup(<Accueil sante={null} />));
  assert.match(sans, /Le moteur juridique ne répond pas pour le moment/);
  assert.doesNotMatch(sans, /situations sont couvertes/);
});

test("erreurs : réseau, service indisponible, session expirée", () => {
  const reseau = texteVisible(
    renderToStaticMarkup(
      <MessageErreur erreur={{ code: "RESEAU", message: "Connexion impossible.", reessayable: true }} onReessayer={() => undefined} />,
    ),
  );
  assert.match(reseau, /Pas de connexion/);
  assert.match(reseau, /Réessayer/);
  const session = texteVisible(
    renderToStaticMarkup(
      <MessageErreur
        erreur={{ code: "SESSION_ABSENTE", message: "Expirée.", reessayable: false }}
        onRecommencer={() => undefined}
      />,
    ),
  );
  assert.match(session, /Recommencer/);
  assert.doesNotMatch(session, /Réessayer/);
});
