import type { StreamState } from "../../hooks/streamState";
import type { AgentRole } from "../../types/api";
import { phraseDOutil } from "./phraseDOutil";
import type { PosteId } from "./postesDuRun";

/** Combien de temps la bulle reste après le dernier appel d'outil (ticket-601). */
export const DUREE_DE_LA_BULLE_MS = 10_000;

/** Ce que dit la bulle, et au-dessus de quel poste. */
export interface BulleDOutil {
  poste: PosteId;
  phrase: string;
}

/** Le poste d'un agent qui appelle des outils ; les autres rôles n'ont pas de poste dans la pièce. */
function posteDeLAgent(agent: AgentRole | null): PosteId | null {
  if (agent === "codeur" || agent === "architect") return "codeur";
  if (agent === "reviewer") return "reviewer";
  return null;
}

/**
 * La bulle d'outil à dessiner, ou null : elle n'existe que `DUREE_DE_LA_BULLE_MS`
 * après le dernier `agent_tool_use`. L'horloge est celle de la vue — la pièce
 * n'ouvre aucun minuteur — et un horodatage illisible ne montre rien.
 */
export function bulleDOutil(etat: StreamState, maintenant: number): BulleDOutil | null {
  const dernier = etat.dernierOutil;
  if (dernier === null) return null;
  const poste = posteDeLAgent(dernier.agent);
  if (poste === null) return null;
  const ecoule = maintenant - Date.parse(dernier.horodatage);
  if (!(ecoule >= 0 && ecoule < DUREE_DE_LA_BULLE_MS)) return null;
  return { poste, phrase: phraseDOutil(dernier.outil, dernier.entree) };
}
