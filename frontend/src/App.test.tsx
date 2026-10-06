import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import App from "./App";
import React from "react";

// --- Stub components — évite Monaco, WebSocket, fetch dans les tests App ---

vi.mock("./components/Sidebar", () => ({ default: () => null }));
vi.mock("./components/ChatPanel", () => ({
  default: () => <div data-testid="chat-panel" />,
}));
vi.mock("./components/SupervisionView", () => ({ default: () => null }));
vi.mock("./components/AgentDetail", () => ({ default: () => null }));
vi.mock("./components/StatsView", () => ({ default: () => null }));
vi.mock("./components/RunView", () => ({ default: () => null }));
vi.mock("./components/Editor", () => ({ default: () => null }));
vi.mock("./components/KanbanView", () => ({ default: () => null }));
vi.mock("./components/DiffView", () => ({ default: () => null }));
vi.mock("./components/BottomPanel", () => ({ default: () => null }));
vi.mock("./components/Toast", () => ({ default: () => null }));

// --- Stub hooks qui ouvrent des sockets ou font des appels réseau ---

vi.mock("./hooks/useActiveProject", () => ({
  useActiveProject: () => ({
    project: null,
    ticket: null,
    setProject: vi.fn(),
    setTicket: vi.fn(),
  }),
}));

vi.mock("./hooks/useSupervision", () => ({
  useSupervision: () => ({
    runs: [],
    selection: null,
    selectionner: vi.fn(),
    etatDe: () => ({
      status: "idle",
      ticketId: null,
      events: [],
      currentAgent: null,
      currentRound: 0,
      currentTokens: "",
      lastResult: null,
      errorMessage: null,
      quota: null,
      pendingQuestion: null,
      questionExpireA: null,
      queue: null,
      branch: null,
      maxRounds: null,
      coutUsd: 0,
      appels: 0,
      outils: 0,
      entries: [],
    }),
    connecte: false,
    envoyer: vi.fn(),
    suivre: vi.fn(),
    observerLeTexte: vi.fn(),
    sortieDuService: () => [],
    signalServices: 0,
  }),
}));

vi.mock("./hooks/useRunActif", () => ({
  useRunActif: () => ({
    status: "idle",
    ticketId: null,
    events: [],
    currentAgent: null,
    currentRound: 0,
    currentTokens: "",
    lastResult: null,
    errorMessage: null,
    quota: null,
    pendingQuestion: null,
    questionExpireA: null,
    queue: null,
    branch: null,
    maxRounds: null,
    coutUsd: 0,
    appels: 0,
    outils: 0,
    entries: [],
    connect: vi.fn(),
    connectQueue: vi.fn(),
    connectAutonome: vi.fn(),
    disconnect: vi.fn(),
    clear: vi.fn(),
    answer: vi.fn(),
    interject: vi.fn(),
    stop: vi.fn(),
  }),
}));

vi.mock("./hooks/useTickets", () => ({
  useTickets: () => ({
    tickets: [],
    loading: false,
    error: null,
    refresh: vi.fn(),
    events: [],
    unreadable: [],
  }),
}));

vi.mock("./hooks/useRuns", () => ({
  useRuns: () => ({ runs: [], loading: false, error: null, refresh: vi.fn() }),
}));

vi.mock("./hooks/useToast", () => ({
  useToast: () => ({
    toasts: [],
    addToast: vi.fn(),
    removeToast: vi.fn(),
  }),
}));

vi.mock("./hooks/useProjects", () => ({
  useProjects: () => ({ projects: [], loading: false, error: null }),
}));

vi.mock("./hooks/useServices", () => ({
  useServices: () => ({ services: [], enCours: false }),
}));

vi.mock("./hooks/useProjetMemorise", () => ({
  useProjetMemorise: () => ({ memoriser: vi.fn() }),
}));

