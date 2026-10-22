import type { ErreurApi } from "@/lib/types";

const TITRES: Partial<Record<ErreurApi["code"], string>> = {
  RESEAU: "Pas de connexion",
  SERVICE_INDISPONIBLE: "Service momentanément indisponible",
  DEBIT_DEPASSE: "Trop de demandes en même temps",
  SESSION_ABSENTE: "Consultation expirée",
  DOSSIER_INCONNU: "Consultation introuvable",
  CONSULTATION_EXPIREE: "Consultation expirée et supprimée",
  ENTREE_INVALIDE: "Votre texte doit être corrigé",
  CONFIGURATION: "Service indisponible",
  CATALOGUE_INVALIDE: "Service suspendu par sécurité",
};

interface Props {
  erreur: ErreurApi;
  onReessayer?: () => void;
  onRecommencer?: () => void;
}

export function MessageErreur({ erreur, onReessayer, onRecommencer }: Props) {
  const recommencer =
    erreur.code === "SESSION_ABSENTE" || erreur.code === "DOSSIER_INCONNU" || erreur.code === "CONSULTATION_EXPIREE";
  return (
    <div className="erreur" role="alert" data-code={erreur.code}>
      <p className="erreur__titre">{TITRES[erreur.code] ?? "La demande n'a pas abouti"}</p>
      <p>{erreur.message}</p>
      {erreur.reessayerDansSecondes ? (
        <p className="erreur__detail">Patientez environ {erreur.reessayerDansSecondes} secondes.</p>
      ) : null}
      <div className="actions">
        {erreur.reessayable && onReessayer ? (
          <button type="button" className="bouton bouton--secondaire" onClick={onReessayer}>
            Réessayer
          </button>
        ) : null}
        {recommencer && onRecommencer ? (
          <button type="button" className="bouton bouton--secondaire" onClick={onRecommencer}>
            Recommencer
          </button>
        ) : null}
      </div>
    </div>
  );
}

export function Chargement({ message }: { message: string }) {
  return (
    <div className="chargement" role="status" aria-live="polite">
      <span className="chargement__barre" aria-hidden="true" />
      <p>{message}</p>
    </div>
  );
}
