import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import CenterView from "./CenterView";
import type { useSupervision } from "../hooks/useSupervision";
import type { useRunActif } from "../hooks/useRunActif";
import type { TicketStatus } from "../types/api";

// Mocks de toutes les vues pour ne pas tirer leurs dépendances lourdes.
vi.mock("./ChatPanel", () => ({
  default: () => <div data-testid="chat-panel">ChatPanel</div>,
}));
vi.mock("./Editor", () => ({
  default: () => <div data-testid="editor">Editor</div>,
}));
vi.mock("./DiffView", () => ({
  default: () => <div data-testid="diff-view">DiffView</div>,
}));
vi.mock("./StatsView", () => ({
  default: () => <div data-testid="stats-view">StatsView</div>,
}));
vi.mock("./AgentDetail", () => ({
  default: () => <div data-testid="agent-detail">AgentDetail</div>,
}));
vi.mock("./SupervisionView", () => ({
  default: () => <div data-testid="supervision-view">SupervisionView</div>,
}));
vi.mock("./RunView", () => ({
  default: () => <div data-testid="run-view">RunView</div>,
}));
vi.mock("./KanbanView", () => ({
  default: () => <div data-testid="kanban-view">KanbanView</div>,
}));

const STATUTS: TicketStatus[] = [
  "todo",
  "in-progress",
  "in-review",
  "done",
  "blocked",
  "cancelled",
];

const byStatus = Object.fromEntries(
  STATUTS.map((s) => [s, []]),
) as Record<TicketStatus, never[]>;

/** Props minimales qui satisfont CenterViewProps sans dépendances réelles. */
const baseProps = {
  panel: "tickets" as const,
  vueCentre: "editor" as const,
  project: null,
  projets: [],
  ticket: null,
  conversationId: "",
  supervision: {} as unknown as ReturnType<typeof useSupervision>,
  servicesDuProjet: [],
  agentSelectionne: null,
  stream: {} as unknown as ReturnType<typeof useRunActif>,
  byStatus,
  running: new Set<string>(),
  unreadable: [],
  openFilePath: null,
  statsDays: 7 as const,
  statsProjectId: null,
  onSelectTicket: vi.fn(),
  onRunPipeline: vi.fn(),
  onChangeStatus: vi.fn(),
};

describe("CenterView", () => {
  it("displays the lazy Editor view after Suspense resolves", async () => {
    render(<CenterView {...baseProps} vueCentre="editor" />);
    // findBy attend la résolution du Suspense — le composant étant lazy,
    // il est absent au premier rendu synchrone.
    expect(await screen.findByTestId("editor")).toBeInTheDocument();
  });

  it("displays the lazy ChatPanel when panel is chat", async () => {
    render(<CenterView {...baseProps} panel="chat" />);
    expect(await screen.findByTestId("chat-panel")).toBeInTheDocument();
  });

  it("displays the lazy DiffView when vueCentre is diff", async () => {
    const project = {
      id: "p1",
      name: "P1",
      path: "/p1",
      description: "",
      active_agents: [],
      stack: null,
      raw_claude_md: "",
      github_remote: null,
    };
    const ticket = {
      id: "t1",
      title: "T1",
      status: "todo" as const,
      type: "feat" as const,
      priority: "medium" as const,
      agent: "codeur",
      depends_on: [],
      created: "2026-01-01T00:00:00Z",
      github_issue_url: null,
      pr_number: null,
      body: "",
      project_id: "p1",
      file_path: "",
    };
    render(
      <CenterView
        {...baseProps}
        vueCentre="diff"
        project={project}
        ticket={ticket}
      />,
    );
    expect(await screen.findByTestId("diff-view")).toBeInTheDocument();
  });

  it("displays the lazy StatsView when panel is usage", async () => {
    render(<CenterView {...baseProps} panel="usage" />);
    expect(await screen.findByTestId("stats-view")).toBeInTheDocument();
  });
});
