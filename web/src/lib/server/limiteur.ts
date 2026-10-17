/**
 * Limite de demandes PAR VISITEUR, en mémoire (un seul serveur).
 *
 * Le moteur limite le débit par clé d'API ; toute l'interface partage cette
 * clé, donc sa limite est globale. Ce limiteur empêche un seul visiteur de la
 * consommer pour tout le monde. Il ne remplace pas une protection anti-DDoS
 * (pare-feu, proxy inverse) : c'est un garde-fou applicatif.
 *
 * Identification : l'adresse ajoutée par le proxy le plus proche, c'est-à-dire
 * la DERNIÈRE valeur de `X-Forwarded-For` (les précédentes sont fournies par le
 * client et donc falsifiables), sinon `X-Real-IP`. Aucune adresse n'est
 * journalisée ni conservée au-delà de la fenêtre.
 */

const FENETRE_MS = 60_000;
const TAILLE_MAX = 10_000;

export class LimiteurVisiteurs {
  private historique = new Map<string, number[]>();

  constructor(private readonly horloge: () => number = Date.now) {}

  /** Retourne 0 si la demande est acceptée, sinon l'attente en secondes. */
  consommer(cle: string, maximum: number): number {
    const maintenant = this.horloge();
    const recents = (this.historique.get(cle) ?? []).filter((t) => maintenant - t < FENETRE_MS);
    if (recents.length >= maximum) {
      this.historique.set(cle, recents);
      return Math.max(1, Math.ceil((FENETRE_MS - (maintenant - recents[0]!)) / 1000));
    }
    recents.push(maintenant);
    this.historique.set(cle, recents);
    if (this.historique.size > TAILLE_MAX) this.nettoyer(maintenant);
    return 0;
  }

  private nettoyer(maintenant: number): void {
    for (const [cle, horodatages] of this.historique) {
      if (!horodatages.some((t) => maintenant - t < FENETRE_MS)) this.historique.delete(cle);
    }
  }
}

export function identifiantVisiteur(requete: Request): string {
  const transmis = requete.headers.get("x-forwarded-for");
  if (transmis) {
    const valeurs = transmis.split(",").map((v) => v.trim()).filter(Boolean);
    const derniere = valeurs[valeurs.length - 1];
    if (derniere) return derniere;
  }
  return requete.headers.get("x-real-ip")?.trim() || "inconnu";
}

export const limiteurParDefaut = new LimiteurVisiteurs();
