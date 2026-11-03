import { describe, expect, it } from "vitest";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import { ecranDuPoste } from "./ecranDuPoste";
import { postesDuRun } from "./postesDuRun";

const HORODATAGE = "2026-10-29T09:00:00.000Z";

function ev(type: EventType, agent: AgentRole | null = null, data: Record<string, unknown> = {}): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: HORODATAGE };
}

function apres(...evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

function outil(agent: AgentRole, nom: string): OrchestratorEvent {
  return ev("agent_tool_use", agent, { tool: nom, input: {} });
}

/** L'écran que la pièce donnerait au poste, l'état du poste étant relu dans les événements. */
function ecran(etat: StreamState, poste: Parameters<typeof ecranDuPoste>[1]): string {
  const etatDuPoste = postesDuRun(etat).find((p) => p.poste === poste)?.etat ?? "libre";
  return ecranDuPoste(etat, poste, etatDuPoste);
}

describe("ecranDuPoste busy posts", () => {
  it("shows code scrolling when the coder writes, whatever the writing tool", () => {
    for (const nom of ["Edit", "Write", "MultiEdit"]) {
      const etat = apres(ev("agent_started", "codeur"), outil("codeur", nom));
      expect(ecran(etat, "codeur"), nom).toBe("code");
    }
  });

  it("shows a still page when the coder reads", () => {
    for (const nom of ["Read", "Grep", "Glob"]) {
      const etat = apres(ev("agent_started", "codeur"), outil("codeur", nom));
      expect(ecran(etat, "codeur"), nom).toBe("lecture");
    }
  });

  it("follows the last tool of the coder", () => {
    const etat = apres(ev("agent_started", "codeur"), outil("codeur", "Edit"), outil("codeur", "Read"));

    expect(ecran(etat, "codeur")).toBe("lecture");
  });

  it("lights the plain screen when the coder has used no tool, or one that says nothing", () => {
    expect(ecran(apres(ev("agent_started", "codeur")), "codeur")).toBe("allume");
    expect(ecran(apres(ev("agent_started", "codeur"), outil("codeur", "Bash")), "codeur")).toBe("allume");
  });

  it("does not read the coder's screen in a tool the reviewer used", () => {
    const etat = apres(ev("agent_started", "codeur"), outil("reviewer", "Edit"));

    expect(ecran(etat, "codeur")).toBe("allume");
  });

  it("reads the architect's tools at the coder's post", () => {
    const etat = apres(ev("agent_started", "architect"), outil("architect", "Write"));

    expect(ecran(etat, "codeur")).toBe("code");
  });

  it("draws a bar for the tester, a scan for security, a diff for the reviewer, a list for the validator", () => {
    expect(ecran(apres(ev("test_started")), "testeur")).toBe("tests");
    expect(ecran(apres(ev("security_audit_started")), "securite")).toBe("audit");
    expect(ecran(apres(ev("agent_started", "reviewer")), "reviewer")).toBe("diff");
    expect(ecran(apres(ev("validation_started")), "validateur")).toBe("criteres");
  });

  it("leaves a free post dark", () => {
    expect(ecran(INITIAL, "codeur")).toBe("eteint");
    expect(ecran(apres(ev("agent_started", "codeur")), "reviewer")).toBe("eteint");
  });
});

describe("ecranDuPoste finished posts", () => {
  it("ticks the coder once it has finished", () => {
    expect(ecran(apres(ev("agent_started", "codeur"), ev("agent_done", "codeur")), "codeur")).toBe("ok");
  });

  it("ticks or crosses the tester after the result of its tests", () => {
    expect(ecran(apres(ev("test_started"), ev("test_result", null, { passed: true })), "testeur")).toBe("ok");
    expect(ecran(apres(ev("test_started"), ev("test_result", null, { passed: false })), "testeur")).toBe("ko");
  });

  it("ticks a PASS of the audit and crosses a BLOCK or an unreadable verdict", () => {
    const rendu = (data: Record<string, unknown>) =>
      ecran(apres(ev("security_audit_started"), ev("security_audit_done", null, data)), "securite");

    expect(rendu({ verdict: "PASS" })).toBe("ok");
    expect(rendu({ verdict: "BLOCK" })).toBe("ko");
    expect(rendu({})).toBe("ko");
  });

  it("ticks an approval of the reviewer and crosses a request for changes", () => {
    const rendu = (verdict: string) =>
      ecran(apres(ev("agent_started", "reviewer"), ev("agent_done", "reviewer", { content: "", verdict })), "reviewer");

    expect(rendu("APPROVED")).toBe("ok");
    expect(rendu("CHANGES_REQUESTED")).toBe("ko");
  });

  it("reads the reviewer's verdict in its text when the event carries none", () => {
    const refus = apres(ev("agent_started", "reviewer"), ev("agent_done", "reviewer", { content: "CHANGES_REQUESTED\n- un test" }));

    expect(ecran(refus, "reviewer")).toBe("ko");
  });

  it("ticks an approved validation and crosses a refused one", () => {
    const rendu = (data: Record<string, unknown>) =>
      ecran(apres(ev("validation_started"), ev("validation_done", null, data)), "validateur");

    expect(rendu({ approved: true, verdict: "APPROVED" })).toBe("ok");
    expect(rendu({ approved: false, verdict: "CHANGES_REQUESTED" })).toBe("ko");
    expect(rendu({ verdict: "APPROVED" })).toBe("ok");
    expect(rendu({})).toBe("ko");
  });

  it("shows the verdict of the latest round", () => {
    const etat = apres(
      ev("test_started"),
      ev("test_result", null, { passed: false }),
      ev("agent_started", "codeur"),
      ev("test_started"),
      ev("test_result", null, { passed: true }),
    );

    expect(ecran(etat, "testeur")).toBe("ok");
  });

  it("does not take the plan turn for the coder's work", () => {
    const etat = apres(ev("agent_started", "codeur", { phase: "plan" }), ev("agent_done", "codeur", { phase: "plan" }));

    expect(ecran(etat, "codeur")).toBe("eteint");
  });
});
