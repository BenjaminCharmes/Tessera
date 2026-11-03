import { beforeEach, describe, expect, it, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useCockpit } from "./useCockpit";
import { ouvrirTicketsDuProjet } from "./useOuvrirTicket";
import type { Project, Ticket } from "../types/api";

const { list, flux, clear } = vi.hoisted(() => ({
  list: vi.fn(),
  clear: vi.fn(),
  flux: {
    status: "running",
    ticketId: "ticket-1",
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
  },
}));

vi.mock("../lib/api", () => ({ api: { tickets: { list, setStatus: vi.fn() } } }));
vi.mock("./useSupervision", () => ({
  useSupervision: () => ({
    runs: [],
    selection: null,
    selectionner: vi.fn(),
    etatDe: () => flux,
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
    ...flux,
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
  useProjects: () => ({ projects: PROJETS, loading: false, error: null }),
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
    cloche: { reglages: { question: { systeme: true, son: true } }, setReglage: vi.fn() },
  }),
  demanderPermissionNotifications: vi.fn(),
}));

function projet(id: string): Project {
  return {
    id,
    name: id,
    path: `/workspace/${id}`,
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
    category: null,
  };
}

const PROJETS = [projet("serpent"), projet("demineur")];

const TICKET = {
  id: "ticket-7",
  title: "Le septième",
  status: "done",
  project_id: "demineur",
} as Ticket;

beforeEach(() => {
  localStorage.clear();
  vi.clearAllMocks();
  list.mockResolvedValue({ tickets: [TICKET], unreadable: [] });
});

describe("useCockpit — ouvrirTicket (ticket-460)", () => {
  it("activates the ticket's project, then shows its detail in the Tickets tab", async () => {
    const { result } = renderHook(() => useCockpit());
    act(() => result.current.sidebar.projet.onSelect(PROJETS[0]));
    expect(result.current.centre.project?.id).toBe("serpent");

    await act(async () => {
      expect(await result.current.ouvrirTicket("demineur", "ticket-7")).toBe("ok");
    });

    expect(result.current.centre.project?.id).toBe("demineur");
    expect(result.current.centre.ticket).toEqual(TICKET);
    expect(result.current.panel).toBe("tickets");
  });

  it("takes the centre back from the running run", async () => {
    const { result } = renderHook(() => useCockpit());
    act(() => result.current.sidebar.projet.onSelect(PROJETS[1]));
    expect(result.current.centre.vueCentre).toBe("run");

    await act(async () => {
      await result.current.ouvrirTicket("demineur", "ticket-7");
    });

    expect(result.current.centre.vueCentre).toBe("editor");
  });

  it("leaves the active project and the panel alone when the ticket is missing", async () => {
    const { result } = renderHook(() => useCockpit());
    act(() => result.current.sidebar.projet.onSelect(PROJETS[0]));
    clear.mockClear();

    await act(async () => {
      expect(await result.current.ouvrirTicket("demineur", "ticket-404")).toBe(
        "introuvable",
      );
    });

    expect(result.current.centre.project?.id).toBe("serpent");
    expect(result.current.panel).toBe("projects");
    expect(clear).not.toHaveBeenCalled();
  });
});

describe("useCockpit — porte du Bureau (ticket-602)", () => {
  it("picks the project of the door and opens the Tickets tab", () => {
    const { result } = renderHook(() => useCockpit());
    act(() => result.current.sidebar.projet.onSelect(PROJETS[0]));
    expect(result.current.panel).toBe("projects");

    act(() => result.current.centre.onOpenProject(PROJETS[1]));

    expect(result.current.centre.project?.id).toBe("demineur");
    expect(result.current.panel).toBe("tickets");
  });

  it("opens the Tickets tab even when the door's project is already the active one", () => {
    const { result } = renderHook(() => useCockpit());
    act(() => result.current.sidebar.projet.onSelect(PROJETS[0]));

    act(() => result.current.centre.onOpenProject(PROJETS[0]));

    expect(result.current.centre.project?.id).toBe("serpent");
    expect(result.current.panel).toBe("tickets");
  });
});

describe("ouvrirTicketsDuProjet", () => {
  it("selects the project first, then asks for the tickets panel", () => {
    const appels: string[] = [];
    const ouvrir = ouvrirTicketsDuProjet(
      (p) => appels.push(`projet:${p.id}`),
      (panneau) => appels.push(`panneau:${panneau}`),
    );

    ouvrir(PROJETS[1]);

    expect(appels).toEqual(["projet:demineur", "panneau:tickets"]);
  });
});
