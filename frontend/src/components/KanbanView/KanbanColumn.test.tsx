import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import KanbanColumn from "./KanbanColumn";
import type { Ticket } from "../../types/api";

const T1: Ticket = {
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

const T2: Ticket = {
  id: "ticket-002",
  title: "Add tests",
  status: "in-progress",
  type: "test",
  priority: "medium",
  depends_on: [],
  created: "2026-07-13T10:00:00Z",
  agent: "codeur",
  github_issue_url: null,
  pr_number: null,
  body: "",
  project_id: "ide-core",
  file_path: "tickets/todo/ticket-002.md",
};

describe("KanbanColumn", () => {
  it("renders status label and ticket count", () => {
    render(
      <KanbanColumn
        status="todo"
        tickets={[T1]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.getByText("TODO")).toBeTruthy();
    expect(screen.getByText("(1)")).toBeTruthy();
  });

  it("renders IN PROGRESS label", () => {
    render(
      <KanbanColumn
        status="in-progress"
        tickets={[]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.getByText("IN PROGRESS")).toBeTruthy();
  });

  it("shows empty placeholder when no tickets", () => {
    render(
      <KanbanColumn
        status="done"
        tickets={[]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.getByText("—")).toBeTruthy();
  });

  it("renders a TicketCard for each ticket", () => {
    render(
      <KanbanColumn
        status="todo"
        tickets={[T1, T2]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.getByText("Fix login")).toBeTruthy();
    expect(screen.getByText("Add tests")).toBeTruthy();
    expect(screen.getByText("(2)")).toBeTruthy();
  });

  it("marks the active ticket", () => {
    render(
      <KanbanColumn
        status="todo"
        tickets={[T1]}
        activeTicket={T1}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.getByText("Fix login")).toBeTruthy();
  });
});
