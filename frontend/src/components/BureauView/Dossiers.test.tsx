import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import Dossiers from "./Dossiers";
import { api } from "../../lib/api";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import { _viderCacheResource } from "../../hooks/useResource";
import type { StatutDuRun } from "../../types/api";

function statut(restants: string[]): StatutDuRun {
  return {
    project_id: "ide-core",
    mode: "queue",
    statut: "en cours",
    ticket_courant: "ticket-001",
    approuves: [],
    restants,
    debut: "2026-10-24T10:00:00Z",
    fin: null,
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
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Dossiers", () => {
  it("draws one folder per remaining ticket", async () => {
    vi.spyOn(api.runs, "status").mockResolvedValue(statut(["ticket-002", "ticket-003", "ticket-004"]));

    render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);

    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(3));
    expect(screen.getByRole("list", { name: "Tickets restants : 3" })).toBeInTheDocument();
  });

  it("draws nothing when no ticket remains", async () => {
    const lire = vi.spyOn(api.runs, "status").mockResolvedValue(statut([]));

    const { container } = render(<Dossiers projet="ide-core" runId="run-1" etat={INITIAL} />);

    await waitFor(() => expect(lire).toHaveBeenCalledTimes(1));
    expect(container).toBeEmptyDOMElement();
  });

  it("asks nothing without a run id", () => {
    const lire = vi.spyOn(api.runs, "status");

    const { container } = render(<Dossiers projet="ide-core" runId={null} etat={INITIAL} />);

    expect(lire).not.toHaveBeenCalled();
    expect(container).toBeEmptyDOMElement();
  });

  it("reads the run again on each queue_progress", async () => {
    const lire = vi
      .spyOn(api.runs, "status")
      .mockResolvedValueOnce(statut(["ticket-002", "ticket-003", "ticket-004"]))
      .mockResolvedValueOnce(statut(["ticket-003", "ticket-004"]));

    const { rerender } = render(<Dossiers projet="ide-core" runId="run-1" etat={apresQueueProgress(0)} />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(3));
    expect(lire).toHaveBeenCalledTimes(1);

    rerender(<Dossiers projet="ide-core" runId="run-1" etat={apresQueueProgress(1)} />);

    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(2));
    expect(lire).toHaveBeenCalledTimes(2);
  });

  it("does not read again when the state changes without a queue_progress", async () => {
    const lire = vi.spyOn(api.runs, "status").mockResolvedValue(statut(["ticket-002"]));
    const etat = apresQueueProgress(0);

    const { rerender } = render(<Dossiers projet="ide-core" runId="run-1" etat={etat} />);
    await waitFor(() => expect(screen.getAllByRole("listitem")).toHaveLength(1));
    rerender(<Dossiers projet="ide-core" runId="run-1" etat={{ ...etat }} />);

    expect(lire).toHaveBeenCalledTimes(1);
  });
});