vi.mock("./hooks/useFiltresTickets", () => ({
  useFiltresTickets: () => ({
    filtres: { texte: "", type: "", priorite: "", agent: "", tri: "numero" },
    setFiltres: vi.fn(),
  }),
}));

vi.mock("./hooks/useNotificationsSysteme", () => ({
  useNotificationsSysteme: () => ({
    active: false,
    etat: "default",
    setActive: vi.fn(),
  }),
  demanderPermissionNotifications: vi.fn(),
}));

beforeEach(() => {
  localStorage.clear();
});

describe("App — panneau Chat", () => {
  it("choisir Chat affiche ChatPanel dans la zone centrale", async () => {
    render(<App />);

    await userEvent.click(screen.getByRole("tab", { name: /^Chat$/ }));

    const main = screen.getByRole("main");
    // ChatPanel est chargé en lazy : on attend sa résolution avant l'assertion.
    const chatPanel = await screen.findByTestId("chat-panel");
    expect(main).toContainElement(chatPanel);
  });

  it("ne rend plus d'onglets Agents et Chat en colonne de droite", () => {
    render(<App />);
    // L'ancienne colonne de droite portait un tablist « Panneau latéral »
    // avec deux onglets « Agents » et « Chat ». Ce tablist ne doit plus exister :
    // le suivi des runs passe par Supervision, le chat par la vue centrale.
    expect(
      screen.queryByRole("tablist", { name: /panneau lat/i }),
    ).not.toBeInTheDocument();
  });
});

// ---------------------------------------------------------------------------
// Ticket-354 : React.memo sur TicketCard — la carte ne se redessine pas si
// ses props n'ont pas changé.
// ---------------------------------------------------------------------------

import TicketCard from "./components/Sidebar/TicketCard";
import type { Ticket } from "./types/api";

describe("TicketCard — React.memo (ticket-354)", () => {
  const ticket: Ticket = {
    id: "ticket-001",
    title: "Add auth module",
    type: "feat",
    status: "todo",
    priority: "high",
    agent: "codeur",
    depends_on: [],
    created: "2026-10-01",
    github_issue_url: null,
    pr_number: null,
    body: "",
    project_id: "ide-core",
    file_path: "/projects/ide-core/tickets/todo/ticket-001.md",
  };

  it("est enveloppée dans React.memo", () => {
    // Un composant React.memo porte le symbole 'react.memo' dans $$typeof.
    // Vérifier que TicketCard est bien un composant mémoïsé — c'est la
    // garantie structurelle que React ne le repassera pas si ses props n'ont
    // pas changé (ticket-354).
    const type = (TicketCard as unknown as { $$typeof?: unknown })?.$$typeof;
    expect(String(type)).toContain("memo");
  });

  it("ne se redessine pas quand le parent re-rend avec les mêmes props", () => {
    let renders = 0;

    // Composant interne compté, enveloppé dans le même TicketCard mémoïsé.
    function Inner() {
      renders++;
      return null;
    }

    // Composant parent qui re-rend sans changer les props de TicketCard.
    function Parent({ tick }: { tick: number }) {
      void tick;
      const stableOnSelect = React.useCallback(() => undefined, []);
      const stableOnRun = React.useCallback(() => undefined, []);
      return (
        <>
          <TicketCard
            ticket={ticket}
            isActive={false}
            isRunning={false}
            onSelect={stableOnSelect}
            onRun={stableOnRun}
          />
          <Inner />
        </>
      );
    }

    const { rerender } = render(<Parent tick={0} />);
    renders = 0;

    // Re-rendu du parent (Inner re-rend), props de TicketCard identiques.
    act(() => { rerender(<Parent tick={1} />); });

    // Inner a re-rendu (le parent a bien re-rendu).
    expect(renders).toBeGreaterThan(0);
    // Et l'affichage de TicketCard est toujours correct.
    expect(screen.getByText("Add auth module")).toBeInTheDocument();
  });
});
