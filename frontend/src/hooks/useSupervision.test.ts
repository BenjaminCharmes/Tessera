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

  it("ne retire pas un run sur pipeline_done ni sur run_closed (ticket-267)", () => {
    // `pipeline_done` est publié avant que le projet soit libéré.
    // `run_closed` marque le run clos (runClosed: true) mais laisse la carte
    // visible : c'est l'utilisateur qui ferme via fermerRun.
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
    // La carte reste visible jusqu'au clic « Fermer ».
    expect(result.current.runs).toHaveLength(1);
    // Mais le run est bien marqué clos dans son état.
    expect(result.current.etatDe("run-1").runClosed).toBe(true);
  });

  it("fermerRun retire le run de la liste", () => {
    const { result } = renderHook(() => useSupervision());
    act(() => {
      MockWebSocket.instance!.triggerMessage({ type: "snapshot", runs: [run()] });
    });

    act(() => {
      result.current.fermerRun("run-1");
    });
    expect(result.current.runs).toHaveLength(0);
  });

  it("fermerRuns removes named runs and keeps the others", () => {
    const { result } = renderHook(() => useSupervision());
    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [
          run({ run_id: "run-1" }),
          run({ run_id: "run-2", project_id: "portfolio" }),
          run({ run_id: "run-3", project_id: "autre" }),
        ],
      });
    });

    act(() => {
      result.current.fermerRuns(["run-1", "run-3"]);
    });

    expect(result.current.runs.map((r) => r.run_id)).toEqual(["run-2"]);
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

describe("useSupervision — aller-retour entre deux runs (ticket-313)", () => {
  it("un aller-retour laisse le texte du codeur inchangé", () => {
    // Le backend rejoue les tokens à chaque abonnement. Sans clearTokensForReplay,
    // revenir sur run-1 doublerait le texte déjà accumulé.
    const { result } = renderHook(() => useSupervision());
    act(() => MockWebSocket.instance!.triggerOpen());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "snapshot",
        runs: [run(), run({ run_id: "run-2", project_id: "autre" })],
      });
    });

    // Sélectionner run-1 → subscribe envoyé, tokens vidés (état initial vide)
    act(() => { result.current.selectionner("run-1"); });

    // Le backend envoie agent_started + un token (premier abonnement)
    act(() => {
      MockWebSocket.instance!.triggerMessage(
        evenement({ type: "agent_started", run_id: "run-1", agent: "codeur", data: { round: 1 } }),
      );
      MockWebSocket.instance!.triggerMessage(
        evenement({ type: "agent_token", run_id: "run-1", agent: "codeur", data: { token: "bonjour" } }),
      );
    });

    // Passer à run-2 → unsubscribe run-1
    act(() => { result.current.selectionner("run-2"); });

    // Revenir sur run-1 → subscribe envoyé, tokens vidés avant le rejeu
    act(() => { result.current.selectionner("run-1"); });

    // Le backend rejoue uniquement agent_token (pas agent_started, cf. RETENUS)
    act(() => {
      MockWebSocket.instance!.triggerMessage(
        evenement({ type: "agent_token", run_id: "run-1", agent: "codeur", data: { token: "bonjour" } }),
      );
    });

    const etat = result.current.etatDe("run-1");
    const codeurEntry = etat.entries.find((e) => e.genre === "agent" && e.agent === "codeur");
    expect(codeurEntry?.genre === "agent" ? codeurEntry.tokens : "").toBe("bonjour");
  });
});

describe("useSupervision — les services (ticket-145)", () => {
  function evenementService(over: Record<string, unknown> = {}) {
    return {
      type: "service_output",
      agent: null,
      ticket_id: "frontend",
      data: { ligne: "VITE ready", service: "frontend" },
      timestamp: new Date().toISOString(),
      run_id: null,
      project_id: "ide-core",
      ...over,
    };
  }

  it("garde la sortie d'un service, qui n'a pas de run_id", () => {
    // `if (!runId) return` jetait ces trames : la sortie n'arrivait jamais,
    // même une fois l'affichage écrit.
    const { result } = renderHook(() => useSupervision());

    act(() => {
      MockWebSocket.instance!.triggerMessage(evenementService());
    });

    expect(result.current.sortieDuService("ide-core", "frontend")).toEqual([
      "VITE ready",
    ]);
  });

  it("sépare les sorties de deux services", () => {
    const { result } = renderHook(() => useSupervision());

    act(() => {
      MockWebSocket.instance!.triggerMessage(evenementService());
      MockWebSocket.instance!.triggerMessage(
        evenementService({
          ticket_id: "backend",
          data: { ligne: "address in use", service: "backend" },
        }),
      );
    });

    expect(result.current.sortieDuService("ide-core", "backend")).toEqual([
      "address in use",
    ]);
    expect(result.current.sortieDuService("ide-core", "frontend")).toEqual([
      "VITE ready",
    ]);
  });

  it("compte les évènements de service, pour déclencher une relecture", () => {
    // Sans ce signal, rien ne dit à `useServices` qu'un service vient de
    // mourir : le bouton proposerait « Arrêter » pour un processus disparu.
    const { result } = renderHook(() => useSupervision());
    const avant = result.current.signalServices;

    act(() => {
      MockWebSocket.instance!.triggerMessage(
        evenementService({
          type: "service_closed",
          data: { service: "backend", code_de_sortie: 1 },
        }),
      );
    });

    expect(result.current.signalServices).toBeGreaterThan(avant);
  });
});
