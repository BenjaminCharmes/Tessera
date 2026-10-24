import { describe, it, expect } from "vitest";
import { INITIAL } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";
import { contourDeLaPiece } from "./contourDeLaPiece";

function pipelineDone(finalStatus: string): OrchestratorEvent {
  return {
    type: "pipeline_done",
    agent: null,
    ticket_id: "ticket-001",
    data: { final_status: finalStatus },
    timestamp: "2026-01-01T00:00:00.000Z",
  };
}

function etat(over: Partial<StreamState>): StreamState {
  return { ...INITIAL, ...over };
}

const clos = (over: Partial<StreamState>): StreamState => etat({ runClosed: true, ...over });

describe("contourDeLaPiece", () => {
  it("is green for a finished run", () => {
    expect(contourDeLaPiece(clos({ events: [pipelineDone("done")] }), "actif")).toBe("vert");
  });

  it("is red for a blocked run", () => {
    expect(contourDeLaPiece(clos({ events: [pipelineDone("blocked")] }), "actif")).toBe("rouge");
  });

  it("is red for a run closed in error", () => {
    expect(contourDeLaPiece(clos({ status: "error" }), "actif")).toBe("rouge");
  });

  it("is red for a live run suspected of being stalled", () => {
    expect(contourDeLaPiece(etat({}), "blocage_suspecte")).toBe("rouge");
  });

  it("is amber for a live run waiting on a question", () => {
    expect(contourDeLaPiece(etat({ pendingQuestion: "Which one?" }), "question")).toBe("amber");
  });

  it("is neutral for a live run that works or is merely quiet", () => {
    expect(contourDeLaPiece(etat({}), "actif")).toBe("neutre");
    expect(contourDeLaPiece(etat({}), "attente")).toBe("neutre");
  });

  it("judges a closed run by its outcome alone, not by the age of its last event", () => {
    // Le dernier événement d'un run clos est toujours « vieux » : la santé le dirait figé.
    expect(contourDeLaPiece(clos({ events: [pipelineDone("done")] }), "blocage_suspecte")).toBe(
      "vert",
    );
  });

  it("is neutral for a run closed without a verdict", () => {
    expect(contourDeLaPiece(clos({}), "blocage_suspecte")).toBe("neutre");
  });
});
