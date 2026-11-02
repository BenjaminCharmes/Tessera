import { useState } from "react";
import type { CockpitNoyau } from "./useCockpitNoyau";

/**
 * Région du panneau d'agent — ticket-696 : l'agent regardé dans la colonne
 * latérale est celui que le centre détaille.
 */
export function useCockpitAgent(n: CockpitNoyau) {
  const [selectionne, setSelectionne] = useState<string | null>(null);
  return {
    selectionne,
    onSelect: setSelectionne,
    onCreated: (role: string) => n.addToast(`Agent \`${role}\` créé`, "success"),
  };
}

export type CockpitAgent = ReturnType<typeof useCockpitAgent>;
