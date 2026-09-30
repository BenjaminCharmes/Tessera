import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../../lib/api";
import Sidebar from "./index";
import type { Project, Ticket, TicketStatus } from "../../types/api";

/**
 * Les conversations du chat vivent dans la colonne 2 — ticket-250.
 *
 * Avant, le panneau Chat laissait la colonne latérale vide (280 px) pendant
 * que le centre s'ouvrait sa propre mini-colonne de conversations : deux
 * colonnes côte à côte, dont une sans contenu.
 */

const project: Project = {
  id: "ide-core",
  name: "ide-core",
  path: "/w/ide-core",
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

function renderSidebar(extra: Partial<SidebarProps> = {}) {
  const base: SidebarProps = {
    panel: "chat",
    projet: { actif: project, onSelect: () => {} },
    tickets: {
      byStatus,
      loading: false,
      error: null,
      actif: null,
      running: new Set<string>(),
      showKanban: false,
      onSelect: () => {},
      onRunPipeline: () => {},
      onToggleKanban: () => {},
    },
    runs: { liste: [], loading: false, error: null },
    usage: { usage: null, loading: false, error: null },
  };
  return render(<Sidebar {...base} {...extra} />);
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api.projects, "list").mockResolvedValue([project]);
  vi.spyOn(api.chat, "list").mockResolvedValue([
    {
      conversation_id: "conv-abc",
      title: "Explique le pipeline",
      last_activity: "2026-09-29T10:00:00Z",
    },
  ]);
});

describe("Sidebar — panneau Chat (ticket-250)", () => {
  it("liste les conversations du projet dans la colonne", async () => {
    renderSidebar({ chat: { conversationId: "default" } });

    expect(
      await screen.findByText("Explique le pipeline"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Nouvelle conversation" }),
    ).toBeInTheDocument();
  });

  it("remonte l'identifiant de la conversation choisie", async () => {
    const onSelect = vi.fn();
    renderSidebar({ chat: { conversationId: "default", onSelect } });

    const user = userEvent.setup();
    await user.click(await screen.findByText("Explique le pipeline"));

    expect(onSelect).toHaveBeenCalledWith("conv-abc");
  });

  it("invite à choisir un projet quand aucun n'est actif", () => {
    renderSidebar({ projet: { actif: null, onSelect: () => {} } });

    expect(screen.getByText(/Sélectionne un projet/)).toBeInTheDocument();
  });
});

describe("Sidebar — panneau Usage (ticket-250)", () => {
  it("ne montre qu'un résumé, le détail vit au centre", () => {
    renderSidebar({
      panel: "usage",
      usage: {
        usage: {
          total_cost_usd: 1.2345,
          total_tokens: 1000,
          total_runs: 3,
          per_ticket: [],
        },
        loading: false,
        error: null,
      },
    });

    expect(screen.getByText(/\$1\.2345/)).toBeInTheDocument();
    expect(screen.getByText(/détail au centre/)).toBeInTheDocument();
    // Le tableau « Par ticket » de l'ancien UsageDashboard ne doit plus être là.
    expect(screen.queryByText("Par ticket")).not.toBeInTheDocument();
  });
});
