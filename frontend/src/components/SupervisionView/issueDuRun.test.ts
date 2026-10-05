import { describe, it, expect } from "vitest";
import { issueDuRun } from "./issueDuRun";
import { INITIAL } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";

function pipelineDone(finalStatus?: string): OrchestratorEvent {
  return {
    type: "pipeline_done",
    agent: null,
    ticket_id: "ticket-001",
    data: finalStatus !== undefined ? { final_status: finalStatus } : {},
    timestamp: "2026-01-01T00:00:00.000Z",
  };
}

function etat(over: Partial<StreamState>): StreamState {
  return { ...INITIAL, ...over };
}

describe("issueDuRun", () => {
  it('renders "en-cours" when runClosed is false', () => {
    expect(issueDuRun(etat({ runClosed: false }))).toBe("en-cours");
  });

  it('renders "en-cours" even when status is "error" but runClosed is false', () => {
    // Un run non clos avec status "error" est encore en cours — pas terminé en erreur.
    expect(issueDuRun(etat({ runClosed: false, status: "error" }))).toBe("en-cours");
  });

  it('renders "erreur" when run is closed and status is "error"', () => {
    expect(issueDuRun(etat({ runClosed: true, status: "error" }))).toBe("erreur");
  });

  it('renders "bloque" when a pipeline_done carries final_status "blocked"', () => {
    expect(
      issueDuRun(etat({ runClosed: true, events: [pipelineDone("blocked")] })),
    ).toBe("bloque");
  });

  it('renders "bloque" for a queue with one done ticket and one blocked ticket', () => {
    // Pour une file, un seul ticket bloqué suffit pour classer le run "bloque".
    expect(
      issueDuRun(
        etat({
          runClosed: true,
          events: [pipelineDone("done"), pipelineDone("blocked")],
        }),
      ),
    ).toBe("bloque");
  });

  it('renders "termine" when all pipeline_done carry "done"', () => {
    expect(
      issueDuRun(etat({ runClosed: true, events: [pipelineDone("done")] })),
    ).toBe("termine");
  });

  it('renders "termine" when all pipeline_done carry "in-review"', () => {
    expect(
      issueDuRun(etat({ runClosed: true, events: [pipelineDone("in-review")] })),
    ).toBe("termine");
  });

  it('renders "termine" when pipeline_done has no final_status (defaults to "done")', () => {
    // streamState.applyEvent applique (?? "done") sur final_status :
    // issueDuRun suit la même règle pour rester cohérent.
    expect(
      issueDuRun(etat({ runClosed: true, events: [pipelineDone()] })),
    ).toBe("termine");
  });

  it('renders "autre" when run is closed but has no pipeline_done events', () => {
    // Chat, run interrompu avant toute sortie de pipeline.
    expect(issueDuRun(etat({ runClosed: true }))).toBe("autre");
  });

  it('renders "autre" when pipeline_done carries an unexpected final_status', () => {
    expect(
      issueDuRun(etat({ runClosed: true, events: [pipelineDone("cancelled")] })),
    ).toBe("autre");
  });
});
