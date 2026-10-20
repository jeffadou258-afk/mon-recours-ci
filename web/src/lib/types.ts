/**
 * Types de l'interface.
 *
 * Deux familles :
 *  - `Brut*`  : ce que renvoie réellement `bin/serveur_api.py` (relevé le
 *    2026-10-17 en appelant le serveur, voir CLAUDE_HANDOFF.md §6 quinquies).
 *    Ces types ne sont utilisés QUE côté serveur, par l'assainisseur.
 *  - `Vue*`   : ce que la couche serveur de Next.js transmet au navigateur,
 *    après avoir retiré les chemins de fichiers et tout champ non prévu.
 *
 * Aucun de ces types ne contient de règle de droit : ils transportent le
 * contenu produit par le moteur, sans le modifier.
 */

// ---------------------------------------------------------------------------
// Valeurs connues (le moteur peut en ajouter : on garde `string` en repli)
// ---------------------------------------------------------------------------

export type StatutReponse =
  | "ANALYSE_CONFORME"
  | "CONCLUSION_IMPOSSIBLE"
  | "ANALYSE_REFUSEE"
  | "REFUS";

export type NiveauUrgence = "CRITIQUE" | "ELEVEE" | "NORMALE";

export type EtatVerification =
  | "VERIFIE"
  | "PARTIELLEMENT_VERIFIE"
  | "NON_VERIFIE"
  | "NON_CONFIRME"
  | "OBSOLETE";

export type OrigineTexte = "CALQUE_TEXTE" | "OCR_AUTO" | "VERIFIE_MANUELLEMENT";

// ---------------------------------------------------------------------------
// Vues transmises au navigateur
// ---------------------------------------------------------------------------

export interface VueUrgence {
  niveau: NiveauUrgence | string;
  consigne: string | null;
  declencheurs: { libelle: string; detecte: string | null }[];
}

export interface VueVerrou {
  code: string | null;
  motif: string;
  rappel: string | null;
}

export interface VueFicheIdentifiee {
  titre: string;
  article: string;
  numeroTexte: string | null;
  etatVerification: EtatVerification | string;
}

export interface VueQuestion {
  cle: string;
  question: string;
  /** Pourquoi la question compte (condition de l'article). */
  pourquoi: string | null;
  /** Ce que le récit laisse penser : pré-sélection modifiable, jamais une réponse. */
  suggestion: { valeur: "oui" | "non"; indice: string } | null;
  /** Message de confirmation quand la réponse précédente contredisait le récit. */
  confirmation: string | null;
}

export interface VueContradiction {
  cle: string;
  message: string;
}

export interface VueComprehension {
  /** « llm » si un modèle de langage a aidé à comprendre le récit, sinon « deterministe ». */
  mode: "llm" | "deterministe";
  /** Résumé rédigé par le modèle, contrôlé (aucun nombre ajouté) — à vérifier par la personne. */
  resume: string | null;
}

export interface VueClarification {
  etape: "clarification";
  avertissement: string | null;
  urgence: VueUrgence | null;
  verrous: VueVerrou[];
  fiches: VueFicheIdentifiee[];
  questions: VueQuestion[];
  noteCorpus: string | null;
  /** Numéro du tour de questions (1, 2 ou 3). */
  tour: number;
  contradictions: VueContradiction[];
  /** Statut des questions du guide (ex. A_RELIRE_PAR_UN_JURISTE). */
  statutQuestions: string | null;
  comprehension: VueComprehension;
}

export interface VueArticleSansFiche {
  article: string;
  numeroTexte: string | null;
  etatVerification: string;
}

export interface VueHorsCatalogue {
  etape: "hors_catalogue";
  statut: "CONCLUSION_IMPOSSIBLE";
  /** Urgence et verrous : restitués même sans fiche (ex. violences). */
  urgence: VueUrgence | null;
  verrous: VueVerrou[];
  /** Domaine(s) probable(s) parmi les 24 de la vision, et fiches réellement disponibles. */
  domainesVision: { code: number; libelle: string; fichesDisponibles: number }[];
  message: string;
  domaines: string[];
  articlesSansFiche: { domaine: string; articles: VueArticleSansFiche[] }[];
  pistes: string[];
  couverture: { domaine: string; fiches: string[] }[];
  avertissement: string | null;
}

export interface VueRaisonRefus {
  code: string | null;
  libelle: string;
  suite: string | null;
}

