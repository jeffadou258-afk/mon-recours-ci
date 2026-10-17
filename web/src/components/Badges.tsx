import { presentationVerification } from "@/lib/libelles";

interface Props {
  etat: string;
  origine?: string | null;
  recoupe?: boolean;
  /** Affiche aussi l'explication sous le badge. */
  detaille?: boolean;
}

/** Badge d'état de vérification. Jamais « vérifié » si le moteur ne le dit pas. */
export function BadgeVerification({ etat, origine = null, recoupe = false, detaille = false }: Props) {
  const p = presentationVerification(etat, origine, recoupe);
  return (
    <span className={`badge badge--${p.niveau}`} data-niveau={p.niveau}>
      <span className="badge__pastille" aria-hidden="true" />
      <span>{p.libelle}</span>
      {detaille ? <span className="badge__detail">{p.detail}</span> : null}
    </span>
  );
}
