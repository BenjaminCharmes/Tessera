import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { INITIAL } from "../../hooks/streamState";
import { _viderCacheResource } from "../../hooks/useResource";
import { api } from "../../lib/api";
import { statutsDuRun } from "../../lib/statutDuRun";
import type { RunActif } from "../../types/api";
import { T0 } from "./etatsDeTest";
import Piece from "./Piece";

const RUN: RunActif = {
  run_id: "run-1",
  project_id: "ide-core",
  mode: "queue",
  ticket_id: "ticket-001",
  etape: "codage",
  agent: "codeur",
  tour: 1,
  tokens_entree: 0,
  tokens_sortie: 0,
  cout_usd: 0,
  verdict: null,
  demarre_a: "2026-10-23T10:00:00.000Z",
};

beforeEach(() => {
  _viderCacheResource();
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
  vi.spyOn(api.tickets, "list").mockResolvedValue({
    tickets: [],
    unreadable: [],
  });
  vi.spyOn(statutsDuRun, "lire").mockResolvedValue({
    project_id: "ide-core",
    mode: "queue",
    statut: "en cours",
    ticket_courant: "ticket-001",
    approuves: [],
    restants: ["ticket-002", "ticket-003"],
    debut: "2026-10-23T10:00:00Z",
    fin: null,
  });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Piece door", () => {
  it("names the project on the door and hands it to onOpenProject on click", () => {
    const onOpenProject = vi.fn();
    render(
      <Piece
        projet="ide-core"
        etat={INITIAL}
        maintenant={T0}
        onOpenProject={onOpenProject}
      />,
    );

    fireEvent.click(
      screen.getByRole("button", { name: "Ouvrir le projet ide-core" }),
    );

    expect(onOpenProject).toHaveBeenCalledTimes(1);
    expect(onOpenProject).toHaveBeenCalledWith("ide-core");
  });

  it("draws no door button when nobody listens", () => {
    render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />);

    expect(
      screen.queryByRole("button", { name: /Ouvrir le projet/ }),
    ).toBeNull();
  });
});

describe("Piece pile of folders", () => {
  it("opens the project's tickets, as the door does", async () => {
    const onOpenProject = vi.fn();
    render(
      <Piece
        projet="ide-core"
        etat={INITIAL}
        maintenant={T0}
        runId="run-1"
        run={RUN}
        onOpenProject={onOpenProject}
      />,
    );

    fireEvent.click(
      await screen.findByRole("button", { name: "Tickets restants : 2" }),
    );

    expect(onOpenProject).toHaveBeenCalledWith("ide-core");
  });

  it("opens the tickets from the keyboard", async () => {
    const onOpenProject = vi.fn();
    render(
      <Piece
        projet="ide-core"
        etat={INITIAL}
        maintenant={T0}
        runId="run-1"
        run={RUN}
        onOpenProject={onOpenProject}
      />,
    );

    const pile = await screen.findByRole("button", {
      name: "Tickets restants : 2",
    });
    fireEvent.keyDown(pile, { key: "Enter" });

    await waitFor(() => expect(onOpenProject).toHaveBeenCalledWith("ide-core"));
  });

  it("stays a plain group when no project can be opened", async () => {
    render(
      <Piece
        projet="ide-core"
        etat={INITIAL}
        maintenant={T0}
        runId="run-1"
        run={RUN}
      />,
    );

    expect(
      await screen.findByRole("group", { name: "Tickets restants : 2" }),
    ).toBeInTheDocument();
  });
});
