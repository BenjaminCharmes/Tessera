import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, it, expect } from "vitest";
import { applyEvent, INITIAL } from "./streamState";
import type { StreamState } from "./streamState";
import type { OrchestratorEvent } from "../types/api";

// La fixture a été calculée avec le réducteur d'avant le découpage par famille
// (ticket-695) : tout écart d'état final est une régression du découpage.
interface Fixture {
  evenements: OrchestratorEvent[];
  etatApresLePremierTicket: StreamState;
  etatFinal: StreamState;
}

const fixture = JSON.parse(
  readFileSync(join(__dirname, "fixtures", "rejeu.json"), "utf-8"),
) as Fixture;

function rejouer(evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

describe("replay of a recorded event sequence", () => {
  it("covers every family of events", () => {
    const types = new Set(fixture.evenements.map((e) => e.type));
    for (const type of [
      "agent_started", "agent_token", "agent_done", "agent_tool_use", "test_started",
      "test_result", "security_audit_done", "validation_done", "agent_question",
      "answer_ack", "queue_progress", "external_wait", "conflict_resolution",
      "provider_fallback", "pipeline_done", "livraison_done", "ci_merge_done",
      "run_closed", "quota_updated", "error",
    ]) {
      expect(types.has(type as OrchestratorEvent["type"])).toBe(true);
    }
  });

  it("reaches the recorded state at the end of the first ticket", () => {
    expect(rejouer(fixture.evenements.slice(0, 31))).toEqual(fixture.etatApresLePremierTicket);
  });

  it("reaches the recorded final state", () => {
    expect(rejouer(fixture.evenements)).toEqual(fixture.etatFinal);
  });

  it("gives the same state when the sequence is replayed twice", () => {
    expect(rejouer(fixture.evenements)).toEqual(rejouer(fixture.evenements));
  });
});
