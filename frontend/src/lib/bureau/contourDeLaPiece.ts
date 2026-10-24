import type { StreamState } from "../../hooks/streamState";
import { issueDuRun } from "../../components/SupervisionView/issueDuRun";
import type { SanteAgent } from "../santeAgent";

export type ContourDeLaPiece = "neutre" | "vert" | "rouge" | "amber";

/**
 * Le contour d'une pièce, d'après l'issue du run et la santé de son agent.
 *
 * Un run clos se juge sur son issue seule : son dernier événement est vieux de
 * toujours, et la santé le lirait « figé » à tort. Un run en cours se juge sur
 * la santé : une question attend l'humain (`amber`), un blocage suspecté est
 * rouge, le reste ne dit rien (`neutre`).
 */
export function contourDeLaPiece(etat: StreamState, sante: SanteAgent): ContourDeLaPiece {
  const issue = issueDuRun(etat);
  if (issue === "termine") return "vert";
  if (issue === "bloque" || issue === "erreur") return "rouge";
  if (issue === "autre") return "neutre";
  if (sante === "question") return "amber";
  if (sante === "blocage_suspecte") return "rouge";
  return "neutre";
}
