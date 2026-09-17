import { describe, it, expect, beforeAll } from "vitest";
import { render, screen } from "@testing-library/react";
import BottomPanel from "./index";
import type { OrchestratorEvent } from "../../types/api";

beforeAll(() => {
  window.HTMLElement.prototype.scrollIntoView = () => {};
});

function makeEvent(
  type: OrchestratorEvent["type"],
  data: Record<string, unknown> = {},
  extra: Partial<OrchestratorEvent> = {},
): OrchestratorEvent {
  return {
    type,
    timestamp: "2026-07-13T10:00:00Z",
    data,
    ...extra,
  } as OrchestratorEvent;
}

describe("BottomPanel", () => {
  it("renders empty state when no events", () => {
    render(<BottomPanel events={[]} />);
    expect(screen.getByText(/en attente/i)).toBeTruthy();
  });

  it("renders ticket_status_changed event", () => {
    const ev = makeEvent(
      "ticket_status_changed",
      { status: "in-progress" },
      {
        ticket_id: "ticket-001",
      },
    );
    render(<BottomPanel events={[ev]} />);
    expect(screen.getByText(/ticket-001/)).toBeTruthy();
    expect(screen.getByText(/in-progress/)).toBeTruthy();
  });

  it("renders agent_started event", () => {
    const ev = makeEvent("agent_started", { round: 2 }, { agent: "codeur" });
    render(<BottomPanel events={[ev]} />);
    expect(screen.getByText(/codeur/)).toBeTruthy();
    expect(screen.getByText(/tour 2/)).toBeTruthy();
  });

  it("renders agent_done event", () => {
    const ev = makeEvent("agent_done", {}, { agent: "reviewer" });
    render(<BottomPanel events={[ev]} />);
    expect(screen.getByText(/reviewer.*terminé/)).toBeTruthy();
  });

  it("renders pipeline_done approved", () => {
    const ev = makeEvent("pipeline_done", {
      approved: true,
      final_status: "done",
    });
    render(<BottomPanel events={[ev]} />);
    expect(screen.getByText(/APPROVED/)).toBeTruthy();
    expect(screen.getByText(/done/)).toBeTruthy();
  });

  it("renders pipeline_done changes requested", () => {
    const ev = makeEvent("pipeline_done", {
      approved: false,
      final_status: "todo",
    });
    render(<BottomPanel events={[ev]} />);
    expect(screen.getByText(/CHANGES_REQUESTED/)).toBeTruthy();
  });

  it("montre la raison d'un refus, pas « unknown »", () => {
    // Panne vecue le 2026-09-17 : le backend emettait
    // `reason="dirty_working_tree"`, le formateur lisait `message`, et
    // l'utilisateur a vu « Erreur: unknown » pendant dix minutes alors que la
    // raison exacte etait dans l'evenement.
    const ev = makeEvent("error", { reason: "dirty_working_tree" });
    render(<BottomPanel events={[ev]} />);
    expect(screen.getByText(/arbre de travail/i)).toBeTruthy();
  });

  it("montre une raison inconnue telle quelle plutot que de l'effacer", () => {
    const ev = makeEvent("error", { reason: "quelque_chose_de_nouveau" });
    render(<BottomPanel events={[ev]} />);
    expect(screen.getByText(/quelque_chose_de_nouveau/)).toBeTruthy();
  });

  it("renders error event", () => {
    const ev = makeEvent("error", { message: "Something went wrong" });
    render(<BottomPanel events={[ev]} />);
    expect(screen.getByText(/Something went wrong/)).toBeTruthy();
  });

  it("filters out unknown event types", () => {
    // Unknown types return null from eventToLine and should not render a line
    const ev = makeEvent("unknown_type" as OrchestratorEvent["type"], {});
    render(<BottomPanel events={[ev]} />);
    // Should show empty state since no lines rendered
    expect(screen.getByText(/en attente/i)).toBeTruthy();
  });

  it("renders multiple events in order", () => {
    const events = [
      makeEvent("agent_started", { round: 1 }, { agent: "codeur" }),
      makeEvent("agent_done", {}, { agent: "codeur" }),
    ];
    render(<BottomPanel events={events} />);
    expect(screen.getByText(/codeur.*démarré/)).toBeTruthy();
    expect(screen.getByText(/codeur.*terminé/)).toBeTruthy();
  });

  it("handles agent_started with missing agent and round", () => {
    const ev = makeEvent("agent_started", {});
    render(<BottomPanel events={[ev]} />);
    expect(screen.getByText(/\?.*démarré.*tour \?/)).toBeTruthy();
  });
});