export interface VueRefus {
  etape: "refus";
  statut: "REFUS";
  raisons: VueRaisonRefus[];
  avertissement: string | null;
}

export type VueOuverture = VueClarification | VueHorsCatalogue | VueRefus;

export interface VueRegleDroit {
  titre: string;
  article: string;
  numeroTexte: string | null;
  citation: string;
  lecture: string | null;
  noteLecture: string | null;
}

export interface VueSource {
  reference: string | null;
  numeroTexte: string | null;
  article: string;
  citation: string;
  urlSource: string | null;
  sha256: string | null;
  etatVerification: EtatVerification | string;
  origineTexte: OrigineTexte | string | null;
  recoupe: boolean;
  confianceOcr: number | null;
  limites: string | null;
  noteLecture: string | null;
}

export interface VueChampCourrier {
  champ: string;
  libelle: string;
  question: string;
  exemple: string | null;
}

export interface VueBrouillon {
  disponible: boolean;
  note: string | null;
  raison: string | null;
  /** Texte du brouillon préparé par le moteur, à relire et compléter. Jamais envoyé. */
  texte: string | null;
  /** Article d'une référence VÉRIFIÉE seulement — jamais un texte OCR. */
  fondement: string | null;
  /** Informations que seul l'utilisateur peut fournir, encore manquantes. */
  champsACompleter: VueChampCourrier[];
}

/** Réponse de /api/courrier : le courrier régénéré avec les informations fournies. */
export interface VueCourrier {
  texte: string | null;
  fondement: string | null;
  champsACompleter: VueChampCourrier[];
  note: string | null;
  pdfDisponible: boolean;
}

export interface VueLectureFait {
  question: string;
  reponse: "oui" | "non" | string;
  lecture: string;
  articles: { article: string; numeroTexte: string | null }[];
  alerte: boolean;
}

export interface VueApplicationFaits {
  statut: string | null;
  note: string | null;
  lignes: VueLectureFait[];
}

export interface VueReponse {
  etape: "reponse";
  statut: StatutReponse | string;
  /** `true` si le moteur indique que ce dossier avait déjà reçu sa réponse. */
  dejaRepondu: boolean;
  demande: string | null;
  noteFaits: string | null;
  droit: VueRegleDroit[];
  application: string | null;
  /** Lectures des articles au vu des réponses (jamais des citations). */
  applicationFaits: VueApplicationFaits | null;
  manquantes: { question: string; pourquoi: string | null }[];
  contradictions: string[];
  demarches: string[];
  aVerifier: string[];
  sources: VueSource[];
  verrous: VueVerrou[];
  actionsExternesAutorisees: boolean | null;
  brouillon: VueBrouillon | null;
  avertissement: string | null;
}

/** Réponse de /api/repondre : un nouveau tour de questions, ou le résultat. */
export type VueSuite = VueClarification | VueReponse;

export interface VueSante {
  catalogue: { fiches: number; parDomaine: { domaine: string; fiches: string[] }[] };
  corpus: {
    integrite: string | null;
    /** « strict » ou « pdf_non_distribues_toleres » : le verdict se lit avec lui. */
    modeIntegrite?: string | null;
    alteres?: number | null;
    absents?: number | null;
    pdfNonDistribues?: number | null;
    documents: number | null;
    articles: number | null;
    parOrigine: { origine: string; articles: number }[];
  };
  domaines: { domaine: string; statut: string; completude: string }[];
  /** Un modèle de langage est-il activé côté serveur ? */
  langageActif: boolean;
  avertissement: string | null;
}

// ---------------------------------------------------------------------------
// Enveloppe des réponses de /api/*
// ---------------------------------------------------------------------------

export type CodeErreur =
  | "ENTREE_INVALIDE"
  | "TYPE_NON_SUPPORTE"
  | "CORPS_TROP_GRAND"
  | "ORIGINE_REFUSEE"
  | "SESSION_ABSENTE"
  | "DOSSIER_INCONNU"
  | "DEBIT_DEPASSE"
  | "SERVICE_INDISPONIBLE"
  | "CONFIGURATION"
  | "CATALOGUE_INVALIDE"
  | "REPONSE_INVALIDE"
  | "RESEAU"
  | "INTERNE";

export interface ErreurApi {
  code: CodeErreur;
  message: string;
  reessayable: boolean;
  reessayerDansSecondes?: number;
}

export type ResultatApi<T> = { ok: true; data: T } | { ok: false; erreur: ErreurApi };
