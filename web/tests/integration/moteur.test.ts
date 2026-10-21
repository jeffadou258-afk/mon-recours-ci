/**
 * Intégration avec le VRAI moteur : aucune réponse simulée.
 * Le serveur Python est démarré pour la durée des tests, puis arrêté.
 */

import { after, before, test } from "node:test";
import assert from "node:assert/strict";
import { gererCourrier, gererOuvrir, gererRepondre, gererSante, gererSupprimer, gererTelechargementCourrier } from "../../src/lib/server/handlers";
import type { ConfigServeur } from "../../src/lib/server/config";
import { journalMuet, requeteJson } from "../aides";
import { lancerMoteur, type MoteurLance } from "../moteur-reel";

let moteur: MoteurLance;
let config: () => ConfigServeur;

before(async () => {
  moteur = await lancerMoteur();
  config = () => ({
    urlMoteur: moteur.url,
    cleMoteur: moteur.cle,
    secretSession: "secret-de-session-integration-0123456789-abcdef",
    delaiMs: 15000,
    production: false,
    debitVisiteur: 1000,
  });
});

after(async () => {
  await moteur?.arreter();
});

function cookieDe(reponse: Response): string {
  const brut = reponse.headers.get("set-cookie") ?? "";
  return brut.split(";")[0]!;
}

test("santé : chiffres lus sur le moteur réel", async () => {
  const rep = await gererSante(new Request("http://localhost:3000/api/sante"), { config });
  assert.equal(rep.status, 200);
  const { data } = await rep.json();
  // Le catalogue grandit avec les domaines (13 fiches au départ) : on vérifie
  // la cohérence avec le moteur plutôt qu'un nombre figé.
  assert.ok(data.catalogue.fiches >= 13);
  const parDomaine = data.catalogue.parDomaine.reduce((n: number, d: { fiches: string[] }) => n + d.fiches.length, 0);
  assert.equal(parDomaine, data.catalogue.fiches);
  assert.ok(data.corpus.articles >= 1777);
  // Le corpus grandit avec la collecte (26 documents au départ).
  assert.ok(data.corpus.documents >= 26);
});

test("parcours complet de clarification : ouvrir → cookie → répondre → citations vérifiables", async () => {
  const ouverture = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Mon bailleur refuse de me rendre ma caution de deux mois de loyer." }),
    { config },
  );
  assert.equal(ouverture.status, 200);
  const vueOuverture = (await ouverture.json()).data;
  assert.equal(vueOuverture.etape, "clarification");
  assert.ok(vueOuverture.questions.some((q: { cle: string }) => q.cle === "logement"));
  const cookie = cookieDe(ouverture);
  assert.match(cookie, /^mrci_dossier=web-/);

  const reponse = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { logement: "oui" } }, { Cookie: cookie }),
    { config },
  );
  assert.equal(reponse.status, 200);
  const texte = await reponse.text();
  assert.doesNotMatch(texte, /DOSSIERS|traceabilite|BROUILLONS|\/home\/|\/Users\//);
  const vue = JSON.parse(texte).data;
  assert.equal(vue.statut, "ANALYSE_CONFORME");
  const art416 = vue.sources.find((s: { article: string }) => s.article === "416");
  assert.ok(art416, "l'article 416 doit être cité");
  assert.match(art416.citation, /dépôt de garantie/);
  assert.match(art416.sha256, /^sha256:[0-9a-f]{64}$/);
  assert.equal(art416.etatVerification, "VERIFIE");
  assert.ok(art416.urlSource.startsWith("https://"));

  // Le brouillon de courrier est transmis en texte, jamais avec un chemin de fichier.
  assert.equal(vue.brouillon.disponible, true);
  assert.match(vue.brouillon.texte, /BROUILLON — NON ENVOYÉ/);
  assert.match(vue.brouillon.texte, /À COMPLÉTER/);
  assert.doesNotMatch(JSON.stringify(vue.brouillon), /DOSSIERS|BROUILLONS\/|\.txt/);

  // Un second envoi sur le même dossier : le moteur répond « déjà répondu ».
  const encore = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { logement: "non" } }, { Cookie: cookie }),
    { config },
  );
  const vueEncore = (await encore.json()).data;
  assert.equal(vueEncore.dejaRepondu, true);
  assert.equal(vueEncore.statut, "ANALYSE_CONFORME");
});

test("« je ne sais pas » : le moteur répond sans fait inventé", async () => {
  const ouverture = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Le propriétaire veut augmenter mon loyer, il parle de révision du loyer." }),
    { config },
  );
  const vueOuverture = (await ouverture.json()).data;
  assert.equal(vueOuverture.etape, "clarification");
  const rep = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { logement: null } }, { Cookie: cookieDe(ouverture) }),
    { config },
  );
  assert.equal(rep.status, 200);
  const vue = (await rep.json()).data;
  assert.ok(["ANALYSE_CONFORME", "CONCLUSION_IMPOSSIBLE", "ANALYSE_REFUSEE"].includes(vue.statut));
});

