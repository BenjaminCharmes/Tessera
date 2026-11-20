import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import FilDuRun from "./index";
import { applyEvent, INITIAL, type EntreeAnomalie, type StreamState } from "../../hooks/streamState";
import type { OrchestratorEvent } from "../../types/api";

function entree(over: Partial<EntreeAnomalie> = {}): EntreeAnomalie {
  return {
    genre: "anomalie", id: "anomalie-0", cle: "silence:1", regle: "silence",
    message: "Aucun événement depuis 15 min sur ce run.", isDone: true, ...over,
  };
}

function evenement(data: Record<string, unknown>): OrchestratorEvent {
  return { type: "run_anomaly", agent: null, ticket_id: "ticket-004", data, timestamp: "2026-11-05T12:00:00Z" };
}

const ANOMALIE = {
  regle: "silence", cle: "silence:1", ticket_id: "ticket-004",
  message: "Aucun événement depuis 15 min sur ce run.", mesure: 900, seuil: 900, unite: "s",
};

describe("FilDuRun — anomalie (ticket-840)", () => {
  it("test_fil_du_run_renders_a_run_anomaly_line_with_rule_and_message", () => {
    render(<FilDuRun entries={[entree()]} />);

    const ligne = screen.getByTestId("entree-anomalie");
    expect(ligne).toHaveTextContent("silence prolongé");
    expect(ligne).toHaveTextContent("Aucun événement depuis 15 min sur ce run.");
  });

  it("test_fil_du_run_ignores_a_run_anomaly_without_a_known_rule_label_gracefully", () => {
    render(<FilDuRun entries={[entree({ regle: "regle_future" })]} />);

    expect(screen.getByTestId("entree-anomalie")).toHaveTextContent("regle_future");
  });

  it("test_run_anomaly_text_uses_amber_never_violet", () => {
    const { container } = render(<FilDuRun entries={[entree()]} />);

    const classes = Array.from(container.querySelectorAll("[class]")).map((e) => e.getAttribute("class") ?? "");
    expect(classes.some((c) => c.includes("text-amber-"))).toBe(true);
    expect(classes.some((c) => /text-violet/.test(c))).toBe(false);
  });
});

describe("applyEvent — run_anomaly (ticket-840)", () => {
  const base: StreamState = { ...INITIAL, status: "running" };

  it("adds one entry to the thread, carrying the rule and the message", () => {
    const apres = applyEvent(base, evenement(ANOMALIE));

    expect(apres.entries).toEqual([
      { genre: "anomalie", id: "anomalie-0", cle: "silence:1", regle: "silence",
        message: "Aucun événement depuis 15 min sur ce run.", isDone: true },
    ]);
  });

  it("shows an episode replayed by a reconnection only once", () => {
    const une = applyEvent(base, evenement(ANOMALIE));
    const deux = applyEvent(une, evenement(ANOMALIE));

    expect(deux.entries).toHaveLength(1);
  });

  it("does not break the silence it reports: the last-event time stays", () => {
    const vu = { ...base, dernierEvenementA: "2026-11-05T11:40:00Z" };

    expect(applyEvent(vu, evenement(ANOMALIE)).dernierEvenementA).toBe("2026-11-05T11:40:00Z");
  });
});
