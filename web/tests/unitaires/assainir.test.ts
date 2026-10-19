import { test } from "node:test";
import assert from "node:assert/strict";
import {
  assainirOuverture,
  assainirReponse,
  assainirSuite,
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
  assert.deepEqual(vue.questions, [
    {
      cle: "logement",
      question: "S'agit-il d'un bail à usage d'habitation ?",
      pourquoi: null,
      suggestion: null,
      confirmation: null,
    },
  ]);
  assert.equal(vue.tour, 1);
  assert.deepEqual(vue.contradictions, []);
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
  // Fixture enregistrée avant l'ajout de `texte` au moteur : absence tolérée.
  assert.equal(vue.brouillon?.texte, null);
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

test("tour suivant : questions, suggestion, confirmation et contradiction transmises", () => {
  const vue = assainirSuite({
    etape: "clarification",
    dossier_id: "web-secret",
    tour: 2,
    questions: [
      {
        cle: "depot_plus_deux_mois",
        question: "Le dépôt dépasse-t-il deux mois de loyer ?",
        pourquoi: "L'article 416 fixe un plafond.",
        suggestion: { valeur: "oui", indice: "caution de trois mois" },
        confirmation: "Votre récit mentionne « caution de trois mois »…",
      },
      { cle: "x", question: "Pirate ?", suggestion: { valeur: "<script>", indice: "a" } },
    ],
    contradictions: [{ cle: "depot_plus_deux_mois", message: "Votre récit mentionne…", recit: "x" }],
    statut_questions: "A_RELIRE_PAR_UN_JURISTE",
  });
  assert.equal(vue.etape, "clarification");
  if (vue.etape !== "clarification") return;
  assert.equal(vue.tour, 2);
  assert.equal(vue.questions[0]?.suggestion?.valeur, "oui");
  assert.match(vue.questions[0]?.confirmation ?? "", /caution de trois mois/);
  assert.equal(vue.questions[1]?.suggestion, null, "une valeur de suggestion inconnue est écartée");
  assert.deepEqual(vue.contradictions, [{ cle: "depot_plus_deux_mois", message: "Votre récit mentionne…" }]);
  assert.equal(vue.statutQuestions, "A_RELIRE_PAR_UN_JURISTE");
  assert.ok(!JSON.stringify(vue).includes("web-secret"));
});

test("résultat : lectures au vu des réponses, manques et contradictions transmis", () => {
  const brut = fixture("repondre_caution");
  const data = structuredClone(brut.data);
  data.reponse.sections["3_application_aux_faits"] = {
    statut: "A_RELIRE_PAR_UN_JURISTE",
    note: "Lectures, pas des citations.",
    lignes: [
      {
        cle: "depot_plus_deux_mois",
        question: "Le dépôt dépasse-t-il deux mois de loyer ?",
        reponse: "oui",
        lecture: "Selon l'article 416, le dépôt ne peut excéder deux mois de loyer.",
        articles: [{ article: "416", numero_texte: "2019-576" }],
        alerte: false,
      },
    ],
  };
  data.reponse.sections["5_informations_manquantes"] = [{ cle: "q", question: "Avez-vous quitté le logement ?", pourquoi: "Fin de contrat." }];
  data.reponse.sections["5_contradictions"] = [{ cle: "q", message: "Le récit et la réponse divergent." }];
  const vue = assainirSuite(data);
  assert.equal(vue.etape, "reponse");
  if (vue.etape !== "reponse") return;
  assert.equal(vue.applicationFaits?.lignes[0]?.articles[0]?.numeroTexte, "2019-576");
  assert.equal(vue.manquantes[0]?.pourquoi, "Fin de contrat.");
  assert.deepEqual(vue.contradictions, ["Le récit et la réponse divergent."]);
});

test("compréhension : le résumé n'est transmis qu'en mode modèle de langage", () => {
  const base = { etape: "clarification", questions: [], fiches_identifiees: [] };
  const sans = assainirSuite({ ...base, comprehension: { mode: "deterministe", resume: "texte parasite" } });
  const avec = assainirSuite({ ...base, comprehension: { mode: "llm", resume: "La personne a quitté le logement." } });
  const absent = assainirSuite(base);
  if (sans.etape !== "clarification" || avec.etape !== "clarification" || absent.etape !== "clarification") {
    assert.fail("clarification attendue");
  }
  assert.deepEqual(sans.comprehension, { mode: "deterministe", resume: null });
  assert.equal(avec.comprehension.resume, "La personne a quitté le logement.");
  assert.equal(absent.comprehension.mode, "deterministe");
});
