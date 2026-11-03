/**
 * L'entrée du fil que `test_result` ajoute (ticket-321). Sortie de `applyEvent`
 * pour le garder sous son plafond de longueur ; pure, comme lui.
 */
import type { OrchestratorEvent } from "../types/api";
import type { EntreeTesteur } from "./streamState";

export function entreeTesteur(ev: OrchestratorEvent, round: number, rang: number): EntreeTesteur {
  const rawErrors = Array.isArray(ev.data["errors"]) ? ev.data["errors"] : [];
  const resume = ev.data["output_summary"];
  return {
    genre: "testeur",
    id: `testeur-${rang}`,
    round,
    passed: ev.data["passed"] === true,
    output_summary: typeof resume === "string" ? resume : "",
    errors: rawErrors.filter((e: unknown): e is string => typeof e === "string"),
    isDone: true,
  };
}
