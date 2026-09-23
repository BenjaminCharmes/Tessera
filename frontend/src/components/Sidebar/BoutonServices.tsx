import type { UseServicesResult } from "../../hooks/useServices";

/**
 * Lancer ou arrêter les services d'un projet — ticket-138.
 *
 * Rien n'apparaît quand le projet ne déclare aucun `services` : un bouton
 * désactivé sans explication fait chercher une panne qui n'existe pas, et
 * ADR-042 pose que ne rien déclarer *est* la réponse « ce projet ne se lance
 * pas depuis l'IDE ».
 *
 * ADR-026 : `blue` pour l'activité, `red` pour un service mort de lui-même,
 * `zinc` au repos.
 */
export default function BoutonServices({
  services,
  libelleDuProjet,
}: {
  services: UseServicesResult;
  libelleDuProjet: string;
}) {
  if (!services.declare) return null;

  const { enCours, enEchec, erreur } = services;
  const classe = enEchec
    ? "bg-red-500/20 text-red-200 hover:bg-red-500/30"
    : enCours
      ? "bg-blue-500/20 text-blue-200 hover:bg-blue-500/30"
      : "bg-zinc-800 text-zinc-300 hover:bg-zinc-700";

  return (
    <button
      type="button"
      onClick={() => void (enCours ? services.arreter() : services.demarrer())}
      title={erreur ?? undefined}
      aria-label={
        enCours
          ? `Arrêter les services de ${libelleDuProjet}`
          : `Lancer les services de ${libelleDuProjet}`
      }
      className={`shrink-0 rounded-sm px-2 py-0.5 text-micro font-medium transition-colors ${classe}`}
    >
      {enCours ? "Arrêter" : enEchec ? "Relancer" : "Lancer"}
    </button>
  );
}
