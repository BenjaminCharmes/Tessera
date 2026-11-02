import { eventsAffichiesFor } from "./regles";
import type { CockpitNoyau } from "./useCockpitNoyau";

/**
 * Région du panneau du bas — ticket-696 : les événements du Pipeline log et
 * le projet du run affiché quand il diffère du projet actif.
 */
export function useCockpitBottomPanel(n: CockpitNoyau) {
  const { supervision, stream, projets } = n;
  // Le run sélectionné dans la Supervision, ou null si rien n'est choisi.
  const runSel = supervision.selection
    ? (supervision.runs.find((r) => r.run_id === supervision.selection) ?? null)
    : null;
  return {
    events: eventsAffichiesFor(
      supervision.selection,
      supervision.runs,
      supervision.etatDe,
      stream.events,
    ),
    // Le projet du run affiché, quand il diffère du projet actif — ticket-283.
    projetLabel: runSel
      ? (projets.find((p) => p.id === runSel.project_id)?.name ?? runSel.project_id)
      : null,
  };
}
