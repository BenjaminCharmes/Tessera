import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import RunCard from "./RunCard";
import { INITIAL } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";

function run(over: Partial<RunActif> = {}): RunActif {
  return {
    run_id: "r1",
    project_id: "demineur",
    mode: "queue",
    ticket_id: "ticket-004",
    etape: null,
    agent: null,
    tour: 0,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    question: null,
    file_index: 2,
    file_total: 3,
    file_restants: ["ticket-005"],
    demarre_a: new Date().toISOString(),
    ...over,
  };
}

function rendre(r: RunActif) {
  return render(
    <RunCard run={r} etat={INITIAL} selectionne={false} onSelect={vi.fn()} />,
  );
}

describe("RunCard — où en est une file (ticket-172)", () => {
  it("affiche l'avancement de la file", () => {
    // La carte disait « file » sans dire s'il en restait deux derrière.
    rendre(run());

    expect(screen.getByText(/2\s*\/\s*3/)).toBeInTheDocument();
  });

  it("nomme les tickets qui restent", () => {
    rendre(run({ file_restants: ["ticket-005", "ticket-006"] }));

    expect(screen.getByText(/ticket-005/)).toBeInTheDocument();
    expect(screen.getByText(/ticket-006/)).toBeInTheDocument();
  });

  it("un run unique n'affiche aucun avancement", () => {
    rendre(
      run({ mode: "single", file_index: 0, file_total: 0, file_restants: [] }),
    );

    expect(screen.queryByText(/\d+\s*\/\s*\d+/)).toBeNull();
  });
});

describe("RunCard — la file se déplie (ticket-179)", () => {
  it("montre les tickets faits quand on déplie", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    rendre(
      run({
        file_faits: ["ticket-001", "ticket-002"],
        file_restants: ["ticket-005"],
      }),
    );

    await userEvent.click(screen.getByText("la file"));

    expect(screen.getByText(/fait · ticket-001/)).toBeInTheDocument();
    expect(screen.getByText(/ensuite · ticket-005/)).toBeInTheDocument();
  });

  it("est repliée par défaut", () => {
    rendre(run({ file_faits: ["ticket-001"] }));

    expect(screen.getByText("la file").closest("details")?.open).toBe(false);
  });

  it("un run unique n'affiche aucune file", () => {
    rendre(
      run({ mode: "single", file_total: 0, file_restants: [], file_faits: [] }),
    );

    expect(screen.queryByText("la file")).toBeNull();
  });
});
