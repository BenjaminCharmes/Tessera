import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import CostView from "./index";

vi.mock("../../lib/api");
import { api } from "../../lib/api";

const ventilation = vi.mocked(api.usage.breakdown);

describe("CostView", () => {
  beforeEach(() => ventilation.mockReset());

  it("dit quel agent consomme, le plus cher en premier", async () => {
    ventilation.mockResolvedValue({
      project_id: "p",
      total_cost_usd: 1.0,
      per_agent: [
        { role: "codeur", total_cost_usd: 0.9, total_tokens: 2200, call_count: 2 },
        { role: "reviewer", total_cost_usd: 0.1, total_tokens: 300, call_count: 1 },
      ],
      per_model: [
        { model: "sonnet", total_cost_usd: 0.9, total_tokens: 2200, call_count: 2 },
      ],
    });

    render(<CostView projectId="p" />);

    expect(await screen.findByText("codeur")).toBeInTheDocument();
    expect(screen.getByText("reviewer")).toBeInTheDocument();
    // « codeur » et « sonnet » pèsent tous deux 90 % : l'assertion doit dire
    // de quelle ventilation elle parle.
    expect(screen.getAllByText(/90 %/)).toHaveLength(2);
  });

  it("montre aussi la ventilation par modele", async () => {
    ventilation.mockResolvedValue({
      project_id: "p",
      total_cost_usd: 0.9,
      per_agent: [],
      per_model: [
        { model: "sonnet", total_cost_usd: 0.9, total_tokens: 2200, call_count: 2 },
      ],
    });

    render(<CostView projectId="p" />);

    expect(await screen.findByText("sonnet")).toBeInTheDocument();
  });

  it("dit qu'il n'y a rien a ventiler plutot que d'afficher des zeros", async () => {
    ventilation.mockResolvedValue({
      project_id: "p", total_cost_usd: 0, per_agent: [], per_model: [],
    });

    render(<CostView projectId="p" />);

    expect(await screen.findByText(/Aucun appel/i)).toBeInTheDocument();
  });
});
