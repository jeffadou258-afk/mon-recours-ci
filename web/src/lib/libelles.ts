/**
 * Libellés d'affichage. Ils traduisent des codes techniques du moteur en
 * français courant ; ils n'ajoutent AUCUNE information juridique.
 * Un code inconnu est affiché tel quel plutôt que deviné.
 */

const DOMAINES: Record<string, string> = {
  logement_baux_foncier: "Logement, baux et foncier",
  travail: "Travail",
  famille_mariage_filiation: "Famille, mariage et filiation",
  contrats_dettes_commerce: "Contrats, dettes et commerce",
  penal_procedure_penale: "Pénal et procédure pénale",
  consommation: "Consommation",
  associations_organisations_religieuses: "Associations et organisations religieuses",
  donnees_personnelles_numerique: "Données personnelles et numérique",
  administratif_voies_de_recours: "Administration et voies de recours",
  transport_responsabilite_civile: "Transport et responsabilité civile",
  sante_droits_usagers: "Santé et droits des usagers",
  indetermine: "Domaine non déterminé",
};

export function libelleDomaine(code: string): string {
  return DOMAINES[code] ?? code.replace(/_/g, " ");
}

const STATUTS_DOMAINE: Record<string, string> = {
  TERMINE_TECHNIQUEMENT: "Textes collectés",
  CORPUS_PARTIEL: "Textes partiels",
  BLOQUE_SOURCE: "Textes non disponibles",
  TERMINE_ET_VERIFIE: "Textes relus par un juriste",
};

export function libelleStatutDomaine(code: string): string {
  return STATUTS_DOMAINE[code] ?? code;
}

export interface PresentationStatut {
  titre: string;
  explication: string;
  ton: "neutre" | "attention" | "bloque";
}

export function presentationStatut(statut: string): PresentationStatut {
  switch (statut) {
    case "ANALYSE_CONFORME":
      return {
        titre: "Des textes du corpus correspondent à votre situation",
        explication:
          "Ils s'appliquent seulement si les faits que vous avez déclarés sont exacts. " +
          "Ce n'est ni un avis d'avocat, ni une décision de justice.",
        ton: "neutre",
      };
    case "CONCLUSION_IMPOSSIBLE":
      return {
        titre: "Aucune conclusion possible avec les textes disponibles",
        explication:
          "Le moteur n'a pas trouvé de source suffisante pour vous répondre. " +
          "Il préfère le dire plutôt que de citer un article au hasard.",
        ton: "attention",
      };
    case "ANALYSE_REFUSEE":
      return {
        titre: "Le moteur a refusé de conclure",
        explication:
          "Son analyse n'a pas passé ses propres contrôles de traçabilité. " +
          "Aucune conclusion n'est donnée.",
        ton: "attention",
      };
    case "REFUS":
      return {
        titre: "Demande refusée",
        explication: "Cette demande ne peut pas être traitée par le service.",
        ton: "bloque",
      };
    default:
      return {
        titre: `Statut du moteur : ${statut}`,
        explication: "Statut non reconnu par l'interface. Il est affiché sans interprétation.",
        ton: "attention",
      };
  }
}

export interface PresentationVerification {
  libelle: string;
  detail: string;
  /** `fiable` uniquement si la référence est vérifiée ET que le texte n'est pas un OCR non recoupé. */
  niveau: "fiable" | "a_verifier" | "non_fiable";
}

export function presentationVerification(
  etat: string,
  origine: string | null,
  recoupe: boolean,
): PresentationVerification {
  const ocrNonRecoupe = origine === "OCR_AUTO" && !recoupe;
  if (etat === "VERIFIE" && !ocrNonRecoupe) {
    return {
      libelle: "Référence vérifiée",
      detail:
        "Le texte a été rapproché de son document officiel. " +
        "Cela ne remplace pas une relecture par un juriste.",
      niveau: "fiable",
    };
  }
  if (etat === "VERIFIE" && ocrNonRecoupe) {
    return {
      libelle: "À vérifier : lecture automatique",
      detail:
        "La référence est identifiée, mais ce texte a été lu par reconnaissance optique " +
        "sans recoupement. Il peut contenir des erreurs de lecture.",
      niveau: "a_verifier",
    };
  }
  if (etat === "PARTIELLEMENT_VERIFIE") {
    return {
      libelle: "Partiellement vérifiée",
      detail: "Une partie seulement des informations sur ce texte a été confirmée.",
      niveau: "a_verifier",
    };
  }
  return {
    libelle: "Non vérifiée",
    detail: "Ne vous appuyez pas sur ce texte sans l'avoir contrôlé dans sa version officielle.",
    niveau: "non_fiable",
  };
}

export function libelleOrigineTexte(origine: string | null, recoupe: boolean, confiance: number | null): string {
  switch (origine) {
    case "CALQUE_TEXTE":
      return "Texte extrait directement du PDF officiel";
    case "VERIFIE_MANUELLEMENT":
      return "Texte relu manuellement";
    case "OCR_AUTO": {
      const c = confiance !== null ? ` (confiance ${confiance.toFixed(2).replace(".", ",")})` : "";
      return `Texte lu par reconnaissance optique${c}, ${recoupe ? "recoupé" : "non recoupé"}`;
    }
    case null:
      return "Mode de lecture non précisé par le moteur";
    default:
      return `Mode de lecture : ${origine}`;
  }
}

/**
 * Numéros d'urgence affichés uniquement quand le moteur classe la situation
 * CRITIQUE (core/urgence.py). Source : page « Côte d'Ivoire » du gouvernement du
 * Canada, rubrique services d'urgence locaux, consultée le 2026-10-17 :
 * https://voyage.gc.ca/assistance/ambassades-consulats/cote-d-ivoire
 * À faire confirmer par l'équipe avant mise en production.
 */
export const NUMEROS_URGENCE: { service: string; numeros: string[] }[] = [
  { service: "Police", numeros: ["170", "110", "111"] },
  { service: "Sapeurs-pompiers", numeros: ["180"] },
  { service: "Assistance médicale", numeros: ["185"] },
];
