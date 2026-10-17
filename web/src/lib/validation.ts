/**
 * Validation des entrées — partagée entre le navigateur (retour immédiat) et la
 * couche serveur (autorité). Les limites reprennent celles de `core/service.py`
 * (LONGUEUR_MAX_DEMANDE = 4000, LONGUEUR_MAX_REPONSE = 1000) : la couche web ne
 * doit jamais accepter ce que le moteur refuserait.
 */

export const LONGUEUR_MAX_DEMANDE = 4000;
export const LONGUEUR_MIN_DEMANDE = 10;
export const LONGUEUR_MAX_REPONSE = 1000;
export const NOMBRE_MAX_REPONSES = 20;
/** Les clés de questions du catalogue sont de simples identifiants (ex. « logement »). */
const MOTIF_CLE = /^[a-z0-9_]{1,40}$/;

export type Validation<T> = { ok: true; valeur: T } | { ok: false; message: string };

function sansCaracteresDeControle(texte: string): string {
  // Conserve les retours à la ligne et tabulations, retire les autres
  // caractères de contrôle (dont l'octet nul).
  return texte.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");
}

export function validerDemande(entree: unknown): Validation<string> {
  if (typeof entree !== "string") {
    return { ok: false, message: "Décrivez votre situation avec un texte." };
  }
  const demande = sansCaracteresDeControle(entree).trim();
  if (demande.length === 0) {
    return { ok: false, message: "Décrivez votre situation avant d'envoyer." };
  }
  if (demande.length < LONGUEUR_MIN_DEMANDE) {
    return {
      ok: false,
      message: "Ajoutez quelques mots : qui est concerné, ce qui s'est passé, depuis quand.",
    };
  }
  if (demande.length > LONGUEUR_MAX_DEMANDE) {
    return {
      ok: false,
      message: `Votre description dépasse ${LONGUEUR_MAX_DEMANDE} caractères. Raccourcissez-la.`,
    };
  }
  return { ok: true, valeur: demande };
}

/**
 * Réponses aux questions de clarification.
 * `null` signifie « je ne sais pas » : le moteur enregistre alors le fait comme
 * manquant (core/conversation.py, `nommer_manquant`) au lieu d'inventer une réponse.
 */
export function validerReponses(entree: unknown): Validation<Record<string, string | null>> {
  if (typeof entree !== "object" || entree === null || Array.isArray(entree)) {
    return { ok: false, message: "Les réponses doivent être envoyées sous forme de liste de champs." };
  }
  const paires = Object.entries(entree as Record<string, unknown>);
  if (paires.length > NOMBRE_MAX_REPONSES) {
    return { ok: false, message: "Trop de réponses envoyées." };
  }
  const propre: Record<string, string | null> = {};
  for (const [cle, valeur] of paires) {
    if (!MOTIF_CLE.test(cle)) {
      return { ok: false, message: "Une réponse porte un identifiant de question invalide." };
    }
    if (valeur === null || valeur === undefined) {
      propre[cle] = null;
      continue;
    }
    if (typeof valeur !== "string") {
      return { ok: false, message: "Chaque réponse doit être un texte." };
    }
    const texte = sansCaracteresDeControle(valeur).trim();
    if (texte.length === 0) {
      propre[cle] = null;
      continue;
    }
    if (texte.length > LONGUEUR_MAX_REPONSE) {
      return {
        ok: false,
        message: `Une réponse dépasse ${LONGUEUR_MAX_REPONSE} caractères. Raccourcissez-la.`,
      };
    }
    propre[cle] = texte;
  }
  return { ok: true, valeur: propre };
}
