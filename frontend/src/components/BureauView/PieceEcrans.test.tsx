import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import { api } from "../../lib/api";
import { SEUIL_ATTENTE_MS } from "../../lib/santeAgent";
import type { AgentRole, EventType, OrchestratorEvent } from "../../types/api";
import Piece from "./Piece";
import { DERNIER, T0 } from "./etatsDeTest";

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function ev(type: EventType, agent: AgentRole | null = null, data: Record<string, unknown> = {}): OrchestratorEvent {
  return { type, agent, ticket_id: "ticket-001", data, timestamp: DERNIER };
}

function etatApres(...evenements: OrchestratorEvent[]): StreamState {
  return evenements.reduce(applyEvent, INITIAL);
}

const CODEUR_FINI = [ev("agent_started", "codeur"), ev("agent_done", "codeur")];

/** Les écrans des cinq postes, dans l'ordre du pipeline. */
function ecrans(etat: StreamState, maintenant = T0 + 1_000): Element[] {
  const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={maintenant} />);
  return [...container.querySelectorAll('[data-sprite="poste"] [data-sprite="ecran"]')];
}

function noms(liste: Element[]): (string | null)[] {
  return liste.map((e) => e.getAttribute("data-ecran"));
}

function anime(ecran: Element | undefined): boolean {
  return ecran?.querySelector('[class*="anim-"]') != null;
}

describe("Piece screens", () => {
  it("draws the scene of each busy step on its own post", () => {
    const codeur = etatApres(ev("agent_started", "codeur"), ev("agent_tool_use", "codeur", { tool: "Edit", input: {} }));
    const lecteur = etatApres(ev("agent_started", "codeur"), ev("agent_tool_use", "codeur", { tool: "Grep", input: {} }));

    expect(noms(ecrans(codeur))[0]).toBe("code");
    expect(noms(ecrans(lecteur))[0]).toBe("lecture");
    expect(noms(ecrans(etatApres(...CODEUR_FINI, ev("test_started"))))).toEqual(["ok", "tests", "eteint", "eteint", "eteint"]);
    expect(noms(ecrans(etatApres(...CODEUR_FINI, ev("security_audit_started"))))[2]).toBe("audit");
    expect(noms(ecrans(etatApres(...CODEUR_FINI, ev("agent_started", "reviewer"))))[3]).toBe("diff");
    expect(noms(ecrans(etatApres(...CODEUR_FINI, ev("validation_started"))))[4]).toBe("criteres");
  });

  it("ticks a done post after a favourable verdict and crosses it after an unfavourable one", () => {
    const favorable = etatApres(
      ...CODEUR_FINI,
      ev("test_result", null, { passed: true }),
      ev("security_audit_done", null, { verdict: "PASS" }),
      ev("agent_started", "reviewer"),
      ev("agent_done", "reviewer", { content: "APPROVED", verdict: "APPROVED" }),
      ev("validation_done", null, { approved: true, verdict: "APPROVED" }),
    );
    const defavorable = etatApres(
      ...CODEUR_FINI,
      ev("test_result", null, { passed: false }),
      ev("security_audit_done", null, { verdict: "BLOCK" }),
      ev("agent_started", "reviewer"),
      ev("agent_done", "reviewer", { content: "CHANGES_REQUESTED", verdict: "CHANGES_REQUESTED" }),
      ev("validation_done", null, { approved: false, verdict: "CHANGES_REQUESTED" }),
    );

    expect(noms(ecrans(favorable))).toEqual(["ok", "ok", "ok", "ok", "ok"]);
    expect(noms(ecrans(defavorable))).toEqual(["ok", "ko", "ko", "ko", "ko"]);
  });

  it("keeps the tick sprite on a favourable screen", () => {
    const [codeur] = ecrans(etatApres(...CODEUR_FINI));

    expect(codeur?.querySelector('[data-sprite="coche"]')).not.toBeNull();
  });
});

describe("Piece screens animation", () => {
  const PAR_ETAPE: [string, OrchestratorEvent[], number][] = [
    ["code", [ev("agent_started", "codeur"), ev("agent_tool_use", "codeur", { tool: "Write", input: {} })], 0],
    ["tests", [...CODEUR_FINI, ev("test_started")], 1],
    ["audit", [...CODEUR_FINI, ev("security_audit_started")], 2],
    ["diff", [...CODEUR_FINI, ev("agent_started", "reviewer")], 3],
    ["criteres", [...CODEUR_FINI, ev("validation_started")], 4],
  ];

  it("animates every scene while the run is active", () => {
    for (const [scene, evenements, poste] of PAR_ETAPE) {
      const ecran = ecrans(etatApres(...evenements))[poste];
      expect(ecran?.getAttribute("data-ecran"), scene).toBe(scene);
      expect(anime(ecran), scene).toBe(true);
    }
  });

  it("freezes every scene once the agent is silent, asks a question or looks frozen", () => {
    const silence = T0 + SEUIL_ATTENTE_MS + 1_000;
    const fige = T0 + 10 * 60_000;
    for (const [scene, evenements, poste] of PAR_ETAPE) {
      const etat = etatApres(...evenements);
      const question = { ...etat, pendingQuestion: "On casse l'API ?" };
      for (const [cas, e, maintenant] of [
        ["silence", etat, silence],
        ["question", question, T0 + 1_000],
        ["frozen", etat, fige],
      ] as const) {
        const ecran = ecrans(e, maintenant)[poste];
        expect(ecran?.getAttribute("data-ecran"), `${scene} ${cas}`).toBe(scene);
        expect(anime(ecran), `${scene} ${cas}`).toBe(false);
      }
    }
  });

  it("animates neither a verdict nor a dark screen", () => {
    const etat = etatApres(...CODEUR_FINI, ev("test_result", null, { passed: false }));

    for (const ecran of ecrans(etat)) expect(anime(ecran), ecran.getAttribute("data-ecran") ?? "").toBe(false);
  });
});
