import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useCockpit } from "./useCockpit";
import type { Project } from "../types/api";

// Hooks qui ouvrent des sockets ou font des appels réseau : remplacés par des
// valeurs inertes, comme dans App.test.tsx.
const etatInactif = {
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
};

const clear = vi.fn();
const setProject = vi.fn();

vi.mock("./useActiveProject", () => ({
  useActiveProject: () => ({
    project: null,
    ticket: null,
    setProject,
    setTicket: vi.fn(),
  }),
}));
vi.mock("./useSupervision", () => ({
  useSupervision: () => ({
    runs: [],
    selection: null,
    selectionner: vi.fn(),
    etatDe: () => etatInactif,
    connecte: false,
    envoyer: vi.fn(),
    suivre: vi.fn(),
    observerLeTexte: vi.fn(),
    sortieDuService: () => [],
    signalServices: 0,
  }),
}));
vi.mock("./useRunActif", () => ({
  useRunActif: () => ({
    ...etatInactif,
    connect: vi.fn(),
    connectQueue: vi.fn(),
    connectAutonome: vi.fn(),
    disconnect: vi.fn(),
    clear,
    answer: vi.fn(),
    interject: vi.fn(),
    stop: vi.fn(),
  }),
}));
vi.mock("./useTickets", () => ({
  useTickets: () => ({
    tickets: [],
    loading: false,
    error: null,
    refresh: vi.fn(),
    events: [],
    unreadable: [],
  }),
}));
vi.mock("./useRuns", () => ({
  useRuns: () => ({ runs: [], loading: false, error: null, refresh: vi.fn() }),
}));
vi.mock("./useToast", () => ({
  useToast: () => ({ toasts: [], addToast: vi.fn(), removeToast: vi.fn() }),
}));
vi.mock("./useProjects", () => ({
  useProjects: () => ({ projects: [], loading: false, error: null }),
}));
vi.mock("./useServices", () => ({
  useServices: () => ({ services: [], enCours: false }),
}));
vi.mock("./useAppsEnCours", () => ({
  useAppsEnCours: () => ({
    apps: [],
    lueA: 0,
    erreur: null,
    arreter: vi.fn(),
    rafraichir: vi.fn(),
  }),
}));
vi.mock("./useProjetMemorise", () => ({
  useProjetMemorise: () => ({ memoriser: vi.fn() }),
}));
vi.mock("./useFiltresTickets", () => ({
  useFiltresTickets: () => ({
    filtres: { texte: "", type: "", priorite: "", agent: "", tri: "numero" },
    setFiltres: vi.fn(),
  }),
}));
vi.mock("./useNotificationsSysteme", () => ({
  useNotificationsSysteme: () => ({
    active: false,
    etat: "default",
    setActive: vi.fn(),
  }),
  demanderPermissionNotifications: vi.fn(),
}));

const SERPENT: Project = {
  id: "serpent",
  name: "Serpent",
  path: "/workspace/serpent",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
  category: null,
};

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
});

// Critères ticket-425 : changer de projet ne renvoie plus sur les tickets.
describe("useCockpit — project switch (ticket-425)", () => {
  it("stays on the projects panel after selecting a project", () => {
    const { result } = renderHook(() => useCockpit());
    expect(result.current.panel).toBe("projects");

    act(() => result.current.sidebar.projet.onSelect(SERPENT));

    expect(setProject).toHaveBeenCalledWith(SERPENT);
    expect(result.current.panel).toBe("projects");
  });

  it("keeps the list view when the list was showing", () => {
    const { result } = renderHook(() => useCockpit());
    expect(result.current.centre.vueCentre).toBe("kanban");

    act(() => result.current.sidebar.projet.onSelect(SERPENT));

    expect(result.current.centre.vueCentre).toBe("kanban");
  });

  it("keeps the non-board view when the board was hidden", () => {
    const { result } = renderHook(() => useCockpit());
    act(() => result.current.sidebar.tickets.onToggleKanban());
    expect(result.current.centre.vueCentre).toBe("editor");

    act(() => result.current.sidebar.projet.onSelect(SERPENT));

    expect(result.current.centre.vueCentre).toBe("editor");
  });

  it("closes the open file and clears the run stream", () => {
    const { result } = renderHook(() => useCockpit());
    act(() => result.current.sidebar.fichiers.onOpen("src/main.ts"));
    expect(result.current.centre.openFilePath).toBe("src/main.ts");

    act(() => result.current.sidebar.projet.onSelect(SERPENT));

    expect(result.current.centre.openFilePath).toBeNull();
    expect(clear).toHaveBeenCalled();
  });
});
