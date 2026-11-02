import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SupervisionView from "./index";
import ListeView from "./ListeView";
import { INITIAL } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { UseSupervisionResult } from "../../hooks/useSupervision";
import { runStore } from "../../hooks/runStore";
import { apiQuota } from "../../lib/quota";
import { statutsDuRun } from "../../lib/statutDuRun";
import { serviceActif, statutDuRun } from "../../test/contrat/exemples";
import type { OrchestratorEvent, Project, RunActif } from "../../types/api";

vi.mock("../../lib/api", () => ({
  api: {
    runs: { events: vi.fn().mockResolvedValue([]), list: vi.fn().mockResolvedValue([]) },
    orchestrator: { limits: vi.fn().mockResolvedValue({ run_max_budget_usd: 0, llm_max_budget_usd: 0 }) },
    tickets: { activity: vi.fn().mockResolvedValue({ ticket_id: "", runs: [], pr_number: null, github_remote: null }) },
    services: { list: vi.fn().mockResolvedValue([]) },
    github: { getPrStatuses: vi.fn().mockResolvedValue([]) },
    projects: { list: vi.fn().mockResolvedValue([]), overview: vi.fn().mockResolvedValue([]) },
    usage: { stats: vi.fn().mockResolvedValue({ daily: [] }) },
  },
}));

function run(numero: number, over: Partial<RunActif> = {}): RunActif {
  return {
    run_id: `run-${numero}`,
    project_id: `projet-${numero}`,
    mode: "single",
    ticket_id: `ticket-00${numero}`,
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

function pipelineDone(finalStatus: string): OrchestratorEvent {
  return {
    type: "pipeline_done",
    agent: null,
    ticket_id: "ticket-001",
    data: { final_status: finalStatus },
    timestamp: "2026-01-01T00:00:00.000Z",
  };
}

function supervision(
  runs: RunActif[],
  etats: Record<string, Partial<StreamState>> = {},
  over: Partial<UseSupervisionResult> = {},
): UseSupervisionResult {
  for (const [runId, etat] of Object.entries(etats)) {
    runStore.set(runId, { ...INITIAL, ...etat });
  }
  return {
    runs,
    selection: null,
    selectionner: vi.fn(),
    etatDe: (runId: string) => ({ ...INITIAL, ...(etats[runId] ?? {}) }),
    connecte: true,
    envoyer: vi.fn(),
    suivre: vi.fn(),
    observerLeTexte: vi.fn(),
    sortieDuService: () => [],
    signalServices: 0,
    fermerRun: vi.fn(),
    fermerRuns: vi.fn(),
    ...over,
  };
}

const lesRuns = (nombre: number) => Array.from({ length: nombre }, (_, i) => run(i + 1));
const lesProjets = (...ids: string[]): Project[] =>
  ids.map((id) => ({ id, name: id, path: `/p/${id}` }) as Project);
const tousLesProjets = (nombre: number) => lesProjets(...lesRuns(nombre).map((r) => r.project_id));

beforeEach(() => {
  runStore.reset();
  vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows: {} });
  vi.spyOn(statutsDuRun, "lire").mockResolvedValue(
    statutDuRun({
      project_id: "projet-1",
      mode: "queue",
      statut: "en cours",
      ticket_courant: "ticket-001",
      restants: [],
      debut: "2026-10-24T10:00:00Z",
    }),
  );
});

