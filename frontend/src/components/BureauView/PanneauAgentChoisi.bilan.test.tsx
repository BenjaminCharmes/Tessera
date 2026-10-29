import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import BureauView from "./index";
import type { ProjetDuBureau } from "./index";
import { api } from "../../lib/api";
import { firstTryCount } from "../../lib/bureau/weekEmployee";
import { apiQuota } from "../../lib/quota";
import { apiVentilation } from "../../lib/ventilation";
import type { VentilationDuProjet } from "../../lib/ventilation";
import type { PipelineRun, RunActif, UsageStats } from "../../types/api";
import { T0, etatEnCodage, nomme } from "./etatsDeTest";

const MAINTENANT = T0 + 5_000;

const RUN: RunActif = {
  run_id: "run-1",
  project_id: "ide-core",
  mode: "ticket",
  ticket_id: "ticket-001",
  etape: null,
  agent: "codeur",
  tour: 1,
  tokens_entree: 0,
  tokens_sortie: 0,
  cout_usd: 0,
  verdict: null,
  demarre_a: "2026-10-23T09:59:00.000Z",
};

function runPasse(id: string, ticket: string, debut: string, tours: number, approuve: boolean): PipelineRun {
  return {
    id,
    ticket_id: ticket,
    started_at: debut,
    finished_at: null,
    rounds: tours,
    approved: approuve,
    final_status: null,
    total_cost_usd: 0,
  };
}

/** Quatre runs de la semaine (deux approuvés du premier coup) et un run vieux de trois semaines. */
const RUNS: PipelineRun[] = [
  runPasse("a", "ticket-010", "2026-10-22T08:00:00.000Z", 1, true),
  runPasse("b", "ticket-011", "2026-10-21T08:00:00.000Z", 1, true),
  runPasse("c", "ticket-012", "2026-10-20T08:00:00.000Z", 2, true),
  runPasse("d", "ticket-013", "2026-10-19T08:00:00.000Z", 3, false),
  runPasse("e", "ticket-001", "2026-10-02T08:00:00.000Z", 1, true),
];

const VENTILATION: VentilationDuProjet = {
  per_agent: [
    { role: "codeur", total_cost_usd: 12.5, total_tokens: 1000, call_count: 20 },
    { role: "reviewer", total_cost_usd: 3.1, total_tokens: 400, call_count: 8 },
  ],
};

const CANAL = { envoyer: vi.fn(), son: { actif: false, regler: vi.fn() } };

async function choisirLeCodeur(): Promise<HTMLElement> {
  const projets: ProjetDuBureau[] = [{ nom: "ide-core", etat: etatEnCodage(), runId: "run-1", run: RUN }];
  render(<BureauView projets={projets} {...CANAL} onOuvrir={vi.fn()} />);
  fireEvent.click(screen.getByRole("button", { name: nomme("Codeur, travaille", "codeur") }));
  // Les lectures du bilan se résolvent hors du clic : on laisse passer leurs promesses.
  await act(async () => {
    await vi.advanceTimersByTimeAsync(0);
  });
  return screen.getByRole("complementary", { name: "Agent choisi" });
}

describe("PanneauAgentChoisi, bilan", () => {
  beforeEach(() => {
    vi.spyOn(api.services, "list").mockResolvedValue([]);
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
    vi.spyOn(api.usage, "stats").mockResolvedValue({ daily: [] } as unknown as UsageStats);
    vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows: {} });
    vi.spyOn(api.runs, "list").mockResolvedValue(RUNS);
    vi.spyOn(apiVentilation, "parProjet").mockResolvedValue(VENTILATION);
    vi.useFakeTimers();
    vi.setSystemTime(MAINTENANT);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("shows the week's runs and those approved on the first round, counted by firstTryCount", async () => {
    const panneau = await choisirLeCodeur();

    const attendu = firstTryCount(RUNS, MAINTENANT);
    expect(attendu).toBe(2);
    const dans = within(within(panneau).getByRole("region", { name: "Bilan" }));
    expect(dans.getByText("Runs de la semaine")).toBeInTheDocument();
    expect(dans.getByText(`4, dont ${attendu} approuvés au premier tour`)).toBeInTheDocument();
    expect(api.runs.list).toHaveBeenCalledWith("ide-core", 100);
  });

  it("shows the cost the chosen role has accumulated on the project", async () => {
    const panneau = await choisirLeCodeur();

    const dans = within(panneau);
    expect(dans.getByText("Coût cumulé")).toBeInTheDocument();
    expect(dans.getByText("12,50 $")).toBeInTheDocument();
    expect(dans.queryByText("3,10 $")).toBeNull();
    expect(apiVentilation.parProjet).toHaveBeenCalledWith("ide-core");
  });

  it("drops the cost line, not the rest of the panel, when the breakdown cannot be read", async () => {
    vi.spyOn(apiVentilation, "parProjet").mockRejectedValue(new Error("500"));

    const panneau = await choisirLeCodeur();

    const dans = within(panneau);
    expect(dans.queryByText("Coût cumulé")).toBeNull();
    expect(dans.getByText("Runs de la semaine")).toBeInTheDocument();
    expect(dans.getByText("ticket-001")).toBeInTheDocument();
    expect(dans.getByRole("button", { name: "Suivre le fil" })).toBeInTheDocument();
  });

  it("drops the runs line when the runs cannot be read, and keeps the cost", async () => {
    vi.spyOn(api.runs, "list").mockRejectedValue(new Error("500"));

    const panneau = await choisirLeCodeur();

    expect(within(panneau).queryByText("Runs de la semaine")).toBeNull();
    expect(within(panneau).getByText("12,50 $")).toBeInTheDocument();
  });

  it("draws no Bilan section when neither reading gives anything", async () => {
    vi.spyOn(api.runs, "list").mockResolvedValue([]);
    vi.spyOn(apiVentilation, "parProjet").mockResolvedValue({ per_agent: [] });

    const panneau = await choisirLeCodeur();

    expect(within(panneau).queryByRole("region", { name: "Bilan" })).toBeNull();
    expect(within(panneau).queryByText(/^0/)).toBeNull();
  });
});
