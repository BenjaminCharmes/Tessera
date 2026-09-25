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