describe("Supervision — vue par défaut et sélecteur", () => {
  it("renders the office when nothing was chosen", () => {
    render(<SupervisionView supervision={supervision(lesRuns(1))} projects={tousLesProjets(1)} />);

    expect(screen.getByRole("region", { name: "projet-1" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Run ticket-001 sur projet-1" })).toBeNull();
    expect(screen.getByRole("button", { name: "Bureau" })).toHaveAttribute("aria-pressed", "true");
  });

  it("switches to the list and renders its run cards", async () => {
    render(<SupervisionView supervision={supervision(lesRuns(1))} projects={tousLesProjets(1)} />);

    await userEvent.click(screen.getByRole("button", { name: "Liste" }));

    expect(screen.getByRole("button", { name: "Run ticket-001 sur projet-1" })).toBeInTheDocument();
    expect(screen.queryByRole("region", { name: "projet-1" })).toBeNull();
  });

  it("comes back to the office from the list", async () => {
    render(<SupervisionView supervision={supervision(lesRuns(1))} projects={tousLesProjets(1)} />);

    await userEvent.click(screen.getByRole("button", { name: "Liste" }));
    await userEvent.click(screen.getByRole("button", { name: "Bureau" }));

    expect(screen.getByRole("region", { name: "projet-1" })).toBeInTheDocument();
  });

  it("does not draw the services strip in the office, but keeps it in the list", async () => {
    const services = [
      serviceActif({
        nom: "backend",
        project_id: "projet-1",
        pid: 1,
        demarre_a: new Date().toISOString(),
        en_cours: true,
      }),
    ];
    render(
      <SupervisionView
        supervision={supervision(lesRuns(1))}
        projects={tousLesProjets(1)}
        services={services}
      />,
    );
    expect(screen.queryByLabelText("Services lancés")).toBeNull();

    await userEvent.click(screen.getByRole("button", { name: "Liste" }));

    expect(screen.getByLabelText("Services lancés")).toHaveTextContent("backend");
  });

  it("zooms the office only, and remembers the choice", async () => {
    // Dézoomer le navigateur rendait le reste de l'app illisible (ticket-657).
    window.localStorage.clear();
    render(<SupervisionView supervision={supervision([])} projects={[]} />);

    await userEvent.click(screen.getByRole("button", { name: "Dézoomer le Bureau" }));

    expect(document.querySelector("[data-zoom]")).toHaveAttribute("data-zoom", "0.9");
    expect(screen.getByRole("group", { name: "Zoom du Bureau" })).toHaveTextContent("90 %");
  });

  it("keeps the office without a run, and says nothing is running where the rooms would be", () => {
    // Le 28/10, sans run, un message remplaçait tout le Bureau : salles du haut,
    // « À toi » et employé de la semaine disparaissaient (ticket-636).
    render(<SupervisionView supervision={supervision([])} projects={[]} />);

    expect(screen.getByText("Salle de pause")).toBeInTheDocument();
    expect(screen.getByText(/Aucun run en cours\. Lance un ticket/)).toBeInTheDocument();
  });
});

describe("Supervision — une pièce par projet", () => {
  it("draws rooms for six projects with a run", () => {
    const { container } = render(
      <SupervisionView supervision={supervision(lesRuns(6))} projects={tousLesProjets(6)} />,
    );

    expect(screen.getAllByRole("region")).toHaveLength(6);
    expect(container.querySelector("[data-mode]")).toHaveAttribute("data-mode", "pieces");
  });

  it("still draws one room per project, stacked, for seven projects with a run", () => {
    const { container } = render(
      <SupervisionView supervision={supervision(lesRuns(7))} projects={tousLesProjets(7)} />,
    );

    expect(screen.getAllByRole("region")).toHaveLength(7);
    expect(container.querySelector("[data-mode]")).toHaveAttribute("data-mode", "pieces");
  });

  it("draws no room for a project at rest", () => {
    render(
      <SupervisionView
        supervision={supervision(lesRuns(6))}
        projects={[...tousLesProjets(6), ...lesProjets("dormant")]}
      />,
    );

    expect(screen.getAllByRole("region")).toHaveLength(6);
    expect(screen.queryByText("au repos")).toBeNull();
  });

  it("draws one room for a project with a chat run and a pipeline run", () => {
    const runs = [run(1, { run_id: "chat", mode: "chat", ticket_id: null }), run(1)];
    render(<SupervisionView supervision={supervision(runs)} projects={tousLesProjets(1)} />);

    expect(screen.getAllByRole("region")).toHaveLength(1);
    expect(screen.getByRole("button", { name: "Ouvrir le fil de ticket-001" })).toBeInTheDocument();
  });
});

describe("Supervision — rangement depuis le Bureau", () => {
  const CLOS = { runClosed: true, events: [pipelineDone("done")] };

  it("puts a closed room away with fermerRuns", async () => {
    const fermerRuns = vi.fn();
    render(
      <SupervisionView
        supervision={supervision(lesRuns(1), { "run-1": CLOS }, { fermerRuns })}
        projects={tousLesProjets(1)}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Ranger ticket-001" }));

    expect(fermerRuns).toHaveBeenCalledWith(["run-1"]);
  });

  it("offers no put-away button while the run is running", () => {
    render(<SupervisionView supervision={supervision(lesRuns(1))} projects={tousLesProjets(1)} />);

    expect(screen.queryByRole("button", { name: /Ranger/ })).toBeNull();
  });

  it("puts away by batch only the runs of the chosen outcome", async () => {
    const fermerRuns = vi.fn();
    const etats = {
      "run-1": {},
      "run-2": CLOS,
      "run-3": { runClosed: true, events: [pipelineDone("blocked")] },
    };
    render(
      <SupervisionView
        supervision={supervision(lesRuns(3), etats, { fermerRuns })}
        projects={tousLesProjets(3)}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Fermer par lot" }));
    await userEvent.click(screen.getByRole("menuitem", { name: /Les bloqués/ }));

    expect(fermerRuns).toHaveBeenCalledWith(["run-3"]);
  });
});

describe("Supervision — chrono et fil depuis le Bureau", () => {
  it("shows the run clock in the room", () => {
    const depuis = new Date(Date.now() - 65_000).toISOString();
    render(
      <SupervisionView
        supervision={supervision([run(1, { demarre_a: depuis })])}
        projects={tousLesProjets(1)}
      />,
    );

    expect(within(screen.getByRole("region", { name: "projet-1" })).getByText(/^1m \d+s$/)).toBeInTheDocument();
  });

  it("switches to the List, with that run selected, when its thread is opened from the room", async () => {
    const selectionner = vi.fn();
    render(
      <SupervisionView supervision={supervision(lesRuns(2), {}, { selectionner })} projects={tousLesProjets(2)} />,
    );

    await userEvent.click(screen.getByRole("button", { name: "Ouvrir le fil de ticket-002" }));

    expect(selectionner).toHaveBeenCalledWith("run-2");
    expect(screen.getByRole("button", { name: "Liste" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.queryByRole("region", { name: "projet-2" })).toBeNull();
  });
});

describe("Supervision — porte d'une pièce", () => {
  it("hands the project of the door to onOpenProject", async () => {
    const onOpenProject = vi.fn();
    const projets = tousLesProjets(2);
    render(<SupervisionView supervision={supervision(lesRuns(2))} projects={projets} onOpenProject={onOpenProject} />);

    await userEvent.click(screen.getByRole("button", { name: "Ouvrir le projet projet-2" }));

    expect(onOpenProject).toHaveBeenCalledTimes(1);
    expect(onOpenProject).toHaveBeenCalledWith(projets[1]);
  });

  it("draws no door button when nobody listens", () => {
    render(<SupervisionView supervision={supervision(lesRuns(1))} projects={tousLesProjets(1)} />);

    expect(screen.queryByRole("button", { name: /Ouvrir le projet/ })).toBeNull();
  });
});

describe("Supervision — même run, même lecture dans les deux vues", () => {
  const CAS: { nom: string; etat: Partial<StreamState>; libelle: string; issue: string; entree: RegExp | null }[] = [
    { nom: "working", etat: { currentAgent: "codeur" }, libelle: "codeur", issue: "en-cours", entree: null },
    { nom: "waiting", etat: { pendingQuestion: "Lequel ?" }, libelle: "attend une réponse", issue: "en-cours", entree: null },
    { nom: "failed", etat: { status: "error", runClosed: true }, libelle: "bloqué", issue: "erreur", entree: /En erreur \(1\)/ },
    { nom: "done", etat: { runClosed: true, events: [pipelineDone("done")] }, libelle: "en cours", issue: "termine", entree: /Les terminés \(1\)/ },
    { nom: "blocked", etat: { runClosed: true, events: [pipelineDone("blocked")] }, libelle: "en cours", issue: "bloque", entree: /Les bloqués \(1\)/ },
  ];

  it.each(CAS)("reads a $nom run the same way in both views", async ({ etat, libelle, issue, entree }) => {
    const props = { supervision: supervision(lesRuns(1), { "run-1": etat }), projects: tousLesProjets(1) };

    const bureau = render(<SupervisionView {...props} />);
    const piece = screen.getByRole("region", { name: "projet-1" });
    expect(within(piece).getByText(libelle, { selector: "[data-etat]" })).toBeInTheDocument();
    expect(piece.querySelector("[data-issue]")).toHaveAttribute("data-issue", issue);
    bureau.unmount();

    render(<ListeView {...props} />);
    const carte = screen.getByRole("button", { name: "Run ticket-001 sur projet-1" });
    expect(within(carte).getByText(libelle, { selector: "[data-etat]" })).toBeInTheDocument();
    if (entree !== null) {
      await userEvent.click(screen.getByRole("button", { name: "Fermer par lot" }));
      expect(screen.getByRole("menuitem", { name: entree })).toBeEnabled();
    }
  });
});
