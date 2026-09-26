import { useEffect, useRef } from "react";
import type { Project } from "../types/api";
import { useEtatPersistant } from "./useEtatPersistant";

/**
 * Rouvre le projet où on était — ticket-193.
 *
 * Avec six projets, un rechargement retombait sur aucun projet et coûtait
 * un clic ou deux, plusieurs fois par jour. L'identifiant est mémorisé ; à
 * l'arrivée de la liste, s'il y figure encore et que rien n'est sélectionné,
 * il est sélectionné **une fois**. Un projet supprimé entre-temps ne
 * sélectionne rien, sans erreur — c'est l'état d'avant.
 */
export function useProjetMemorise(
  projets: Project[],
  project: Project | null,
  selectionner: (p: Project) => void,
): { memoriser: (id: string | null) => void } {
  const [memorise, setMemorise] = useEtatPersistant<string | null>(
    "projet",
    null,
    (v): v is string | null => v === null || typeof v === "string",
  );
  const restaure = useRef(false);

  useEffect(() => {
    if (restaure.current || project !== null || projets.length === 0) return;
    restaure.current = true;
    const trouve = projets.find((p) => p.id === memorise);
    if (trouve) selectionner(trouve);
  }, [projets, project, memorise, selectionner]);

  return { memoriser: setMemorise };
}
