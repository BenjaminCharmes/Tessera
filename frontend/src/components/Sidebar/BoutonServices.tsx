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
  // Mêmes tailles et même bordure que « VSCode » et « Git », dans une rangée
  // où l'alignement est ce qui se voit en premier (ticket-145). Seules les
  // couleurs changent, et elles restent dans les cinq familles d'état
  // d'ADR-026 : le violet est réservé à l'identité, jamais à un état.
  const classe = enEchec
    ? "border-red-500/40 bg-red-500/15 text-red-200 hover:border-red-500/60"
    : enCours
      ? "border-blue-500/40 bg-blue-500/15 text-blue-200 hover:border-blue-500/60"
      : "border-zinc-700 text-zinc-300 hover:border-zinc-500 hover:text-zinc-100";

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
      className={`shrink-0 whitespace-nowrap rounded border px-2 py-1 text-mini transition-colors ${classe}`}
    >
      {enCours ? "Arrêter" : enEchec ? "Relancer" : "Lancer"}
    </button>
  );
}
