import { useState } from "react";
import type { ProjetPourLaColonne } from "../lib/bureau/aToi";
import { MEMOIRE_VIERGE, ronde } from "../lib/bureau/ronde";
import type { DemandeDeVisite, Visite } from "../lib/bureau/ronde";

/**
 * La visite du directeur, relue à chaque rendu : l'horloge du Bureau est la seule à
 * battre, aucun minuteur n'est ouvert ici. La mémoire se met à jour pendant le rendu
 * (la forme documentée de React pour dériver un état) ; `ronde` rend la même mémoire
 * quand rien ne change, donc la relecture converge au second passage.
 */
export function useRondeDuDirecteur(
  projets: readonly ProjetPourLaColonne[],
  demande: DemandeDeVisite | null,
  maintenant: number,
): Visite | null {
  const [memoire, setMemoire] = useState(MEMOIRE_VIERGE);
  const suivante = ronde(memoire, projets, demande, maintenant);
  if (suivante !== memoire) setMemoire(suivante);
  return suivante.visite;
}
