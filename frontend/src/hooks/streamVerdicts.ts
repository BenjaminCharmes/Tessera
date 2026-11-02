/**
 * Famille « verdicts » du réducteur de `streamState.ts` (ticket-695) : les
 * événements qui ajoutent une entrée au fil — tests, audit sécurité, validation.
 * Chaque fonction de famille rend le morceau d'état à fusionner, ou null quand
 * l'événement n'en est pas.
 */
import type { OrchestratorEvent } from "../types/api";
import type { EntreeSecurite, EntreeValidateur } from "./streamEntrees";
import { removeEtapeEnCours } from "./streamEtapes";
import { entreeTesteur } from "./streamTests";
import type { StreamState } from "./streamState";

function texte(data: Record<string, unknown>, cle: string): string {
  const v = data[cle];
  return typeof v === "string" ? v : "";
}

/** L'audit ajoute une entrée dans le fil, visible à côté des agents (ticket-257). */
function appliquerAudit(s: StreamState, ev: OrchestratorEvent): Partial<StreamState> {
  const compte = ev.data["issues_count"];
  const entree: EntreeSecurite = {
    genre: "securite",
    id: `securite-${s.entries.length}`,
    round: s.currentRound,
    verdict: texte(ev.data, "verdict"),
    summary: texte(ev.data, "summary"),
    issues_count: typeof compte === "number" ? compte : 0,
    reason: texte(ev.data, "reason"),
    isDone: true,
  };
  return {
    entries: [...s.entries, entree],
    etapesEnCours: removeEtapeEnCours(s.etapesEnCours, "securite"),
  };
}

/** La validation ajoute une entrée dans le fil, critère par critère (ticket-257). */
function appliquerValidation(s: StreamState, ev: OrchestratorEvent): Partial<StreamState> {
  const brut = Array.isArray(ev.data["criteria"]) ? ev.data["criteria"] : [];
  const criteria = brut.map((c: unknown) => {
    const cr = c as Record<string, unknown>;
    return { criterion: texte(cr, "criterion"), passed: cr["passed"] === true, note: texte(cr, "note") };
  });
  const entree: EntreeValidateur = {
    genre: "validateur",
    id: `validateur-${s.entries.length}`,
    round: s.currentRound,
    verdict: texte(ev.data, "verdict"),
    feedback: texte(ev.data, "feedback"),
    criteria,
    isDone: true,
  };
  return {
    entries: [...s.entries, entree],
    etapesEnCours: removeEtapeEnCours(s.etapesEnCours, "validation"),
  };
}

/** Les événements qui rendent un verdict : `test_result`, audit, validation. */
export function appliquerVerdict(
  s: StreamState,
  ev: OrchestratorEvent,
): Partial<StreamState> | null {
  switch (ev.type) {
    case "test_result":
      return {
        entries: [...s.entries, entreeTesteur(ev, s.currentRound, s.entries.length)],
        etapesEnCours: removeEtapeEnCours(s.etapesEnCours, "tests"),
      };
    case "security_audit_done":
      return appliquerAudit(s, ev);
    case "validation_done":
      return appliquerValidation(s, ev);
    default:
      return null;
  }
}
