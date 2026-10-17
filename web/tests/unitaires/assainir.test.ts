import { test } from "node:test";
import assert from "node:assert/strict";
import {
  assainirOuverture,
  assainirReponse,
  assainirSante,
  ReponseInattendue,
} from "../../src/lib/server/assainir";
import { fixture } from "../aides";

const CHEMIN_SERVEUR = /\/home\/|\/Users\/|DOSSIERS|\.json"|BROUILLONS|traceabilite|fichier_txt/;

test("clarification réelle : fiches, questions, urgence et verrous conservés", () => {
  const vue = assainirOuverture(fixture("ouvrir_urgence").data);
  assert.equal(vue.etape, "clarification");
  if (vue.etape !== "clarification") return;
  assert.equal(vue.urgence?.niveau, "ELEVEE");
  assert.equal(vue.fiches[0]?.article, "445");
  assert.equal(vue.fiches[0]?.etatVerification, "VERIFIE");
  assert.deepEqual(vue.questions, [{ cle: "logement", question: "S'agit-il d'un bail à usage d'habitation ?" }]);
  assert.equal(vue.verrous.length, 2);
  assert.equal(vue.verrous[0]?.code, "RISQUE_PERTE_DE_DROITS");
  assert.ok(!JSON.stringify(vue).includes("dossier_id"));
});

test("réponse réelle : citations mot pour mot, chemins de fichiers retirés", () => {
  const brut = fixture("repondre_caution");
  assert.match(JSON.stringify(brut), CHEMIN_SERVEUR, "la fixture doit contenir des chemins pour que le test ait un sens");
  const vue = assainirReponse(brut.data);
  const serialise = JSON.stringify(vue);
  assert.doesNotMatch(serialise, CHEMIN_SERVEUR);
  assert.equal(vue.statut, "ANALYSE_CONFORME");

  const brutSource = brut.data.reponse.sections["6_sources"][0];
  const source = vue.sources[0]!;
  assert.equal(source.citation, brutSource.citation, "la citation doit être identique au caractère près");
  assert.equal(source.sha256, brutSource.sha256_article);
  assert.equal(source.etatVerification, "VERIFIE");
  assert.equal(source.origineTexte, "CALQUE_TEXTE");
  assert.equal(source.recoupe, false);
  assert.ok(source.urlSource?.startsWith("https://www.dgi.gouv.ci/"));
  assert.equal(vue.droit[1]?.noteLecture, brut.data.reponse.sections["2_droit"][1].note_lecture);
  assert.equal(vue.brouillon?.disponible, true);
  assert.equal(vue.demarches.length, 7);
});

test("verrous renvoyés sous forme de chaînes par /repondre", () => {
  const vue = assainirReponse(fixture("repondre_urgence_vide").data);
  assert.equal(vue.verrous[0]?.code, "RISQUE_PERTE_DE_DROITS");
  assert.match(vue.verrous[0]!.motif, /expulsion/);
});

test("dossier déjà répondu : signalé, contenu identique", () => {
  const vue = assainirReponse(fixture("repondre_deja").data);
  assert.equal(vue.dejaRepondu, true);
  assert.equal(vue.statut, "ANALYSE_CONFORME");
});

test("hors catalogue : CONCLUSION_IMPOSSIBLE, aucune citation fabriquée", () => {
  const vue = assainirOuverture(fixture("ouvrir_hors").data);
  assert.equal(vue.etape, "hors_catalogue");
  if (vue.etape !== "hors_catalogue") return;
  assert.equal(vue.statut, "CONCLUSION_IMPOSSIBLE");
  assert.deepEqual(vue.domaines, ["travail"]);
  assert.equal(vue.articlesSansFiche[0]?.articles.length, 0);
  assert.equal(vue.couverture.length, 3);
});

test("refus : raison et suite sûre transmises", () => {
  const vue = assainirOuverture(fixture("ouvrir_refus").data);
  assert.equal(vue.etape, "refus");
  if (vue.etape !== "refus") return;
  assert.equal(vue.raisons[0]?.code, "PREUVE_FABRIQUEE");
  assert.match(vue.raisons[0]!.suite!, /fabriquer/);
});

test("santé réelle : intégrité affichée telle quelle", () => {
  const vue = assainirSante(fixture("sante").data);
  assert.equal(vue.catalogue.fiches, 13);
  assert.equal(vue.corpus.articles, 1777);
  assert.equal(vue.corpus.integrite, "ECART DETECTE");
  assert.ok(vue.domaines.some((d) => d.domaine === "travail" && d.statut === "BLOQUE_SOURCE"));
});

test("réponse malformée : erreur explicite, jamais une vue inventée", () => {
  assert.throws(() => assainirOuverture({ etape: "autre" }), ReponseInattendue);
  assert.throws(() => assainirOuverture(null), ReponseInattendue);
  assert.throws(() => assainirReponse({ etape: "reponse", reponse: {} }), ReponseInattendue);
});

test("champs de type inattendu : remplacés par une absence, pas par une valeur devinée", () => {
  const vue = assainirReponse({
    etape: "reponse",
    reponse: {
      statut_reponse: "ANALYSE_CONFORME",
      sections: {
        "2_droit": [{ titre: 12, article: null, citation: { x: 1 } }],
        "6_sources": [{ article: "1", citation: "c", url_source: "javascript:alert(1)", recoupe: "oui" }],
        "4_demarches": ["a", 3, null, ""],
      },
    },
  });
  assert.equal(vue.droit[0]?.article, "?");
  assert.equal(vue.droit[0]?.citation, "");
  assert.equal(vue.sources[0]?.urlSource, null, "une URL non http(s) ne doit jamais devenir un lien");
  assert.equal(vue.sources[0]?.recoupe, false);
  assert.equal(vue.sources[0]?.etatVerification, "NON_VERIFIE");
  assert.deepEqual(vue.demarches, ["a", "3"]);
});
