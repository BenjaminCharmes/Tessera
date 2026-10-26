import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import TableauDuJour from "./TableauDuJour";
import BureauView from "./index";
import { api } from "../../lib/api";
import { apiQuota } from "../../lib/quota";
import type { QuotaWindowReading, QuotaWindows } from "../../lib/quota";
import { heureDeReprise } from "../../lib/bureau/heureDeReprise";
import { _viderCacheResource } from "../../hooks/useResource";
import { applyEvent } from "../../hooks/streamState";
import { DERNIER, etatEnCodage } from "./etatsDeTest";
import type { UsageStats } from "../../types/api";

const MAINTENANT = new Date(2026, 9, 26, 10, 0).getTime();

function stats(couts: number[]): UsageStats {
  const daily = couts.map((cost_usd, i) => ({
    day: `2026-10-${20 + i}`,
    runs: 0,
    input_tokens: 0,
    output_tokens: 0,
    cost_usd,
  }));
  // Seul `daily` compte ici : le reste de la charge utile n'est pas lu par le tableau.
  return { daily } as unknown as UsageStats;
}

function lecture(utilization: number, resets_at: string | null): QuotaWindowReading {
  return { status: "allowed", utilization, resets_at, observed_at: DERNIER };
}

function simuler(couts: number[], windows: QuotaWindows["windows"] = {}) {
  return {
    stats: vi.spyOn(api.usage, "stats").mockResolvedValue(stats(couts)),
    quota: vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows }),
  };
}

beforeEach(() => {
  _viderCacheResource();
});
afterEach(() => {
  vi.restoreAllMocks();
});

describe("TableauDuJour", () => {
  it("shows the cost of the last point of daily", async () => {
    const { stats: espion } = simuler([1.5, 9, 3.456]);
    render(<TableauDuJour maintenant={MAINTENANT} signalRunsClos={0} />);

    expect(await screen.findByText("$3.46")).toBeInTheDocument();
    expect(espion).toHaveBeenCalledWith(7, null);
  });

  it("shows 0 for an empty daily series, without an error", async () => {
    simuler([]);
    render(<TableauDuJour maintenant={MAINTENANT} signalRunsClos={0} />);

    expect(await screen.findByText("$0.00")).toBeInTheDocument();
    expect(screen.queryByText("inconnue")).not.toBeInTheDocument();
  });

  it("shows the cost as unknown when the statistics cannot be read", async () => {
    vi.spyOn(api.usage, "stats").mockRejectedValue(new Error("down"));
    vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows: {} });
    render(<TableauDuJour maintenant={MAINTENANT} signalRunsClos={0} />);

    expect(await screen.findByText("inconnue")).toBeInTheDocument();
  });

  it("shows an absent window as unknown, with no progress bar", async () => {
    const { quota } = simuler([2]);
    render(<TableauDuJour maintenant={MAINTENANT} signalRunsClos={0} />);
    await waitFor(() => expect(quota).toHaveBeenCalled());
    await screen.findByText("$2.00");

    expect(screen.getAllByText("inconnu")).toHaveLength(2);
    expect(screen.queryByRole("progressbar")).not.toBeInTheDocument();
  });

  it("shows only the unknown window as unknown when the other one is read", async () => {
    simuler([2], { five_hour: lecture(0.42, null) });
    render(<TableauDuJour maintenant={MAINTENANT} signalRunsClos={0} />);

    expect(await screen.findByRole("progressbar", { name: "Session, 42 %" })).toBeInTheDocument();
    expect(screen.getAllByText("inconnu")).toHaveLength(1);
    expect(screen.getAllByRole("progressbar")).toHaveLength(1);
  });

  it("shows the utilization and the resume time of five_hour and seven_day", async () => {
    const reprise5h = new Date(2026, 9, 26, 14, 30).toISOString();
    const reprise7j = new Date(2026, 9, 29, 8, 15).toISOString();
    simuler([2], { five_hour: lecture(0.42, reprise5h), seven_day: lecture(0.8, reprise7j) });
    render(<TableauDuJour maintenant={MAINTENANT} signalRunsClos={0} />);

    const session = await screen.findByRole("progressbar", { name: "Session, 42 %" });
    const semaine = screen.getByRole("progressbar", { name: "Semaine, 80 %" });
    expect(session).toHaveAttribute("aria-valuenow", "42");
    expect(semaine).toHaveAttribute("aria-valuenow", "80");
    expect(screen.getByText("42 %")).toBeInTheDocument();
    expect(screen.getByText("80 %")).toBeInTheDocument();

    const heure5h = heureDeReprise(reprise5h, MAINTENANT) ?? "";
    const heure7j = heureDeReprise(reprise7j, MAINTENANT) ?? "";
    expect(screen.getByText(heure5h)).toHaveAttribute("datetime", reprise5h);
    expect(screen.getByText(heure7j)).toHaveAttribute("datetime", reprise7j);
  });

  it("states in its accessible name that the day is in UTC", async () => {
    simuler([2]);
    render(<TableauDuJour maintenant={MAINTENANT} signalRunsClos={0} />);
    await screen.findByText("$2.00");

    const tableau = screen.getByRole("complementary", { name: /UTC/ });
    expect(within(tableau).getByTestId("depense-du-jour")).toHaveTextContent("$2.00");
  });

  it("reads again each minute of the clock, and not before", async () => {
    const { stats: espion } = simuler([2]);
    const { rerender } = render(<TableauDuJour maintenant={MAINTENANT} signalRunsClos={0} />);
    await waitFor(() => expect(espion).toHaveBeenCalledTimes(1));

    rerender(<TableauDuJour maintenant={MAINTENANT + 5_000} signalRunsClos={0} />);
    expect(espion).toHaveBeenCalledTimes(1);

    rerender(<TableauDuJour maintenant={MAINTENANT + 60_000} signalRunsClos={0} />);
    await waitFor(() => expect(espion).toHaveBeenCalledTimes(2));
  });
});

describe("TableauDuJour in the office", () => {
  it("reads again when a run closes", async () => {
    const { stats: espion, quota } = simuler([2]);
    vi.spyOn(api.services, "list").mockResolvedValue([]);
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
    const enCours = etatEnCodage();
    const clos = applyEvent(enCours, {
      type: "run_closed",
      agent: null,
      ticket_id: "ticket-001",
      data: {},
      timestamp: DERNIER,
    });

    const { rerender } = render(<BureauView projets={[{ nom: "p", etat: enCours }]} />);
    await waitFor(() => expect(espion).toHaveBeenCalledTimes(1));

    rerender(<BureauView projets={[{ nom: "p", etat: clos }]} />);

    await waitFor(() => expect(espion).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(quota).toHaveBeenCalledTimes(2));
  });
});
