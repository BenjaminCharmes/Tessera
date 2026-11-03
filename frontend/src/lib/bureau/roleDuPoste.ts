import type { StreamState } from "../../hooks/streamState";
import { POSTES } from "./postesDuRun";
import type { PosteId, RoleAffiche } from "./postesDuRun";

/**
 * Le rôle que le poste montre. Seul le poste du codeur peut changer : il se lit
 * « Architecte » tant que le dernier `agent_started` du poste vient de l'architecte,
 * « Codeur » sinon — y compris avant tout événement.
 */
export function roleDuPoste(etat: StreamState, poste: PosteId): RoleAffiche {
  if (poste !== "codeur") return poste;
  const dernier = etat.ticketEvents.findLast(
    (ev) => ev.type === "agent_started" && (ev.agent === "codeur" || ev.agent === "architect"),
  );
  return dernier?.agent === "architect" ? "architect" : "codeur";
}

/** Le rôle affiché de chacun des cinq postes. */
export function rolesDesPostes(etat: StreamState): Record<PosteId, RoleAffiche> {
  const roles = {} as Record<PosteId, RoleAffiche>;
  for (const poste of POSTES) roles[poste] = roleDuPoste(etat, poste);
  return roles;
}
