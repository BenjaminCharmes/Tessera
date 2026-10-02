import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import KanbanView from "./index";
import type { Ticket, TicketStatus, TicketUnreadable } from "../../types/api";

const EMPTY_BY_STATUS: Record<TicketStatus, never[]> = {
  todo: [],
  "in-progress": [],
  "in-review": [],
  done: [],
  blocked: [],
  cancelled: [],
};

const TODO_TICKET: Ticket = {
  id: "ticket-001",
  title: "Fix login",
  status: "todo",
  type: "feat",
  priority: "high",
  depends_on: [],
  created: "2026-07-13T10:00:00Z",
  agent: "codeur",
  github_issue_url: null,
  pr_number: null,
  body: "",
  project_id: "ide-core",
  file_path: "tickets/todo/ticket-001.md",
};

describe("KanbanView — file de tickets (ticket-284)", () => {
  const BY_STATUS_WITH_TODO: Record<TicketStatus, Ticket[]> = {
    ...EMPTY_BY_STATUS,
    todo: [TODO_TICKET],
  };

  it("n'affiche pas QueueBar quand la sélection est vide", () => {
    render(
      <KanbanView
        byStatus={EMPTY_BY_STATUS}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
        onToggleQueue={vi.fn()}
        onRunQueue={vi.fn()}
        onClearQueue={vi.fn()}
        selection={[]}
      />,
    );
    expect(screen.queryByText("Lancer la file")).toBeNull();
  });

  it("affiche QueueBar quand la sélection contient au moins un ticket", () => {
    render(
      <KanbanView
        byStatus={EMPTY_BY_STATUS}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
        onToggleQueue={vi.fn()}
        onRunQueue={vi.fn()}
        onClearQueue={vi.fn()}
        selection={["ticket-001"]}
      />,
    );
    expect(screen.getByText("Lancer la file")).toBeTruthy();
    expect(screen.getByText("1 ticket en file")).toBeTruthy();
  });

  it("un ticket ajouté depuis la Vue Tableau figure dans la sélection transmise à la sidebar", () => {
    const onToggleQueue = vi.fn();
    render(
      <KanbanView
        byStatus={BY_STATUS_WITH_TODO}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
        onToggleQueue={onToggleQueue}
        onRunQueue={vi.fn()}
        onClearQueue={vi.fn()}
        selection={[]}
      />,
    );
    screen.getByRole("button", { name: "Ajouter à la file" }).click();
    expect(onToggleQueue).toHaveBeenCalledWith("ticket-001");
  });
});

describe("KanbanView — tickets illisibles (ticket-210)", () => {
  it("affiche rien quand il n'y a pas d'illisibles", () => {
    render(
      <KanbanView
        byStatus={EMPTY_BY_STATUS}
        activeTicket={null}
        running={new Set()}
        unreadable={[]}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("kanban-unreadable")).toBeNull();
  });

  it("affiche la section illisibles quand un fichier ne peut pas être parsé", () => {
    const bad: TicketUnreadable = {
      file_path: "/workspace/mon-projet/tickets/todo/ticket-099-x.md",
      error: "1 validation error for Ticket\ntype\n  Field required",
    };
    render(
      <KanbanView
        byStatus={EMPTY_BY_STATUS}
        activeTicket={null}
        running={new Set()}
        unreadable={[bad]}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.getByTestId("kanban-unreadable")).toBeTruthy();
    expect(screen.getByText("1 fichier illisible")).toBeTruthy();
    const item = screen.getByTestId("kanban-unreadable-item");
    expect(item).toBeTruthy();
    // Le nom de fichier court est affiché
    expect(item.textContent).toContain("ticket-099-x.md");
    // L'erreur est affichée (au moins partiellement)
    expect(item.textContent).toContain("validation error");
  });

  it("affiche le pluriel correctement pour plusieurs illisibles", () => {
    const bads: TicketUnreadable[] = [
      { file_path: "/tmp/ticket-001.md", error: "missing type" },
      { file_path: "/tmp/ticket-002.md", error: "missing agent" },
    ];
    render(
      <KanbanView
        byStatus={EMPTY_BY_STATUS}
        activeTicket={null}
        running={new Set()}
        unreadable={bads}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.getByText("2 fichiers illisibles")).toBeTruthy();
    expect(screen.getAllByTestId("kanban-unreadable-item")).toHaveLength(2);
  });
});
