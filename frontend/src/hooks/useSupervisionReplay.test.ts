/**
 * Rechargement de page : reconstruction de l'historique d'un run vivant.
 *
 * ticket-325 — quand la page se recharge, l'instantané ne contient que
 * l'agent en cours. GET /runs/{db_run_id}/events renvoie les événements
 * persistés ; useSupervision les rejoue pour reconstruire toutes les cartes.
 *
 * Compatibilité ticket-353 : le chemin historique passe par chargerHistorique
 * qui applique les événements directement via setEtats (pas par pendingRef),
 * donc ces tests ne dépendent pas du regroupement par image et restent verts
 * sans avance de frame.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { MockWebSocket } from "../test/mockWebSocket";
import { useSupervision } from "./useSupervision";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mockFetch = vi.fn<any>();
vi.stubGlobal("WebSocket", MockWebSocket);
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  MockWebSocket.instance = null;
  mockFetch.mockReset();
});

afterEach(() => {
  vi.restoreAllMocks();
});

/** Un run vivant renvoyé dans l'instantané, avec db_run_id. */
function runVivant(over: Record<string, unknown> = {}) {
  return {
    run_id: "run-1",
    project_id: "ide-core",
    mode: "single",
    ticket_id: "ticket-001",
    etape: null,
    agent: "codeur",
    tour: 2,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    demarre_a: new Date().toISOString(),
    db_run_id: "db-xyz",
    ...over,
  };
}

/** Événements persistés simulant un premier tour codeur + reviewer terminés. */
function evenementsHistoriques() {
  return [
    { type: "agent_started", agent: "codeur", data: { round: 1 }, timestamp: "2026-10-02T10:00:01.000Z" },
    { type: "agent_done", agent: "codeur", data: { content: "Code écrit.", cost_usd: 0.1 }, timestamp: "2026-10-02T10:00:02.000Z" },
    { type: "agent_started", agent: "reviewer", data: { round: 1 }, timestamp: "2026-10-02T10:00:03.000Z" },
    { type: "agent_done", agent: "reviewer", data: { content: "CHANGES_REQUESTED\nAjouter des tests.", cost_usd: 0.05 }, timestamp: "2026-10-02T10:00:04.000Z" },
    { type: "agent_started", agent: "codeur", data: { round: 2 }, timestamp: "2026-10-02T10:00:05.000Z" },
  ];
}

function mockEventsResponse(events: unknown[]) {
  mockFetch.mockResolvedValue({
    ok: true,
    json: () => Promise.resolve(events),
  } as Response);
}

describe("useSupervision — rechargement de l'historique (ticket-325)", () => {
  it("appelle GET /runs/{db_run_id}/events quand le run a un db_run_id", async () => {
    mockEventsResponse([]);

    renderHook(() => useSupervision());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [runVivant()],
      });
    });

    await waitFor(() => {
      const url = mockFetch.mock.calls[0]?.[0] as string | undefined;
      expect(url).toContain("/runs/db-xyz/events");
    });
  });

  it("ne déclenche pas de fetch si db_run_id est absent", async () => {
    renderHook(() => useSupervision());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [runVivant({ db_run_id: null })],
      });
    });

    await new Promise((r) => setTimeout(r, 20));
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it("montre une carte par passage d'agent terminé après le rejeu", async () => {
    mockEventsResponse(evenementsHistoriques());

    const { result } = renderHook(() => useSupervision());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [runVivant()],
      });
    });

    await waitFor(() => {
      // codeur tour 1 (done) + reviewer tour 1 (done) + codeur tour 2 (en cours) = 3
      expect(result.current.etatDe("run-1").entries).toHaveLength(3);
    });

    const entries = result.current.etatDe("run-1").entries;
    const termines = entries.filter((e) => e.isDone);
    expect(termines).toHaveLength(2);
    expect(entries[0]).toMatchObject({ genre: "agent", agent: "codeur", isDone: true });
    expect(entries[1]).toMatchObject({ genre: "agent", agent: "reviewer", isDone: true });
    expect(entries[2]).toMatchObject({ genre: "agent", agent: "codeur", isDone: false });
  });

  it("n'applique pas deux fois un événement reçu via l'historique et le flux en direct", async () => {
    const evts = evenementsHistoriques();
    // Le dernier événement historique est agent_started codeur tour 2 à T5.
    const dernierTs = evts[evts.length - 1]!.timestamp;

    // La résolution est différée pour laisser le temps d'injecter un doublon.
    let resoudre!: (v: Response) => void;
    mockFetch.mockReturnValue(
      new Promise<Response>((resolve) => { resoudre = resolve; }),
    );

    const { result } = renderHook(() => useSupervision());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [runVivant()],
      });
    });

    // Un événement en direct avec le même horodatage que le dernier événement
    // historique arrive pendant que le fetch est en cours.
    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "agent_started",
        agent: "codeur",
        data: { round: 2 },
        timestamp: dernierTs,
        run_id: "run-1",
        ticket_id: "ticket-001",
        project_id: "ide-core",
      });
    });

    // Résoudre le fetch avec les événements historiques.
    act(() => {
      resoudre({
        ok: true,
        json: () => Promise.resolve(evts),
      } as Response);
    });

    await waitFor(() => {
      // Doit rester 3 entrées, pas 4 : le doublon a été écarté.
      expect(result.current.etatDe("run-1").entries).toHaveLength(3);
    });
  });

  it("n'appelle pas deux fois /events pour le même run (idempotence)", async () => {
    mockEventsResponse([]);

    const { result } = renderHook(() => useSupervision());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [runVivant()],
      });
    });

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(1));

    // Deuxième snapshot (reconnexion) — ne doit pas refetch.
    act(() => {
      result.current.selectionner("run-1");
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [runVivant()],
      });
    });

    await new Promise((r) => setTimeout(r, 20));
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});
