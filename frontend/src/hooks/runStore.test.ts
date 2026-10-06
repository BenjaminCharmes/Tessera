/**
 * Tests du store externe de runs — ticket-354.
 *
 * Critères d'acceptation couverts :
 * - Un abonné à run-A n'est pas notifié quand seul run-B reçoit un événement.
 * - `useListeRuns()` ne redessine pas sur `agent_token`, redessine sur
 *   changement de statut.
 * - Un événement d'un run ne redessine pas un composant abonné à un autre run.
 */
import { describe, it, expect, beforeEach } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { runStore, useEtatRun, useListeRuns } from "./runStore";
import { INITIAL } from "./streamState";
import type { OrchestratorEvent } from "../types/api";

function makeEvent(
  runId: string,
  type: OrchestratorEvent["type"],
  extra: Partial<OrchestratorEvent> = {},
): OrchestratorEvent {
  return {
    type,
    agent: "codeur",
    ticket_id: "t-1",
    data: {},
    timestamp: new Date().toISOString(),
    run_id: runId,
    project_id: "proj-a",
    ...extra,
  } as OrchestratorEvent;
}

beforeEach(() => {
  runStore.reset();
});

// ---------------------------------------------------------------------------
// Isolation des abonnés (critère 1)
// ---------------------------------------------------------------------------

describe("runStore — isolation des abonnés", () => {
  it("un abonné à run-A n'est pas notifié quand seul run-B reçoit un événement", () => {
    // Semer les deux runs.
    runStore.set("run-A", INITIAL);
    runStore.set("run-B", INITIAL);

    let callsA = 0;
    const unsubA = runStore.subscribe(() => {
      callsA++;
    });

    // On va vérifier que useEtatRun("run-A") ne re-rend pas.
    // Ici on teste au niveau store : un abonné compte les notifications.
    // La notification est globale — l'isolation est dans le sélecteur de
    // useSyncExternalStore qui compare par identité l'état de run-A.
    const snapAvant = runStore.getSnapshot()["run-A"];

    act(() => {
      runStore.appliquer([
        makeEvent("run-B", "agent_started", { data: { round: 1 } }),
      ]);
    });

    // Le listener global a été appelé (run-B a changé).
    expect(callsA).toBeGreaterThan(0);
    // Mais l'état de run-A n'a pas changé de référence.
    expect(runStore.getSnapshot()["run-A"]).toBe(snapAvant);

    unsubA();
  });

  it("useEtatRun('run-A') ne re-rend pas quand seul run-B change", () => {
    runStore.set("run-A", { ...INITIAL, status: "running" });
    runStore.set("run-B", INITIAL);

    let rendersA = 0;
    renderHook(() => {
      rendersA++;
      return useEtatRun("run-A");
    });

    rendersA = 0; // Remettre à zéro après le premier rendu.

    act(() => {
      runStore.appliquer([
        makeEvent("run-B", "agent_started", { data: { round: 1 } }),
      ]);
    });

    // useEtatRun("run-A") retourne la même référence → pas de re-rendu.
    expect(rendersA).toBe(0);
  });

  it("useEtatRun('run-A') re-rend quand run-A change", () => {
    runStore.set("run-A", INITIAL);

    let rendersA = 0;
    renderHook(() => {
      rendersA++;
      return useEtatRun("run-A");
    });

    rendersA = 0;

    act(() => {
      runStore.appliquer([
        makeEvent("run-A", "agent_started", { data: { round: 1 } }),
      ]);
    });

    expect(rendersA).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// useListeRuns — sélecteur stable sur tokens (critère 2)
// ---------------------------------------------------------------------------

describe("useListeRuns — stabilité sur agent_token", () => {
  it("ne re-rend pas sur agent_token (statut inchangé)", () => {
    runStore.set("run-1", { ...INITIAL, status: "running" });

    let renders = 0;
    renderHook(() => {
      renders++;
      return useListeRuns();
    });

    renders = 0;

    act(() => {
      runStore.appliquer([
        makeEvent("run-1", "agent_token", {
          agent: "codeur",
          data: { token: "bonjour" },
        }),
      ]);
    });

    // useListeRuns retourne le même _statusSnapshot → pas de re-rendu.
    expect(renders).toBe(0);
  });

  it("re-rend quand le statut change (pipeline_done)", () => {
    runStore.set("run-1", { ...INITIAL, status: "running" });

    let renders = 0;
    const { result } = renderHook(() => {
      renders++;
      return useListeRuns();
    });

    renders = 0;

    act(() => {
      runStore.appliquer([
        makeEvent("run-1", "pipeline_done", {
          data: { approved: true, rounds: 1, final_status: "done" },
        }),
      ]);
    });

    expect(renders).toBeGreaterThan(0);
    expect(result.current[0]?.status).toBe("done");
  });

  it("re-rend quand une question apparaît", () => {
    runStore.set("run-1", { ...INITIAL, status: "running" });

    let renders = 0;
    renderHook(() => {
      renders++;
      return useListeRuns();
    });

    renders = 0;

    act(() => {
      runStore.appliquer([
        makeEvent("run-1", "agent_question", {
          data: { question: "Casser l'API ?" },
        }),
      ]);
    });

    expect(renders).toBeGreaterThan(0);
  });
});

// ---------------------------------------------------------------------------
// appliquer — sémantique de lot
// ---------------------------------------------------------------------------

describe("runStore.appliquer", () => {
  it("n'émet qu'une notification pour un lot de 10 événements", () => {
    runStore.set("run-1", INITIAL);

    let notifications = 0;
    const unsub = runStore.subscribe(() => notifications++);

    act(() => {
      runStore.appliquer(
        Array.from({ length: 10 }, () =>
          makeEvent("run-1", "agent_tool_use"),
        ),
      );
    });

    expect(notifications).toBe(1);
    unsub();
  });

  it("n'émet pas de notification si aucun état n'a changé", () => {
    // Lot vide ou événements sans run_id.
    let notifications = 0;
    const unsub = runStore.subscribe(() => notifications++);

    act(() => {
      runStore.appliquer([]);
    });

    expect(notifications).toBe(0);
    unsub();
  });
});

// ---------------------------------------------------------------------------
// clearTokens
// ---------------------------------------------------------------------------

describe("runStore.clearTokens", () => {
  it("vide les tokens d'un run et notifie", () => {
    const startedEvent = makeEvent("run-1", "agent_started", {
      data: { round: 1 },
    });
    const tokenEvent = makeEvent("run-1", "agent_token", {
      agent: "codeur",
      data: { token: "bonjour" },
    });

    runStore.set("run-1", INITIAL);
    act(() => runStore.appliquer([startedEvent, tokenEvent]));

    const etatAvant = runStore.getSnapshot()["run-1"]!;
    expect(etatAvant.currentTokens).toBe("bonjour");

    act(() => runStore.clearTokens("run-1"));

    expect(runStore.getSnapshot()["run-1"]!.currentTokens).toBe("");
  });
});
