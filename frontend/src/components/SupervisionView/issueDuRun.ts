import type { StreamState } from "../../hooks/streamState";

export type IssueDuRun = "en-cours" | "termine" | "bloque" | "erreur" | "autre";

/**
 * The outcome category of a run based on its accumulated state (ticket-344).
 *
 * Rules:
 * - "en-cours" as long as runClosed is false, regardless of other state;
 * - "erreur" if the run is closed and status is "error";
 * - "bloque" if any pipeline_done event has final_status "blocked"
 *   (a single blocked ticket in a queue suffices);
 * - "termine" if at least one pipeline_done exists and all carry
 *   final_status "done" or "in-review" (a missing final_status defaults
 *   to "done", matching the behaviour of streamState.applyEvent);
 * - "autre" otherwise (chat, run closed without pipeline_done, etc.).
 */
export function issueDuRun(etat: StreamState): IssueDuRun {
  if (!etat.runClosed) return "en-cours";
  if (etat.status === "error") return "erreur";

  const pipelineDones = etat.events.filter((ev) => ev.type === "pipeline_done");
  if (pipelineDones.length === 0) return "autre";

  const hasBlocked = pipelineDones.some(
    (ev) => (ev.data["final_status"] ?? "done") === "blocked",
  );
  if (hasBlocked) return "bloque";

  const allTermine = pipelineDones.every((ev) => {
    const fs = ev.data["final_status"] ?? "done";
    return fs === "done" || fs === "in-review";
  });
  return allTermine ? "termine" : "autre";
}