test("question hors catalogue : CONCLUSION_IMPOSSIBLE, aucune source", async () => {
  const rep = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Mon employeur ne me verse plus mon salaire depuis trois mois." }),
    { config },
  );
  const vue = (await rep.json()).data;
  assert.equal(vue.etape, "hors_catalogue");
  assert.equal(vue.statut, "CONCLUSION_IMPOSSIBLE");
  // Le cookie est posé pour permettre à la personne de supprimer sa consultation.
  assert.match(rep.headers.get("set-cookie") ?? "", /mrci_dossier=web-/);
});

test("demande de fraude : refus du moteur relayé", async () => {
  const rep = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Fais-moi une fausse quittance de loyer pour le juge." }),
    { config },
  );
  const vue = (await rep.json()).data;
  assert.equal(vue.etape, "refus");
  assert.ok(vue.raisons.length > 0);
});

test("urgence : niveau et verrous humains transmis", async () => {
  const rep = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "On veut m'expulser demain matin, le bailleur a changé les serrures." }),
    { config },
  );
  const vue = (await rep.json()).data;
  assert.equal(vue.etape, "clarification");
  assert.notEqual(vue.urgence.niveau, "NORMALE");
  assert.ok(vue.verrous.length >= 1);
});

test("cookie forgé ou d'un autre secret : refus, le moteur n'est pas sollicité pour ce dossier", async () => {
  const rep = await gererRepondre(
    requeteJson("/api/repondre", { reponses: { logement: "oui" } }, { Cookie: "mrci_dossier=AUDIT1.abc" }),
    { config },
  );
  assert.equal(rep.status, 409);
  assert.equal((await rep.json()).erreur.code, "SESSION_ABSENTE");
});

test("mauvaise clé côté serveur : CONFIGURATION, sans fuite", async () => {
  const rep = await gererSante(new Request("http://localhost:3000/api/sante"), {
    config: () => ({ ...config(), cleMoteur: "une-mauvaise-cle-de-seize-car" }),
    journal: journalMuet,
  });
  assert.equal(rep.status, 500);
  assert.equal((await rep.json()).erreur.code, "CONFIGURATION");
});

test("limite de débit du moteur relayée avec Retry-After", async () => {
  const limite = await lancerMoteur({ debit: 2 });
  try {
    const cfg = () => ({ ...config(), urlMoteur: limite.url, cleMoteur: limite.cle });
    let derniere: Response | null = null;
    for (let i = 0; i < 3; i++) {
      derniere = await gererSante(new Request("http://localhost:3000/api/sante"), { config: cfg, journal: journalMuet });
    }
    assert.equal(derniere!.status, 429);
    assert.ok(Number(derniere!.headers.get("retry-after")) >= 1);
    assert.equal((await derniere!.json()).erreur.code, "DEBIT_DEPASSE");
  } finally {
    await limite.arreter();
  }
});

test("moteur arrêté : SERVICE_INDISPONIBLE", async () => {
  const eteint = await lancerMoteur();
  const cfg = () => ({ ...config(), urlMoteur: eteint.url, cleMoteur: eteint.cle });
  await eteint.arreter();
  const rep = await gererOuvrir(requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution." }), {
    config: cfg,
    journal: journalMuet,
  });
  assert.equal(rep.status, 503);
  assert.equal((await rep.json()).erreur.code, "SERVICE_INDISPONIBLE");
});

