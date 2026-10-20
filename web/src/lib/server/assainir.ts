/**
 * Assainissement des réponses du moteur avant envoi au navigateur.
 *
 * Principe : liste blanche. Seuls les champs nommés ici sont recopiés, sans
 * transformation de leur contenu juridique (citations, lectures, démarches sont
 * transmises mot pour mot). Sont volontairement RETIRÉS :
 *  - `traceabilite` et `brouillon.genere.fichier_*` : chemins de fichiers du
 *    serveur (CLAUDE_HANDOFF.md §6 quinquies, recommandation 6) ;
 *  - `dossier_id` : l'identifiant reste dans le cookie signé ;
 *  - les identifiants internes (`ref_ids`, `faits_ids`, dates d'ouverture de verrou).
 *
 * Une valeur absente ou d'un type inattendu devient `null` ou une liste vide :
 * l'interface affiche alors l'absence, elle ne la comble pas.
 */

import type {
  VueApplicationFaits,
  VueArticleSansFiche,
  VueContradiction,
  VueBrouillon,
  VueClarification,
  VueFicheIdentifiee,
  VueHorsCatalogue,
  VueOuverture,
  VueQuestion,
  VueRaisonRefus,
  VueRefus,
  VueRegleDroit,
  VueReponse,
  VueSante,
  VueSource,
  VueSuite,
  VueUrgence,
  VueVerrou,
} from "../types";

type Objet = Record<string, unknown>;

export class ReponseInattendue extends Error {}

function estObjet(v: unknown): v is Objet {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}
function objet(v: unknown): Objet {
  return estObjet(v) ? v : {};
}
function texte(v: unknown): string | null {
  if (typeof v === "string") return v;
  if (typeof v === "number" && Number.isFinite(v)) return String(v);
  return null;
}
function texteRequis(v: unknown, repli = ""): string {
  return texte(v) ?? repli;
}
function nombre(v: unknown): number | null {
  return typeof v === "number" && Number.isFinite(v) ? v : null;
}
function liste(v: unknown): unknown[] {
  return Array.isArray(v) ? v : [];
}
function textes(v: unknown): string[] {
  return liste(v)
    .map(texte)
    .filter((t): t is string => t !== null && t.trim().length > 0);
}
function urlPublique(v: unknown): string | null {
  const t = texte(v);
  if (!t) return null;
  try {
    const u = new URL(t);
    return u.protocol === "https:" || u.protocol === "http:" ? u.toString() : null;
  } catch {
    return null;
  }
}

function urgence(v: unknown): VueUrgence | null {
  if (!estObjet(v)) return null;
  const niveau = texte(v.niveau);
  if (!niveau) return null;
  return {
    niveau,
    consigne: texte(v.consigne),
    declencheurs: liste(v.declencheurs)
      .filter(estObjet)
      .map((d) => ({ libelle: texteRequis(d.libelle, "déclencheur"), detecte: texte(d.detecte) })),
  };
}

/** `/ouvrir` renvoie des objets de verrou, `/repondre` des chaînes « CODE — motif ». */
function verrous(v: unknown): VueVerrou[] {
  return liste(v)
    .map((element): VueVerrou | null => {
      if (typeof element === "string") {
        const separateur = element.indexOf(" — ");
        if (separateur > 0) {
          return { code: element.slice(0, separateur), motif: element.slice(separateur + 3), rappel: null };
        }
        return { code: null, motif: element, rappel: null };
      }
      if (estObjet(element)) {
        if (element.ouvert === false) return null;
        const motif = texte(element.motif);
        if (!motif) return null;
        return { code: texte(element.motif_code), motif, rappel: texte(element.rappel) };
      }
      return null;
    })
    .filter((x): x is VueVerrou => x !== null);
}

function fiche(v: Objet): VueFicheIdentifiee {
  return {
    titre: texteRequis(v.titre, "Fiche sans titre"),
    article: texteRequis(v.article, "?"),
    numeroTexte: texte(v.numero_texte),
    etatVerification: texteRequis(v.etat_verification, "NON_VERIFIE"),
  };
}

function question(v: Objet): VueQuestion | null {
  const cle = texte(v.cle);
  const libelle = texte(v.question);
  if (!cle || !libelle) return null;
  const s = objet(v.suggestion);
  const valeur = texte(s.valeur);
  const indice = texte(s.indice);
  return {
    cle,
    question: libelle,
    pourquoi: texte(v.pourquoi),
    suggestion: (valeur === "oui" || valeur === "non") && indice ? { valeur, indice } : null,
    confirmation: texte(v.confirmation),
  };
}

function contradictions(v: unknown): VueContradiction[] {
  return liste(v)
    .filter(estObjet)
    .map((c) => ({ cle: texteRequis(c.cle), message: texteRequis(c.message) }))
    .filter((c) => c.cle && c.message);
}

