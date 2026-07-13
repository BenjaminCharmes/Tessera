import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import UsageDashboard from "./UsageDashboard";
import type { ProjectUsage } from "../../types/api";

const EMPTY_USAGE: ProjectUsage = {
  total_cost_usd: 0,
  total_tokens: 0,
  total_runs: 0,
  per_ticket: [],
};

const USAGE: ProjectUsage = {
  total_cost_usd: 0.0375,
  total_tokens: 12500,
  total_runs: 3,
  per_ticket: [
    {
      ticket_id: "ticket-001",
      total_cost_usd: 0.025,
      input_tokens: 5000,
      output_tokens: 2000,
      cache_read_tokens: 500,
      call_count: 2,
    },
    {
      ticket_id: "ticket-002",
      total_cost_usd: 0.0125,
      input_tokens: 3000,
      output_tokens: 1500,
      cache_read_tokens: 500,
      call_count: 1,
    },
  ],
};

describe("UsageDashboard", () => {
  it("affiche un spinner de chargement", () => {
    render(
      <UsageDashboard
        usage={null}
        loading={true}
        error={null}
        onRefresh={() => {}}
      />,
    );
    expect(screen.getByText(/chargement/i)).toBeTruthy();
  });

  it("affiche une erreur", () => {
    render(
      <UsageDashboard
        usage={null}
        loading={false}
        error="Erreur réseau"
        onRefresh={() => {}}
      />,
    );
    expect(screen.getByText("Erreur réseau")).toBeTruthy();
  });

  it("affiche l'empty state si aucun run", () => {
    render(
      <UsageDashboard
        usage={EMPTY_USAGE}
        loading={false}
        error={null}
        onRefresh={() => {}}
      />,
    );
    expect(screen.getByText(/aucun pipeline/i)).toBeTruthy();
  });

  it("affiche le résumé global", () => {
    render(
      <UsageDashboard
        usage={USAGE}
        loading={false}
        error={null}
        onRefresh={() => {}}
      />,
    );
    expect(screen.getByText("3")).toBeTruthy(); // total_runs
    expect(screen.getByText("$0.0375")).toBeTruthy(); // total_cost
  });

  it("affiche les tickets par coût décroissant", () => {
    render(
      <UsageDashboard
        usage={USAGE}
        loading={false}
        error={null}
        onRefresh={() => {}}
      />,
    );
    const rows = screen.getAllByText(/ticket-00\d/);
    expect(rows[0].textContent).toBe("ticket-001");
    expect(rows[1].textContent).toBe("ticket-002");
  });

  it("appelle onRefresh au clic sur le bouton", () => {
    const onRefresh = vi.fn();
    render(
      <UsageDashboard
        usage={USAGE}
        loading={false}
        error={null}
        onRefresh={onRefresh}
      />,
    );
    fireEvent.click(screen.getByTitle("Rafraîchir"));
    expect(onRefresh).toHaveBeenCalledOnce();
  });
});
