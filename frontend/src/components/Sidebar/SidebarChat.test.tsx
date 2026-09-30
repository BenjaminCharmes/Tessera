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
    usage: {
      usage: null,
      loading: false,
      error: null,
      days: 30,
      setDays: () => {},
      portee: "tous",
      setPortee: () => {},
      projetActifId: null,
    },
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

describe("Sidebar — panneau Usage (ticket-253)", () => {
  beforeEach(() => {
    vi.spyOn(api.orchestrator, "limits").mockResolvedValue({
      run_max_budget_usd: 0,
      llm_max_budget_usd: 0,
    });
  });

  it("montre les boutons de période dans la colonne", async () => {
    renderSidebar({
      panel: "usage",
      usage: {
        usage: null,
        loading: false,
        error: null,
        days: 30,
        setDays: () => {},
        portee: "tous",
        setPortee: () => {},
        projetActifId: null,
      },
    });

    expect(screen.getByRole("group", { name: "Période" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "7 j" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "30 j" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "90 j" })).toBeInTheDocument();
  });

  it("désactive le bouton Ce projet quand aucun projet n'est actif", () => {
    renderSidebar({
      panel: "usage",
      usage: {
        usage: null,
        loading: false,
        error: null,
        days: 30,
        setDays: () => {},
        portee: "tous",
        setPortee: () => {},
        projetActifId: null,
      },
    });

    expect(screen.getByRole("button", { name: "Ce projet" })).toBeDisabled();
  });

  it("active le bouton Ce projet quand un projet est actif", () => {
    renderSidebar({
      panel: "usage",
      usage: {
        usage: null,
        loading: false,
        error: null,
        days: 30,
        setDays: () => {},
        portee: "projet",
        setPortee: () => {},
        projetActifId: "ide-core",
      },
    });

    expect(screen.getByRole("button", { name: "Ce projet" })).not.toBeDisabled();
    expect(screen.getByRole("button", { name: "Ce projet" })).toHaveAttribute("aria-pressed", "true");
  });

  it("affiche aucun plafond quand les limites sont à zéro", async () => {
    renderSidebar({
      panel: "usage",
      usage: {
        usage: null,
        loading: false,
        error: null,
        days: 30,
        setDays: () => {},
        portee: "tous",
        setPortee: () => {},
        projetActifId: null,
      },
    });

    expect(await screen.findAllByText("aucun plafond")).toHaveLength(2);
  });
});
