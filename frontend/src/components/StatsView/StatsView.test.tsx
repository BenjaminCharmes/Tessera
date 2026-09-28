import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import StatsView from "./index";
import type { UsageStats } from "../../types/api";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const stats = vi.mocked(api.usage.stats);

function payload(overrides: Partial<UsageStats> = {}): UsageStats {
  return {
    days: 7,
    project_id: "p",
    since: "2026-09-22",
    until: "2026-09-28",
    totals: {
      runs: 2, calls: 3, input_tokens: 3779, output_tokens: 2028, cache_read_tokens: 0,
      pipeline_cost_usd: 0.8, chat_cost_usd: 0.1, cost_usd: 0.9, call_duration_ms: 90_000,
    },
    daily: Array.from({ length: 7 }, (_, i) => ({
      day: `2026-09-2${2 + i}`,
      runs: i === 6 ? 2 : 0,
      input_tokens: i === 6 ? 3779 : 0,
      output_tokens: i === 6 ? 2028 : 0,
      cost_usd: i === 6 ? 0.9 : 0,
    })),
    per_agent: [
      { key: "codeur", cost_usd: 0.6, tokens: 4000, calls: 2, avg_duration_ms: 40_000 },
      { key: "reviewer", cost_usd: 0.2, tokens: 1800, calls: 1, avg_duration_ms: 10_000 },
    ],
    per_model: [{ key: "sonnet", cost_usd: 0.8, tokens: 5800, calls: 3, avg_duration_ms: 30_000 }],
    per_project: [],
    quality: {
      finished_runs: 2, approval_rate: 0.5, avg_rounds: 1.5, avg_run_duration_ms: 600_000,
      by_status: [{ status: "done", count: 1 }, { status: "blocked", count: 1 }],
    },
    recent_runs: [
      {
        id: "r1", project_id: "p", ticket_id: "ticket-007", started_at: "2026-09-28T08:00:00+00:00",
        finished_at: "2026-09-28T08:10:00+00:00", approved: true, final_status: "done",
        cost_usd: 0.5, input_tokens: 2000, output_tokens: 1000, duration_ms: 600_000,
      },
    ],
    ...overrides,
  };
}

describe("StatsView", () => {
  it("shows the headline figures and every chart for the period", async () => {
    stats.mockResolvedValue(payload());

    render(<StatsView projectId="p" />);

    const tile = (await screen.findByText("Tokens entrants")).parentElement;
    expect(tile).toHaveTextContent("3 779");
    expect(screen.getByText("dont chat 0.10 $")).toBeInTheDocument();
    expect(screen.getByText("Taux d'approbation").parentElement).toHaveTextContent("50 %");
    expect(screen.getByRole("region", { name: "Dépense par jour" })).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Tokens par jour" })).toBeInTheDocument();
    const runs = screen.getByRole("region", { name: "Runs récents" });
    expect(within(runs).getByText("ticket-007")).toBeInTheDocument();
    // Un seul projet : le ventiler par projet n'apprendrait rien.
    expect(screen.queryByRole("region", { name: "Dépense par projet" })).toBeNull();
  });

  it("asks for another period when a period button is pressed", async () => {
    stats.mockResolvedValue(payload());
    render(<StatsView projectId={null} />);
    await screen.findByText("Tokens entrants");

    fireEvent.click(screen.getByRole("button", { name: "90 j" }));

    expect(stats).toHaveBeenLastCalledWith(90, null);
    expect(screen.getByRole("button", { name: "90 j" })).toHaveAttribute("aria-pressed", "true");
  });

  it("says the period is empty rather than drawing flat charts", async () => {
    stats.mockResolvedValue(
      payload({
        totals: {
          runs: 0, calls: 0, input_tokens: 0, output_tokens: 0, cache_read_tokens: 0,
          pipeline_cost_usd: 0, chat_cost_usd: 0, cost_usd: 0, call_duration_ms: 0,
        },
        daily: [{ day: "2026-09-28", runs: 0, input_tokens: 0, output_tokens: 0, cost_usd: 0 }],
        per_agent: [],
        per_model: [],
        quality: { finished_runs: 0, approval_rate: null, avg_rounds: null, avg_run_duration_ms: null, by_status: [] },
        recent_runs: [],
      }),
    );

    render(<StatsView projectId="p" />);

    expect(await screen.findByText(/Aucun run sur les 7 derniers jours/)).toBeInTheDocument();
    expect(screen.getByText("Aucune dépense sur la période.")).toBeInTheDocument();
  });

  it("says the statistics are unavailable when the request fails", async () => {
    stats.mockImplementation(() => Promise.reject(new Error("down")));

    render(<StatsView projectId="p" />);

    expect(await screen.findByText("Statistiques indisponibles.")).toBeInTheDocument();
  });
});
