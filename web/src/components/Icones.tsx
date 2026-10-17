/** Pictogrammes des domaines du droit (traits simples, couleur héritée). */

const TRACES: Record<string, string> = {
  logement_baux_foncier: "M3 10.5 12 3l9 7.5V21h-6v-6H9v6H3z",
  travail: "M3 8h18v12H3z M8 8V5h8v3 M3 13h18",
  famille_mariage_filiation:
    "M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6z M17 11a2.5 2.5 0 1 0 0-5 M3 20c0-3.3 2.7-6 6-6s6 2.7 6 6 M15.5 14.2c3 .3 5.5 2.4 5.5 5.8",
  contrats_dettes_commerce: "M6 3h9l4 4v14H6z M14 3v5h5 M9 12h7 M9 16h7",
  penal_procedure_penale:
    "M12 3v18 M6 21h12 M4 7h16 M7 7l-3 6.5a3 3 0 0 0 6 0z M17 7l-3 6.5a3 3 0 0 0 6 0z",
  consommation: "M3 4h2l2.4 11h11L21 7H6.4 M9 20h.01 M17 20h.01",
  associations_organisations_religieuses: "M4 21V9.5l8-5.5 8 5.5V21 M9.5 21v-5.5h5V21 M12 4V1.5",
  donnees_personnelles_numerique: "M3 4h18v12H3z M8 20h8 M12 16v4 M9 10l2 2 4-4",
  administratif_voies_de_recours: "M3 21h18 M4 10h16 M12 3l9 5H3z M6 10v8 M10 10v8 M14 10v8 M18 10v8",
  transport_responsabilite_civile: "M5 16h14v-4l-2-5H7l-2 5z M5 12h14 M7.5 19.5h.01 M16.5 19.5h.01",
  sante_droits_usagers: "M12 20.5s-8-4.4-8-10.8A4.4 4.4 0 0 1 12 7a4.4 4.4 0 0 1 8 2.7c0 6.4-8 10.8-8 10.8z M12 10v5 M9.5 12.5h5",
};

const DEFAUT = "M12 3v18 M6 21h12 M4 7h16";

export function IconeDomaine({ domaine, taille = 28 }: { domaine: string; taille?: number }) {
  return (
    <svg
      className="icone"
      width={taille}
      height={taille}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.6"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d={TRACES[domaine] ?? DEFAUT} />
    </svg>
  );
}