function clarification(d: Objet): VueClarification {
  const tour = nombre(d.tour);
  return {
    etape: "clarification",
    avertissement: texte(d.avertissement),
    urgence: urgence(d.urgence),
    verrous: verrous(d.verrous_humains),
    fiches: liste(d.fiches_identifiees).filter(estObjet).map(fiche),
    questions: liste(d.questions)
      .filter(estObjet)
      .map(question)
      .filter((q): q is VueQuestion => q !== null),
    noteCorpus: texte(d.note_corpus),
    tour: tour && tour >= 1 ? Math.floor(tour) : 1,
    contradictions: contradictions(d.contradictions),
    statutQuestions: texte(d.statut_questions),
    comprehension: {
      mode: objet(d.comprehension).mode === "llm" ? "llm" : "deterministe",
      resume: objet(d.comprehension).mode === "llm" ? texte(objet(d.comprehension).resume) : null,
    },
  };
}

function horsCatalogue(reponse: Objet, domainesData: unknown, d: Objet = {}): VueHorsCatalogue {
  const sansFiche = objet(reponse.articles_du_domaine_sans_fiche);
  const couverture = objet(reponse.couverture_du_catalogue);
  const domaines = textes(reponse.domaines_identifies);
  return {
    etape: "hors_catalogue",
    statut: "CONCLUSION_IMPOSSIBLE",
    urgence: urgence(d.urgence),
    verrous: verrous(d.verrous_humains),
    domainesVision: liste(reponse.domaines_vision)
      .filter(estObjet)
      .map((v) => ({
        code: nombre(v.code) ?? 0,
        libelle: texteRequis(v.libelle),
        fichesDisponibles: nombre(v.fiches_disponibles) ?? 0,
      }))
      .filter((v) => v.code >= 1 && v.code <= 24 && v.libelle.length > 0),
    message: texteRequis(
      reponse.message,
      "Aucune fiche de réponse ne correspond à votre question.",
    ),
    domaines: domaines.length ? domaines : textes(domainesData),
    articlesSansFiche: Object.entries(sansFiche).map(([domaine, articles]) => ({
      domaine,
      articles: liste(articles)
        .filter(estObjet)
        .map(
          (a): VueArticleSansFiche => ({
            article: texteRequis(a.article, "?"),
            numeroTexte: texte(a.numero_texte),
            etatVerification: texteRequis(a.etat_verification, "NON_VERIFIE"),
          }),
        ),
    })),
    pistes: textes(reponse.pistes_sans_fiche),
    couverture: Object.entries(couverture).map(([domaine, fiches]) => ({ domaine, fiches: textes(fiches) })),
    avertissement: texte(reponse.avertissement),
  };
}

function refus(reponse: Objet): VueRefus {
  const raisons = liste(reponse.raison)
    .filter(estObjet)
    .map(
      (r): VueRaisonRefus => ({
        code: texte(r.code),
        libelle: texteRequis(r.libelle, "Demande refusée par les garde-fous du service."),
        suite: texte(r.suite_sure),
      }),
    );
  return {
    etape: "refus",
    statut: "REFUS",
    raisons,
    avertissement: texte(reponse.avertissement),
  };
}

export function assainirOuverture(data: unknown): VueOuverture {
  const d = objet(data);
  const etape = texte(d.etape);
  if (etape === "clarification") return clarification(d);
  if (etape === "hors_catalogue") return horsCatalogue(objet(d.reponse), d.domaines, d);
  if (etape === "refus") return refus(objet(d.reponse));
  throw new ReponseInattendue(`étape d'ouverture inconnue : ${String(etape)}`);
}

function source(s: Objet): VueSource {
  return {
    reference: texte(s.reference),
    numeroTexte: texte(s.numero_texte),
    article: texteRequis(s.article, "?"),
    citation: texteRequis(s.citation),
    urlSource: urlPublique(s.url_source),
    sha256: texte(s.sha256_article),
    etatVerification: texteRequis(s.etat_verification, "NON_VERIFIE"),
    origineTexte: texte(s.origine_texte),
    recoupe: s.recoupe === true,
    confianceOcr: nombre(s.confiance_ocr),
    limites: texte(s.limites_texte),
    noteLecture: texte(s.note_lecture),
  };
}

function regle(r: Objet): VueRegleDroit {
  return {
    titre: texteRequis(r.titre, "Texte"),
    article: texteRequis(r.article, "?"),
    numeroTexte: texte(r.numero_texte),
    citation: texteRequis(r.citation),
    lecture: texte(r.lecture),
    noteLecture: texte(r.note_lecture),
  };
}

function brouillon(v: unknown): VueBrouillon | null {
  if (!estObjet(v)) return null;
  // `genere` contient des chemins de fichiers serveur : il n'est jamais transmis.
  // `texte` est le contenu du brouillon (moteur ≥ domaine-famille), borné en taille.
  const contenu = texte(v.texte);
  return {
    disponible: v.disponible === true,
    note: texte(v.note),
    raison: texte(v.raison),
    texte: contenu ? contenu.slice(0, 12000) : null,
  };
}