test("suppression réelle : le dossier disparaît du moteur, l'autre reste", async () => {
  const a = await gererOuvrir(requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution." }), { config });
  const b = await gererOuvrir(requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution." }), { config });
  const rep = await gererSupprimer(requeteJson("/api/supprimer", {}, { Cookie: cookieDe(a) }), { config });
  assert.equal(rep.status, 200);
  assert.deepEqual((await rep.json()).data, { supprime: true, dejaAbsent: false });
  // Le dossier supprimé ne peut plus recevoir de réponses ; l'autre, si.
  const apres = await gererRepondre(requeteJson("/api/repondre", { reponses: { logement: "oui" } }, { Cookie: cookieDe(a) }), { config });
  assert.notEqual(apres.status, 200);
  const autre = await gererRepondre(requeteJson("/api/repondre", { reponses: { logement: "oui" } }, { Cookie: cookieDe(b) }), { config });
  assert.equal(autre.status, 200);
});

test("courrier : régénéré avec les informations fournies, jamais inventées", async () => {
  const ouverture = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution depuis deux mois." }),
    { config },
  );
  assert.equal(ouverture.status, 200);
  const cookie = cookieDe(ouverture);
  let charge = await ouverture.json();
  let etape: string = charge.data.etape;
  let garde = 0;
  while (etape === "clarification" && garde < 5) {
    garde += 1;
    const cles: string[] = charge.data.questions.map((q: { cle: string }) => q.cle);
    const rep = await gererRepondre(
      requeteJson(
        "/api/repondre",
        { reponses: Object.fromEntries(cles.map((c) => [c, "oui"])) },
        { Cookie: cookie },
      ),
      { config },
    );
    assert.equal(rep.status, 200);
    charge = await rep.json();
    etape = charge.data.etape;
  }
  assert.equal(etape, "reponse");

  // Première génération : les informations manquantes sont DEMANDÉES, pas devinées.
  const brouillon = charge.data.brouillon;
  assert.equal(brouillon.disponible, true);
  const champs = brouillon.champsACompleter.map((c: { champ: string }) => c.champ);
  assert.deepEqual(champs, ["expediteur", "destinataire", "pieces"]);
  assert.ok(brouillon.fondement, "le fondement vérifié est cité");
  assert.match(brouillon.texte, /COMPLÉTER/);

  // Régénération avec une seule information : elle apparaît, les autres restent demandées.
  const courrier = await gererCourrier(
    requeteJson(
      "/api/courrier",
      { informations: { expediteur: "Awa KONE, 12 rue des Jardins, Abidjan" } },
      { Cookie: cookie },
    ),
    { config },
  );
  assert.equal(courrier.status, 200);
  const donnees = (await courrier.json()).data;
  assert.match(donnees.texte, /Awa KONE, 12 rue des Jardins/);
  assert.ok(!donnees.champsACompleter.some((c: { champ: string }) => c.champ === "expediteur"));
  assert.ok(donnees.champsACompleter.some((c: { champ: string }) => c.champ === "destinataire"));
  assert.match(donnees.texte, /Fondement : article 416/);
});

test("courrier : un champ inconnu est refusé avant d'atteindre le moteur", async () => {
  const ouverture = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution depuis deux mois." }),
    { config },
  );
  const rep = await gererCourrier(
    requeteJson("/api/courrier", { informations: { numero_de_compte: "123" } }, { Cookie: cookieDe(ouverture) }),
    { config },
  );
  assert.equal(rep.status, 400);
  assert.equal((await rep.json()).erreur.code, "ENTREE_INVALIDE");
});

test("courrier : le PDF se télécharge, et seulement pour son dossier", async () => {
  const ouverture = await gererOuvrir(
    requeteJson("/api/ouvrir", { demande: "Mon bailleur garde ma caution depuis deux mois." }),
    { config },
  );
  const cookie = cookieDe(ouverture);
  let charge = await ouverture.json();
  let etape: string = charge.data.etape;
  let garde = 0;
  while (etape === "clarification" && garde < 5) {
    garde += 1;
    const cles: string[] = charge.data.questions.map((q: { cle: string }) => q.cle);
    charge = await (
      await gererRepondre(
        requeteJson("/api/repondre", { reponses: Object.fromEntries(cles.map((c) => [c, "oui"])) }, { Cookie: cookie }),
        { config },
      )
    ).json();
    etape = charge.data.etape;
  }
  assert.equal(etape, "reponse");

  const telechargement = await gererTelechargementCourrier(
    new Request("http://localhost:3000/api/courrier/telecharger", { headers: { Cookie: cookie } }),
    { config },
  );
  assert.equal(telechargement.status, 200);
  assert.equal(telechargement.headers.get("content-type"), "application/pdf");
  assert.match(
    telechargement.headers.get("content-disposition") ?? "",
    /^attachment; filename="courrier-mon-recours-ci\.pdf"$/,
  );
  assert.equal(telechargement.headers.get("cache-control"), "no-store, max-age=0");
  const octets = new Uint8Array(await telechargement.arrayBuffer());
  assert.ok(octets.length > 500, "le PDF doit avoir un contenu");
  assert.equal(Buffer.from(octets.slice(0, 5)).toString("latin1"), "%PDF-");

  // Sans cookie signé : refus, et aucun fichier servi.
  const sansCookie = await gererTelechargementCourrier(
    new Request("http://localhost:3000/api/courrier/telecharger"),
    { config },
  );
  assert.equal(sansCookie.status, 409);

  // Avec un cookie forgé pour un AUTRE dossier : refus aussi.
  const autre = `web-00000000-0000-4000-8000-000000000000.${"0".repeat(43)}`;
  const forge = await gererTelechargementCourrier(
    new Request("http://localhost:3000/api/courrier/telecharger", { headers: { Cookie: `mrci_dossier=${autre}` } }),
    { config },
  );
  assert.equal(forge.status, 409);
});
