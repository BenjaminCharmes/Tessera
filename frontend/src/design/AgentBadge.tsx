/**
 * Le badge « d'où vient cet agent » — ticket-079.
 *
 * Il existait en deux exemplaires : `built-in` / `custom`, en anglais et
 * colorés dans la liste ; `natif` / `personnalisé`, en français et sans
 * couleur dans l'en-tête. Le même fait, dit de deux façons, à deux endroits
 * visibles en même temps.
 *
 * Le vocabulaire d'une interface est le balisage de celui qui s'y repère : un
 * mot par chose, et le même partout.
 */
interface AgentBadgeProps {
  natif: boolean;
}

export default function AgentBadge({ natif }: AgentBadgeProps) {
  return (
    <span
      title={
        natif
          ? "Livré avec vibe-ide. Son prompt fait partie du produit : il peut être ajusté, pas supprimé."
          : "Créé depuis l'IDE. Tu peux l'ajuster et le supprimer."
      }
      className={`shrink-0 rounded px-1.5 py-0.5 text-micro font-medium ${
        natif
          ? "bg-blue-900 text-blue-300"
          : "bg-violet-500/20 text-violet-200"
      }`}
    >
      {natif ? "natif" : "perso"}
    </span>
  );
}
