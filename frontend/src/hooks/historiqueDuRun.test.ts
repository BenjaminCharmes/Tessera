import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../lib/api";
import type { OrchestratorEvent, RunEvent } from "../types/api";
import { rejouerHistorique } from "./historiqueDuRun";
import { runStore } from "./runStore";

const RUN = "run-historique";

function persiste(horodatage: string): RunEvent {
  return {
    type: "agent_started",
    agent: "codeur",
    data: {},
    timestamp: horodatage,
  } as unknown as RunEvent;
}

function direct(type: OrchestratorEvent["type"], horodatage: string): OrchestratorEvent {
  return { type, agent: "codeur", ticket_id: "", data: {}, timestamp: horodatage, run_id: RUN };
}

afterEach(() => {
  vi.restoreAllMocks();
  runStore.reset();
});

describe("rejouerHistorique", () => {
  it("replays the persisted events into the store", async () => {
    vi.spyOn(api.runs, "events").mockResolvedValue([persiste("2026-10-27T10:00:00.000Z")]);

    await rejouerHistorique(RUN, "db-1", () => []);

    expect(runStore.getSnapshot()[RUN]?.etape).toBe("production");
  });

  it("adds the buffered events newer than the history and drops the older ones", async () => {
    vi.spyOn(api.runs, "events").mockResolvedValue([persiste("2026-10-27T10:00:00.000Z")]);
    const tampon = [direct("run_closed", "2026-10-27T09:59:00.000Z")];

    await rejouerHistorique(RUN, "db-1", () => tampon);
    expect(runStore.getSnapshot()[RUN]?.runClosed).toBe(false);

    tampon.push(direct("run_closed", "2026-10-27T10:00:05.000Z"));
    await rejouerHistorique(RUN, "db-1", () => tampon);
    expect(runStore.getSnapshot()[RUN]?.runClosed).toBe(true);
  });

  it("falls back to the buffer when the history is unavailable", async () => {
    vi.spyOn(api.runs, "events").mockRejectedValue(new Error("hors ligne"));

    await rejouerHistorique(RUN, "db-1", () => [direct("run_closed", "2026-10-27T10:00:05.000Z")]);

    expect(runStore.getSnapshot()[RUN]?.runClosed).toBe(true);
  });
});
