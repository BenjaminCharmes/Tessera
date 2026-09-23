import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { MockWebSocket } from "../test/mockWebSocket";
import { useSupervision } from "./useSupervision";

vi.stubGlobal("WebSocket", MockWebSocket);

beforeEach(() => {
  MockWebSocket.instance = null;
});

function run(over: Record<string, unknown> = {}) {
  return {
    run_id: "run-1",
    project_id: "ide-core",
    mode: "single",
    ticket_id: "ticket-001",
    etape: null,
    agent: null,
    tour: 0,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    demarre_a: new Date().toISOString(),
    ...over,
  };
}

function evenement(over: Record<string, unknown> = {}) {
  return {
    type: "agent_started",
    agent: "codeur",
    ticket_id: "ticket-001",
    data: {},
    timestamp: new Date().toISOString(),
    run_id: "run-1",
    project_id: "ide-core",
    ...over,
  };
}

describe("useSupervision", () => {
  it("n'ouvre qu'une seule socket, sans projet dans l'URL", () => {
    renderHook(() => useSupervision());
    expect(MockWebSocket.instance?.url).toContain("/orchestrator/observe");
    expect(MockWebSocket.instance?.url).not.toContain("ide-core");
  });

  it("adopte l'instantané reçu à la connexion", () => {
    // Quelqu'un qui ouvre l'IDE alors que des runs tournent doit les voir
    // tout de suite, pas au prochain événement.
    const { result } = renderHook(() => useSupervision());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [run(), run({ run_id: "run-2", project_id: "portfolio" })],
      });
    });

    expect(result.current.runs.map((r) => r.project_id)).toEqual([
      "ide-core",
      "portfolio",
    ]);
  });

  it("montre deux projets qui tournent en même temps", () => {
    // Le parallélisme réel de Tessera (ADR-038), et ce que rien n'affichait.
    const { result } = renderHook(() => useSupervision());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [run(), run({ run_id: "run-2", project_id: "portfolio" })],
      });
    });

    act(() => {
      MockWebSocket.instance!.triggerMessage(evenement({ run_id: "run-1" }));
    });

    expect(result.current.runs).toHaveLength(2);
    // Chaque run accumule le sien : un état partagé afficherait l'agent d'un
    // projet sur la carte d'un autre.
    expect(result.current.etatDe("run-1").currentAgent).toBe("codeur");
    expect(result.current.etatDe("run-2").currentAgent).toBeNull();
    expect(result.current.etatDe("run-2").events).toHaveLength(0);
  });

  it("retire un run sur run_closed, pas sur pipeline_done", () => {
    // `pipeline_done` est publié avant que le projet soit libéré : retirer la
    // carte à ce moment-là ferait croire qu'on peut déjà relancer.
    const { result } = renderHook(() => useSupervision());
    act(() => {
      MockWebSocket.instance!.triggerMessage({ type: "snapshot", runs: [run()] });
    });

    act(() => {
      MockWebSocket.instance!.triggerMessage(evenement({ type: "pipeline_done" }));
    });
    expect(result.current.runs).toHaveLength(1);

    act(() => {
      MockWebSocket.instance!.triggerMessage(evenement({ type: "run_closed" }));
    });
    expect(result.current.runs).toHaveLength(0);
  });

  it("s'abonne au run sélectionné et se désabonne du précédent", () => {
    // Sans le désabonnement, le flux de tokens de tous les runs déjà regardés
    // continuerait d'arriver — ce que l'abonnement existe pour éviter.
    const { result } = renderHook(() => useSupervision());
    act(() => {
      MockWebSocket.instance!.triggerOpen();
    });

    act(() => {
      result.current.selectionner("run-1");
    });
    act(() => {
      result.current.selectionner("run-2");
    });

    const envoyes = MockWebSocket.instance!.sent.map(
      (s) => JSON.parse(s) as Record<string, string>,
    );
    expect(envoyes).toContainEqual({ subscribe: "run-1" });
    expect(envoyes).toContainEqual({ unsubscribe: "run-1" });
    expect(envoyes).toContainEqual({ subscribe: "run-2" });
  });

  it("renvoie son abonnement après une reconnexion", () => {
    // La socket ne commande plus rien depuis ticket-128 : se rattacher est
    // sûr, mais l'abonnement, lui, ne survit pas côté serveur.
    const { result } = renderHook(() => useSupervision());
    act(() => {
      MockWebSocket.instance!.triggerOpen();
      result.current.selectionner("run-1");
    });

    MockWebSocket.instance!.sent = [];
    act(() => {
      MockWebSocket.instance!.triggerOpen();
    });

    expect(
      MockWebSocket.instance!.sent.map((s) => JSON.parse(s) as unknown),
    ).toContainEqual({ subscribe: "run-1" });
  });

  it("adresse une réponse de dialogue au run qu'on nomme", () => {
    // Deux runs suspendus en même temps : une réponse sans destinataire
    // débloquerait le mauvais agent avec le mauvais texte (ADR-025).
    const { result } = renderHook(() => useSupervision());
    act(() => {
      MockWebSocket.instance!.triggerOpen();
    });

    act(() => {
      result.current.envoyer("run-2", { type: "answer", text: "oui" });
    });

    expect(
      MockWebSocket.instance!.sent.map((s) => JSON.parse(s) as unknown),
    ).toContainEqual({ type: "answer", text: "oui", run_id: "run-2" });
  });
});
