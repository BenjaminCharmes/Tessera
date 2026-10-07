import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import KanbanColumn from "./KanbanColumn";
import type { Ticket, TicketStatus } from "../../types/api";

function makeTicket(n: number, status: TicketStatus = "done"): Ticket {
  const id = `ticket-${String(n).padStart(3, "0")}`;
  return {
    id,
    title: `Ticket Title ${String(n).padStart(3, "0")}`,
    status,
    type: "feat",
    priority: "medium",
    depends_on: [],
    created: "2026-07-13T10:00:00Z",
    agent: "codeur",
    github_issue_url: null,
    pr_number: null,
    body: "",
    project_id: "ide-core",
    file_path: `tickets/done/${id}.md`,
  };
}

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

describe("KanbanColumn — file de tickets (ticket-284)", () => {
  it("affiche le bouton Ajouter à la file sur une carte todo quand onToggleQueue est fourni", () => {
    render(
      <KanbanColumn
        status="todo"
        tickets={[T1]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
        onToggleQueue={vi.fn()}
        selection={[]}
      />,
    );
    expect(
      screen.getByRole("button", { name: "Ajouter à la file" }),
    ).toBeInTheDocument();
  });

  it("appelle onToggleQueue avec l'id du ticket au clic", () => {
    const onToggleQueue = vi.fn();
    render(
      <KanbanColumn
        status="todo"
        tickets={[T1]}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
        onToggleQueue={onToggleQueue}
        selection={[]}
      />,
    );
    screen.getByRole("button", { name: "Ajouter à la file" }).click();
    expect(onToggleQueue).toHaveBeenCalledWith(T1.id);
  });
});

describe("KanbanColumn — limite done/cancelled (ticket-368)", () => {
  const FIFTY_DONE = Array.from({ length: 50 }, (_, i) => makeTicket(i + 1, "done"));
  const FIFTY_TODO = Array.from({ length: 50 }, (_, i) => makeTicket(i + 1, "todo"));

  it("rend 30 cartes sur les 30 numéros les plus élevés pour une colonne done de 50", () => {
    render(
      <KanbanColumn
        status="done"
        tickets={FIFTY_DONE}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    // Les 30 numéros les plus élevés (021–050) sont visibles.
    expect(screen.queryByText("ticket-050")).toBeTruthy();
    expect(screen.queryByText("ticket-021")).toBeTruthy();
    // Les numéros inférieurs (001–020) sont masqués.
    expect(screen.queryByText("ticket-020")).toBeNull();
    expect(screen.queryByText("ticket-001")).toBeNull();
  });

  it("rend les 50 cartes après un clic sur Afficher les 20 autres", () => {
    render(
      <KanbanColumn
        status="done"
        tickets={FIFTY_DONE}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    fireEvent.click(screen.getByRole("button", { name: "Afficher les 20 autres" }));
    // Tous les identifiants de ticket sont désormais dans le DOM.
    expect(screen.queryByText("ticket-001")).toBeTruthy();
    expect(screen.queryByText("ticket-050")).toBeTruthy();
    const allIds = screen.getAllByText(/^ticket-\d{3}$/);
    expect(allIds).toHaveLength(50);
  });

  it("rend les 50 cartes d'une colonne todo sans limitation", () => {
    render(
      <KanbanColumn
        status="todo"
        tickets={FIFTY_TODO}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.queryByText("ticket-001")).toBeTruthy();
    expect(screen.queryByText("ticket-050")).toBeTruthy();
    expect(screen.queryByRole("button", { name: /Afficher les/ })).toBeNull();
  });

  it("affiche le compteur total de la colonne done même quand 30 cartes seulement sont rendues", () => {
    render(
      <KanbanColumn
        status="done"
        tickets={FIFTY_DONE}
        activeTicket={null}
        running={new Set()}
        onSelectTicket={vi.fn()}
        onRunPipeline={vi.fn()}
      />,
    );
    expect(screen.getByText("(50)")).toBeTruthy();
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
