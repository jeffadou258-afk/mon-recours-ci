import { test } from "node:test";
import assert from "node:assert/strict";
import { renderToStaticMarkup } from "react-dom/server";
import { ChoixSituation } from "../../src/components/ChoixSituation";
import { assainirOuverture } from "../../src/lib/server/assainir";
import type { VueAiguillage } from "../../src/lib/types";

/**
 * Ce que l'interface doit montrer quand le moteur ne peut pas décider seule
 * laquelle de plusieurs procédures s'applique.
 */

function texteVisible(html: string): string {
  return html
    .replace(/<[^>]+>/g, " ")
    .replace(/&#x27;|&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&amp;/g, "&")
    .replace(/\s+/g, " ");
}

const CHARGE = {
  etape: "aiguillage",
  dossier_id: "DOSSIER-TEST",
  situation: "logement_reprise_par_le_bailleur",
  question: "Parmi ces situations, laquelle correspond à la vôtre ?",
  pourquoi: "Ces trois démarches ne s'appliquent pas aux mêmes faits.",
  message: "Plusieurs situations peuvent correspondre à ce que vous décrivez.",
  option_aucune: "Aucune de ces situations ne correspond à la mienne",
  avertissement: "Je suis un service d'information juridique, pas un avocat.",
  options: [
    {
      cle: "LOGEME_440",
      libelle: "Le propriétaire veut reprendre le logement, pour l'habiter lui-même ou pour le vendre",
      titre: "Congé donné par le bailleur",
      article: "440",
      numero_texte: "2019-576",
      etat_verification: "VERIFIE",
    },
    {
      cle: "LOGEME_445",
      libelle: "Le propriétaire veut me faire partir, ou menace de le faire sans passer par le juge",
      titre: "Expulsion forcée",
      article: "445",
      numero_texte: "2019-576",
      etat_verification: "VERIFIE",
    },
    {
      cle: "LOGEME_443",
      libelle: "C'est moi qui veux quitter le logement avant la fin du bail",
      titre: "Demande de résiliation",
      article: "443",
      numero_texte: "2019-576",
      etat_verification: "VERIFIE",
    },
  ],
};

function vue(): VueAiguillage {
  return assainirOuverture(CHARGE) as VueAiguillage;
}

test("aiguillage : les situations sont proposées, en langage simple", () => {
  const html = renderToStaticMarkup(<ChoixSituation vue={vue()} onChoisir={() => {}} />);
  const visible = texteVisible(html);
  assert.equal(vue().etape, "aiguillage");
  assert.ok(visible.includes("Parmi ces situations, laquelle correspond à la vôtre ?"));
  for (const option of vue().options) {
    assert.ok(visible.includes(option.libelle), `option absente : ${option.cle}`);
  }
  // Aucun libellé ne doit exiger de connaître une notion juridique.
  for (const interdit of ["résiliation", "exécution", "référé", "nullité"]) {
    assert.ok(
      !vue().options.some((o) => o.libelle.toLowerCase().includes(interdit)),
      `le libellé emploie « ${interdit} », que le citoyen ne connaît pas`,
    );
  }
});

test("aiguillage : une option « aucune situation » est toujours offerte", () => {
  const html = renderToStaticMarkup(<ChoixSituation vue={vue()} onChoisir={() => {}} />);
  const visible = texteVisible(html);
  assert.ok(visible.includes("Aucune de ces situations ne correspond à la mienne"));
  // Quatre boutons radio : trois situations + « aucune ».
  assert.equal((html.match(/type="radio"/g) ?? []).length, 4);
  // Une seule sélection possible : même nom de groupe pour tous.
  const noms = new Set((html.match(/name="([^"]+)"/g) ?? []).map((n) => n));
  assert.equal(noms.size, 1, "les boutons n'appartiennent pas au même groupe");
});

test("aiguillage : on ne peut pas valider sans avoir choisi", () => {
  const html = renderToStaticMarkup(<ChoixSituation vue={vue()} onChoisir={() => {}} />);
  assert.match(html, /<button[^>]*disabled/);
  assert.doesNotMatch(html, /type="radio"[^>]*checked/);
});

test("aiguillage : la sélection invalide est signalée, sans conclusion", () => {
  const avecErreur = { ...vue(), erreurSelection: "Choisissez l'une des situations proposées." };
  const html = renderToStaticMarkup(<ChoixSituation vue={avecErreur} onChoisir={() => {}} />);
  const visible = texteVisible(html);
  assert.ok(visible.includes("Choisissez l'une des situations proposées."));
  assert.match(html, /role="alert"/);
  assert.ok(!visible.includes("Ce que disent les textes"), "une conclusion a été affichée");
});

test("aiguillage : le message d'incertitude est affiché, pas une affirmation de droit", () => {
  const visible = texteVisible(
    renderToStaticMarkup(<ChoixSituation vue={vue()} onChoisir={() => {}} />),
  );
  assert.ok(visible.includes("Plusieurs situations peuvent correspondre"));
  assert.ok(visible.includes("pas un avocat"));
});

test("assainir : un aiguillage doit porter au moins deux options exploitables", () => {
  assert.throws(() => assainirOuverture({ ...CHARGE, options: [CHARGE.options[0]] }));
  assert.throws(() => assainirOuverture({ ...CHARGE, options: [] }));
  assert.throws(() =>
    assainirOuverture({ ...CHARGE, options: [{ cle: "", libelle: "" }, { cle: "X", libelle: "" }] }),
  );
});

test("assainir : une étape inconnue reste refusée", () => {
  assert.throws(() => assainirOuverture({ etape: "aiguillage_bis" }));
});
