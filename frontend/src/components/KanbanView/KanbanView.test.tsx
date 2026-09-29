import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import KanbanView from "./index";
import type { TicketStatus, TicketUnreadable } from "../../types/api";

const EMPTY_BY_STATUS: Record<TicketStatus, never[]> = {
  todo: [],
  "in-progress": [],
  "in-review": [],
  done: [],
  blocked: [],
  cancelled: [],
};

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