function applicationFaits(v: unknown): VueApplicationFaits | null {
  if (!estObjet(v)) return null;
  const lignes = liste(v.lignes)
    .filter(estObjet)
    .map((l) => ({
      question: texteRequis(l.question),
      reponse: texteRequis(l.reponse),
      lecture: texteRequis(l.lecture),
      articles: liste(l.articles)
        .filter(estObjet)
        .map((a) => ({ article: texteRequis(a.article, "?"), numeroTexte: texte(a.numero_texte) })),
      alerte: l.alerte === true,
    }))
    .filter((l) => l.question && l.lecture);
  return { statut: texte(v.statut), note: texte(v.note), lignes };
}

/** `/repondre` peut demander un tour de questions supplémentaire. */
export function assainirSuite(data: unknown): VueSuite {
  const d = objet(data);
  if (texte(d.etape) === "clarification") return clarification(d);
  return assainirReponse(data);
}

export function assainirReponse(data: unknown): VueReponse {
  const d = objet(data);
  const etape = texte(d.etape);
  if (etape !== "reponse" && etape !== "repondu") {
    throw new ReponseInattendue(`étape de réponse inconnue : ${String(etape)}`);
  }
  const r = objet(d.reponse);
  const statut = texte(r.statut_reponse);
  if (!statut) throw new ReponseInattendue("statut_reponse absent");
  const sections = objet(r.sections);
  const faits = objet(sections["1_faits"]);
  return {
    etape: "reponse",
    statut,
    dejaRepondu: etape === "repondu",
    demande: texte(faits.demande),
    noteFaits: texte(faits.note),
    droit: liste(sections["2_droit"]).filter(estObjet).map(regle),
    application: texte(sections["3_application"]),
    applicationFaits: applicationFaits(sections["3_application_aux_faits"]),
    manquantes: liste(sections["5_informations_manquantes"])
      .filter(estObjet)
      .map((m) => ({ question: texteRequis(m.question), pourquoi: texte(m.pourquoi) }))
      .filter((m) => m.question),
    contradictions: liste(sections["5_contradictions"])
      .filter(estObjet)
      .map((c) => texteRequis(c.message))
      .filter((m) => m.length > 0),
    demarches: textes(sections["4_demarches"]),
    aVerifier: textes(sections["5_a_verifier"]),
    sources: liste(sections["6_sources"]).filter(estObjet).map(source),
    verrous: verrous(r.verrous_humains),
    actionsExternesAutorisees:
      typeof r.actions_externes_autorisees === "boolean" ? r.actions_externes_autorisees : null,
    brouillon: brouillon(r.brouillon),
    avertissement: texte(r.avertissement),
  };
}

/**
 * Le moteur signale une analyse refusée par une erreur (code ANALYSE_REFUSEE).
 * C'est pourtant un résultat légitime : on le présente comme tel, sans conclusion.
 */
export function reponseAnalyseRefusee(): VueReponse {
  return {
    etape: "reponse",
    statut: "ANALYSE_REFUSEE",
    dejaRepondu: false,
    demande: null,
    noteFaits: null,
    droit: [],
    application: null,
    applicationFaits: null,
    manquantes: [],
    contradictions: [],
    demarches: [],
    aVerifier: [],
    sources: [],
    verrous: [],
    actionsExternesAutorisees: null,
    brouillon: null,
    avertissement: null,
  };
}

export function assainirSante(data: unknown): VueSante {
  const d = objet(data);
  const catalogue = objet(d.catalogue);
  const corpus = objet(d.corpus);
  return {
    catalogue: {
      fiches: nombre(catalogue.fiches) ?? 0,
      parDomaine: Object.entries(objet(catalogue.par_domaine)).map(([domaine, fiches]) => ({
        domaine,
        fiches: textes(fiches),
      })),
    },
    corpus: {
      integrite: texte(corpus.verdict_integrite),
      modeIntegrite: texte(corpus.mode_integrite),
      alteres: nombre(corpus.alteres),
      absents: nombre(corpus.absents),
      pdfNonDistribues: nombre(corpus.pdf_non_distribues),
      documents: nombre(corpus.documents),
      articles: nombre(corpus.articles),
      parOrigine: Object.entries(objet(corpus.articles_par_origine)).map(([origine, n]) => ({
        origine,
        articles: nombre(n) ?? 0,
      })),
    },
    domaines: liste(d.domaines)
      .filter(estObjet)
      .map((l) => ({
        domaine: texteRequis(l.domaine, "?"),
        statut: texteRequis(l.statut, "INCONNU"),
        completude: texteRequis(l.completude, "INCONNU"),
      })),
    langageActif: objet(d.langage).actif === true,
    avertissement: texte(d.avertissement),
  };
}
