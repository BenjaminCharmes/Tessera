import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, OrchestratorEvent } from "../../types/api";
import { DUREE_DE_LA_BULLE_MS, bulleDOutil } from "./bulleDOutil";

const DEPART = "2026-10-27T09:00:00.000Z";
const T0 = Date.parse(DEPART);

function outil(agent: AgentRole | null, data: Record<string, unknown>, timestamp = DEPART): OrchestratorEvent {
  return { type: "agent_tool_use", agent, ticket_id: "ticket-001", data, timestamp };
}

function apres(...evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const LECTURE = { tool: "Read", input: { file_path: "C:\\Users\\jdupont\\ide-core\\conflits.py" } };

describe("StreamState.dernierOutil", () => {
  it("keeps the last tool use with its input and timestamp", () => {
    const etat = apres(outil("codeur", LECTURE), outil("codeur", { tool: "Bash", input: { command: "uv run pytest" } }, "2026-10-27T09:00:04.000Z"));

    expect(etat.dernierOutil).toEqual({
      agent: "codeur",
      outil: "Bash",
      entree: { command: "uv run pytest" },
      horodatage: "2026-10-27T09:00:04.000Z",
    });
  });

  it("ignores an event that names no tool, and keeps the previous one", () => {
    const etat = apres(outil("codeur", LECTURE), outil("codeur", {}));

    expect(etat.dernierOutil?.outil).toBe("Read");
  });

  it("counts the tool uses as before", () => {
    expect(apres(outil("codeur", LECTURE), outil("codeur", {})).outils).toBe(2);
  });
});

describe("bulleDOutil", () => {
  it("says nothing before any tool use", () => {
    expect(bulleDOutil(INITIAL, T0)).toBeNull();
  });

  it("puts the phrase on the coder's desk for 10 s", () => {
    const etat = apres(outil("codeur", LECTURE));

    expect(bulleDOutil(etat, T0)).toEqual({ poste: "codeur", phrase: "lit conflits.py" });
    expect(bulleDOutil(etat, T0 + DUREE_DE_LA_BULLE_MS - 1)?.phrase).toBe("lit conflits.py");
    expect(bulleDOutil(etat, T0 + DUREE_DE_LA_BULLE_MS)).toBeNull();
  });

  it("puts the architect's tools on the coder's desk and the reviewer's on its own", () => {
    expect(bulleDOutil(apres(outil("architect", LECTURE)), T0)?.poste).toBe("codeur");
    expect(bulleDOutil(apres(outil("reviewer", LECTURE)), T0)?.poste).toBe("reviewer");
  });

  it("has no desk for a role that sits at none", () => {
    expect(bulleDOutil(apres(outil("github-sync", LECTURE)), T0)).toBeNull();
    expect(bulleDOutil(apres(outil(null, LECTURE)), T0)).toBeNull();
  });

  it("shows nothing for an unreadable timestamp or a clock before the event", () => {
    expect(bulleDOutil(apres(outil("codeur", LECTURE, "pas une date")), T0)).toBeNull();
    expect(bulleDOutil(apres(outil("codeur", LECTURE)), T0 - 1)).toBeNull();
  });
});
