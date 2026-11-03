import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { api } from "../../lib/api";
import Sidebar from "./index";
import type { Project, Ticket, TicketStatus } from "../../types/api";

/**
 * L'en-tête de colonne ne montre que ce qui concerne le projet actif — ticket-441.
 */

const project: Project = {
  id: "lyra",
  name: "Lyra",
  path: "/w/lyra",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

const byStatus: Record<TicketStatus, Ticket[]> = {
  todo: [],
  "in-progress": [],
  "in-review": [],
  done: [],
  blocked: [],
  cancelled: [],
};

type SidebarProps = Parameters<typeof Sidebar>[0];

function renderSidebar(
  running: string[] = [],
  panel: SidebarProps["panel"] = "chat",
  actif: Project = project,
) {
  const props: SidebarProps = {
    panel,
    projet: { actif, onSelect: () => {} },
    tickets: {
      byStatus,
      loading: false,
      error: null,
      actif: null,
      running: new Set<string>(running),
      showKanban: false,
      onSelect: () => {},
      onRunPipeline: () => {},
      onToggleKanban: () => {},
    },
    runs: { liste: [], loading: false, error: null },
    usage: {
      days: 30,
      setDays: () => {},
      portee: "tous",
      setPortee: () => {},
      projetActifId: null,
    },
  };
  return render(<Sidebar {...props} />);
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api.projects, "list").mockResolvedValue([project]);
  vi.spyOn(api.chat, "list").mockResolvedValue([]);
});

describe("Sidebar — en-tête allégé (ticket-441)", () => {
  it("ne répète plus le réglage des notifications sous le nom du projet", () => {
    renderSidebar();

    expect(screen.queryByText(/bloquées par le navigateur/)).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Notifications système")).not.toBeInTheDocument();
  });

  it("montre la pastille « run en cours » quand un run tourne", () => {
    renderSidebar(["ticket-001"]);

    expect(screen.getByText("run en cours")).toBeInTheDocument();
  });

  it("n'affiche aucune pastille quand aucun run ne tourne", () => {
    renderSidebar([]);

    expect(screen.queryByText("run en cours")).not.toBeInTheDocument();
  });

  it("garde le réglage du pipeline sur l'onglet Tickets", () => {
    renderSidebar([], "tickets");

    expect(screen.getByRole("button", { name: "Pipeline" })).toBeInTheDocument();
  });

  it("ne montre plus le réglage du pipeline sous l'en-tête des autres onglets", () => {
    renderSidebar([], "chat");

    expect(screen.queryByRole("button", { name: "Pipeline" })).not.toBeInTheDocument();
  });

  it("ne remplace pas le panneau des services par une phrase pour ide-core", () => {
    renderSidebar([], "chat", { ...project, fait_tourner_l_ide: true });

    expect(screen.queryByText(/fait tourner l'IDE/)).not.toBeInTheDocument();
  });
});
