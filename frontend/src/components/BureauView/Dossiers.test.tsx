import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, waitFor, within } from "@testing-library/react";
import Dossiers from "./Dossiers";
import { api } from "../../lib/api";
import type { Ticket } from "../../types/api";
import { statutsDuRun } from "../../lib/statutDuRun";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import { _viderCacheResource } from "../../hooks/useResource";
import type { StatutDuRun } from "../../lib/statutDuRun";
import { statutDuRun } from "../../test/contrat/exemples";

function statut(restants: string[]): StatutDuRun {
  return statutDuRun({
    project_id: "ide-core",
    mode: "queue",
    statut: "en cours",
    ticket_courant: "ticket-001",
    restants,
    debut: "2026-10-24T10:00:00Z",
  });
}

function ids(n: number): string[] {
  return Array.from({ length: n }, (_, i) => `ticket-${String(i + 1).padStart(3, "0")}`);
}

function ticket(id: string, title: string): Ticket {
  return {
    id,
    title,
    type: "feat",
    status: "todo",
    priority: "medium",
    agent: "codeur",
    depends_on: [],
    created: "2026-10-26",
    github_issue_url: null,
    pr_number: null,
    body: "",
    project_id: "ide-core",
    file_path: `/tmp/${id}.md`,
  };
}

function apresQueueProgress(index: number) {
  return applyEvent(INITIAL, {
    type: "queue_progress",
    agent: null,
    ticket_id: "ticket-001",
    data: { index, total: 4 },
    timestamp: "2026-10-24T10:00:00.000Z",
  });
}

beforeEach(() => {
  _viderCacheResource();
  vi.spyOn(api.tickets, "list").mockResolvedValue({ tickets: [], unreadable: [] });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Dossiers", () => {
  it("draws a single pile of three folders and the count for fifteen tickets", async () => {
    vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut(ids(15)));

    const { container } = render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);

    await waitFor(() => expect(screen.getByText("15")).toBeInTheDocument());
    expect(container.querySelectorAll('[data-sprite="dossier"]')).toHaveLength(3);
    expect(screen.getByRole("group", { name: "Tickets restants : 15" })).toBeInTheDocument();
  });

  it("draws as many folders as tickets below three", async () => {
    vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut(ids(2)));

    const { container } = render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);

    await waitFor(() => expect(screen.getByText("2")).toBeInTheDocument());
    expect(container.querySelectorAll('[data-sprite="dossier"]')).toHaveLength(2);
  });

  it("lists identifier and title of each ticket in queue order on focus", async () => {
    vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut(["ticket-003", "ticket-002", "ticket-009"]));
    vi.spyOn(api.tickets, "list").mockResolvedValue({
      tickets: [ticket("ticket-002", "Second title"), ticket("ticket-003", "Third title")],
      unreadable: [],
    });

    render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);
    const pile = await screen.findByRole("group", { name: "Tickets restants : 3" });
    await waitFor(() => expect(api.tickets.list).toHaveBeenCalled());
    await act(async () => {});
    act(() => pile.focus());

    const lignes = within(screen.getByRole("tooltip")).getAllByRole("listitem");
    expect(lignes.map((li) => li.textContent)).toEqual([
      "ticket-003 — Third title",
      "ticket-002 — Second title",
      "ticket-009",
    ]);
  });

  it("shows ten tickets then the number of others beyond ten", async () => {
    vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut(ids(15)));

    render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);
    const pile = await screen.findByRole("group", { name: "Tickets restants : 15" });
    act(() => pile.focus());

    expect(within(screen.getByRole("tooltip")).getAllByRole("listitem")).toHaveLength(10);
    expect(screen.getByText("et 5 autres")).toBeInTheDocument();
  });

  it("writes the number of remaining tickets on a badge of the pile", async () => {
    vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut(ids(13)));

    render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);

    expect(await screen.findByText("13")).toBeInTheDocument();
  });

  it("renders the tooltip in document.body, outside the room that clips its overflow", async () => {
    vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut(ids(13)));

    render(
      <section aria-label="ide-core" className="overflow-hidden">
        <Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />
      </section>,
    );
    const pile = await screen.findByRole("group", { name: "Tickets restants : 13" });
    act(() => pile.focus());

    const infobulle = screen.getByRole("tooltip");
    expect(screen.getByRole("region", { name: "ide-core" })).not.toContainElement(infobulle);
    expect(infobulle.parentElement).toBe(document.body);
    expect(infobulle.className).toContain("fixed");
  });

  it("hides the tooltip when the pile loses focus", async () => {
    vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut(ids(2)));

    render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);
    const pile = await screen.findByRole("group", { name: "Tickets restants : 2" });
    act(() => pile.focus());
    expect(screen.getByRole("tooltip")).toBeInTheDocument();
    act(() => pile.blur());

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("draws nothing when no ticket remains", async () => {
    const lire = vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut([]));

    const { container } = render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);

    await waitFor(() => expect(lire).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  it("asks nothing without a run id", () => {
    const lire = vi.spyOn(statutsDuRun, "lire");

    const { container } = render(<Dossiers projet="ide-core" runId={null} etat={INITIAL} />);

    expect(lire).not.toHaveBeenCalled();
    expect(container).toBeEmptyDOMElement();
  });

  it("reads the run again on each queue_progress", async () => {
    const lire = vi
      .spyOn(statutsDuRun, "lire")
      .mockResolvedValueOnce(statut(["ticket-002", "ticket-003", "ticket-004"]))
      .mockResolvedValueOnce(statut(["ticket-003", "ticket-004"]));

    const { rerender } = render(<Dossiers projet="ide-core" runId="run-1" etat={apresQueueProgress(0)} />);
    await waitFor(() => expect(screen.getByText("3")).toBeInTheDocument());
    expect(lire).toHaveBeenCalledTimes(1);

    rerender(<Dossiers projet="ide-core" runId="run-1" etat={apresQueueProgress(1)} />);

    await waitFor(() => expect(screen.getByText("2")).toBeInTheDocument());
    expect(lire).toHaveBeenCalledTimes(2);
  });

  it("does not read again when the state changes without a queue_progress", async () => {
    const lire = vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut(["ticket-002"]));
    const etat = apresQueueProgress(0);

    const { rerender } = render(<Dossiers projet="ide-core" runId="run-1" etat={etat} />);
    await waitFor(() => expect(screen.getByText("1")).toBeInTheDocument());
    rerender(<Dossiers projet="ide-core" runId="run-1" etat={{ ...etat }} />);

    expect(lire).toHaveBeenCalledTimes(1);
  });

  it("reads the run again every 30 seconds while it lives", async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    try {
      const lire = vi.spyOn(statutsDuRun, "lire").mockResolvedValue(statut(["ticket-002"]));
      render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);
      await waitFor(() => expect(lire).toHaveBeenCalledTimes(1));

      await act(async () => {
        await vi.advanceTimersByTimeAsync(30_000);
      });

      await waitFor(() => expect(lire).toHaveBeenCalledTimes(2));
    } finally {
      vi.useRealTimers();
    }
  });
});
