/**
 * Pastille d'état — ticket-439, charte du 2026-10-14.
 *
 * Fond teinté à 12 % de la famille de l'état, texte clair de la même famille,
 * rayon 4 px, toujours un mot : la couleur seule ne dit rien aux daltoniens.
 */
export type EtatPastille = "en-cours" | "reussi" | "attention" | "echec" | "neutre";

interface StatusPillProps {
  etat: EtatPastille;
  /** Obligatoire : l'état se lit au mot, jamais à la couleur seule. */
  libelle: string;
  /** Infobulle : la cause d'un état, quand on la connaît. */
  titre?: string;
}

const CLASSES: Record<EtatPastille, string> = {
  "en-cours": "bg-blue-500/12 text-blue-300",
  reussi: "bg-green-500/12 text-green-300",
  attention: "bg-amber-500/12 text-amber-300",
  echec: "bg-red-500/12 text-red-300",
  neutre: "bg-zinc-500/12 text-zinc-300",
};

export default function StatusPill({ etat, libelle, titre }: StatusPillProps) {
  return (
    <span
      data-etat={etat}
      title={titre}
      className={`inline-flex items-center rounded px-2 py-0.5 text-mini font-medium ${CLASSES[etat]}`}
    >
      {libelle}
    </span>
  );
}
