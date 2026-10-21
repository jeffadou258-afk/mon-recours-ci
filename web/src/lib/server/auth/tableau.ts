/**
 * Données du tableau de bord d'administration, assemblées CÔTÉ SERVEUR.
 *
 * Règle : on ne transmet au composant que des valeurs non secrètes. Pour une
 * clé ou un secret, seule sa présence est indiquée (« Configurée »), jamais sa
 * valeur ni sa longueur. Une donnée indisponible est dite indisponible.
 */

import type { DonneesTableauDeBord } from "@/components/admin/TableauDeBord";
import { lireConfig, type ConfigServeur } from "../config";
import { obtenirSante, type Dependances } from "../handlers";
import { fichierAudit, lireAudit } from "./audit";
import type { Compte } from "./comptes";
import paquet from "../../../../package.json";

export async function construireTableauDeBord(
  compte: Compte,
  comptes: Compte[],
  comptesIgnores: number,
  env: Record<string, string | undefined> = process.env,
  dep: Dependances = {},
): Promise<DonneesTableauDeBord> {
  let config: ConfigServeur | null = null;
  try {
    config = (dep.config ?? (() => lireConfig(env)))();
  } catch {
    config = null;
  }
  const sante = config ? await obtenirSante({ ...dep, config: () => config! }) : null;
  const demo = env.MONRECOURS_MODE === "demo";

  let hoteMoteur = "Non disponible";
  if (config) {
    try {
      hoteMoteur = new URL(config.urlMoteur).host;
    } catch {
      hoteMoteur = "Non disponible";
    }
  }

  return {
    compte: { email: compte.email, role: compte.role },
    plateforme: {
      mode: demo ? "demonstration" : "reel",
      moteur: config === null ? "non_configure" : sante ? "joignable" : "injoignable",
      langageActif: sante ? sante.langageActif : null,
      versionInterface: typeof paquet.version === "string" ? paquet.version : "Non disponible",
    },
    sante,
    comptes: comptes.map((c) => ({ email: c.email, role: c.role })),
    comptesIgnores,
    audit: await lireAudit(50, env).catch(() => null),
    parametres: [
      { libelle: "Mode", valeur: demo ? "Démonstration (réponses figées)" : "Service réel" },
      { libelle: "Adresse du moteur", valeur: demo ? "Aucune (démonstration)" : hoteMoteur },
      { libelle: "Clé d'accès au moteur", valeur: env.MONRECOURS_API_KEY ? "Configurée" : "Absente" },
      { libelle: "Secret de session", valeur: "Configuré", note: "obligatoire pour ouvrir cette page" },
      {
        libelle: "Délai d'attente du moteur",
        valeur: config ? `${Math.round(config.delaiMs / 1000)} s` : "Non disponible",
      },
      {
        libelle: "Limite par visiteur",
        valeur: config ? `${config.debitVisiteur} demandes par minute` : "Non disponible",
      },
      { libelle: "Tentatives de connexion", valeur: "5 par minute et par visiteur, 5 par minute et par adresse" },
      { libelle: "Durée d'une session d'administration", valeur: "8 heures" },
      { libelle: "Fichier d'audit", valeur: fichierAudit(env) ? "Configuré" : "Non configuré" },
      { libelle: "Comptes configurés", valeur: String(comptes.length) },
    ],
  };
}
