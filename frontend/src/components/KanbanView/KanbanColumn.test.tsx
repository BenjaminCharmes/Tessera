import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
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

describe("KanbanColumn — infobulle d'arrêt (ticket-218)", () => {
  it("transmet l'arrêt au badge de statut d'un ticket bloqué", () => {
    const blocked: typeof T1 = {
      ...T1,
      id: "ticket-blocked",
      title: "Un ticket bloqué",
      status: "blocked",
    };
    render(
      <KanbanColumn
        status="blocked"
        tickets={[blocked]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
        blockedArrets={{ "ticket-blocked": "Reached maximum number of turns (30)" }}
      />,
    );
    const badge = screen.getByText("blocked");
    expect(badge).toHaveAttribute("title", "Reached maximum number of turns (30)");
  });
});

describe("KanbanColumn — glisser-déposer (ticket-194)", () => {
  function deposer(statutDepuis: string, id = "ticket-001") {
    return {
      dataTransfer: {
        types: ["application/x-tessera-ticket"],
        getData: () => JSON.stringify({ id, status: statutDepuis }),
      },
    };
  }

  it("change le statut d'un ticket depose sur la colonne", () => {
    const onChangeStatus = vi.fn();
    render(
      <KanbanColumn
        status="todo"
        tickets={[]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
        onChangeStatus={onChangeStatus}
      />,
    );
    fireEvent.drop(screen.getByTestId("colonne-todo"), deposer("blocked"));
    expect(onChangeStatus).toHaveBeenCalledWith("ticket-001", "todo");
  });

  it("refuse un depot vers un statut tenu par le pipeline", () => {
    const onChangeStatus = vi.fn();
    render(
      <KanbanColumn
        status="in-progress"
        tickets={[]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
        onChangeStatus={onChangeStatus}
      />,
    );
    fireEvent.drop(screen.getByTestId("colonne-in-progress"), deposer("todo"));
    expect(onChangeStatus).not.toHaveBeenCalled();
  });

  it("ignore un depot sans onChangeStatus", () => {
    render(
      <KanbanColumn
        status="todo"
        tickets={[]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    fireEvent.drop(screen.getByTestId("colonne-todo"), deposer("blocked"));
  });
});
