import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MockWebSocket } from "../test/mockWebSocket";
import { useSupervision } from "./useSupervision";
import { etatDepuisRun } from "./streamState";

vi.stubGlobal("WebSocket", MockWebSocket);

beforeEach(() => {
  MockWebSocket.instance = null;
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

function run(over: Record<string, unknown> = {}) {
  return {
    run_id: "run-1",
    project_id: "demineur",
    mode: "single",
    ticket_id: "ticket-001",
    etape: null,
    agent: null,
    tour: 0,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    question: null,
    file_index: 0,
    file_total: 0,
    file_restants: [],
    demarre_a: new Date().toISOString(),
    ...over,
  };
}

describe("useSupervision — la socket se rouvre (ticket-163)", () => {
  it("rouvre la socket après une fermeture", () => {
    // Un redémarrage du backend suffisait à rendre l'onglet aveugle pour de
    // bon : rien ne rouvrait, et le seul signe était « hors ligne ».
    renderHook(() => useSupervision());
    const premiere = MockWebSocket.instance;
    act(() => premiere!.triggerOpen());

    act(() => premiere!.triggerClose());
    act(() => {
      vi.advanceTimersByTime(10_000);
    });

    expect(MockWebSocket.instance).not.toBe(premiere);
  });

  it("espace les tentatives au lieu de marteler", () => {
    renderHook(() => useSupervision());
    const premiere = MockWebSocket.instance;
    act(() => premiere!.triggerOpen());
    act(() => premiere!.triggerClose());

    act(() => {
      vi.advanceTimersByTime(50);
    });

    expect(MockWebSocket.instance).toBe(premiere);
  });
});

describe("etatDepuisRun — l'instantané sème l'état (ticket-163)", () => {
  it("rend un run en cours, pas au repos", () => {
    // `status` ne passait à `running` que sur `agent_started`, émis une fois
    // trois secondes après le début : tout observateur plus tardif restait
    // `idle` pour la durée du run.
    const etat = etatDepuisRun(run({ agent: "codeur", tour: 1 }));

    expect(etat.status).toBe("running");
    expect(etat.currentAgent).toBe("codeur");
    expect(etat.currentRound).toBe(1);
  });

  it("porte la question en attente", () => {
    // Sans elle, `AgentDialogue` rend `null` et personne ne peut répondre —
    // alors qu'ADR-025 attend précisément une réponse humaine.
    const etat = etatDepuisRun(run({ agent: "codeur", question: "On casse l'API ?" }));

    expect(etat.pendingQuestion).toBe("On casse l'API ?");
  });

  it("sans question, n'en invente pas", () => {
    expect(etatDepuisRun(run({ agent: "codeur" })).pendingQuestion).toBeNull();
  });
});

describe("useSupervision — l'instantané alimente l'état du run", () => {
  it("un run reçu dans l'instantané est déjà en cours", () => {
    const { result } = renderHook(() => useSupervision());
    act(() => MockWebSocket.instance!.triggerOpen());

    act(() =>
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [run({ agent: "codeur", tour: 1, question: "On casse l'API ?" })],
      }),
    );

    const etat = result.current.etatDe("run-1");
    expect(etat.status).toBe("running");
    expect(etat.pendingQuestion).toBe("On casse l'API ?");
  });
});
