import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { _viderCacheResource } from "../../hooks/useResource";
import { api } from "../../lib/api";
import type { PipelineRun } from "../../types/api";
import BureauView from "./index";
import SallesCommunes from "./SallesCommunes";

const NOW = Date.parse("2026-10-27T12:00:00Z");
const DAY_MS = 24 * 60 * 60 * 1000;
const CANAL = { envoyer: vi.fn(), son: { actif: false, regler: vi.fn() } };

function run(id: string, over: Partial<PipelineRun> = {}): PipelineRun {
  return {
    id: `run-${id}`,
    ticket_id: `ticket-${id}`,
    started_at: new Date(NOW - DAY_MS).toISOString(),
    finished_at: null,
    rounds: 1,
    approved: true,
    final_status: "done",
    total_cost_usd: 0,
    ...over,
  };
}

function approved(count: number): PipelineRun[] {
  return Array.from({ length: count }, (_, i) => run(String(i + 1)));
}

function historique(parProjet: Record<string, PipelineRun[]>): void {
  vi.spyOn(api.runs, "list").mockImplementation((projet: string) =>
    Promise.resolve(parProjet[projet] ?? []),
  );
}

function renderBureau() {
  return render(
    <BureauView projets={[]} auRepos={["alpha", "beta"]} signalServices={0} {...CANAL} />,
  );
}

beforeEach(() => {
  _viderCacheResource();
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(NOW);
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Employee of the week frame", () => {
  it("names the project with five first-try tickets over the one with three", async () => {
    historique({ alpha: approved(3), beta: approved(5) });
    const { container } = renderBureau();

    await waitFor(() => expect(container.querySelector('[data-employe="beta"]')).not.toBeNull());
    expect(container.querySelector('[data-employe="alpha"]')).toBeNull();

    fireEvent.focus(container.querySelector('[data-employe="beta"]')!.parentElement!);
    expect(screen.getByRole("tooltip")).toHaveTextContent("beta · codeur, 5 tickets du 1er coup");
  });

  it("does not count a ticket approved at round 2 or eight days ago", async () => {
    historique({
      alpha: [run("1", { rounds: 2 }), run("2", { started_at: new Date(NOW - 8 * DAY_MS).toISOString() })],
      beta: [run("3")],
    });
    const { container } = renderBureau();

    await waitFor(() => expect(container.querySelector('[data-employe="beta"]')).not.toBeNull());
    fireEvent.focus(container.querySelector('[data-employe="beta"]')!.parentElement!);
    expect(screen.getByRole("tooltip")).toHaveTextContent("beta · codeur, 1 ticket du 1er coup");
  });

  it("draws no frame when nothing was approved at the first try this week", async () => {
    historique({ alpha: [run("1", { rounds: 2 })], beta: [] });
    const { container } = renderBureau();

    // Les deux relectures sont parties ; on attend leur résultat avant de conclure à l'absence.
    await waitFor(() => expect(api.runs.list).toHaveBeenCalledTimes(2));
    await act(async () => {
      await Promise.all(vi.mocked(api.runs.list).mock.results.map((r) => r.value));
    });

    expect(container.querySelector('[data-sprite="cadre-employe"]')).toBeNull();
  });

  it("hangs the frame in the break room, not in the director's office", () => {
    const { container } = render(
      <SallesCommunes projets={[]} maintenant={NOW} employe={{ project: "beta", count: 5 }} />,
    );

    const salle = container.querySelector('[data-sprite="cadre-employe"]')?.closest("aside");
    expect(salle?.getAttribute("aria-label")).toBe("Salle de pause");
  });

  it("writes the text nowhere but in the tooltip", async () => {
    const { container } = render(
      <SallesCommunes projets={[]} maintenant={NOW} employe={{ project: "beta", count: 5 }} />,
    );

    expect(container.querySelector('[data-sprite="cadre-employe"]')).not.toBeNull();
    expect(screen.queryByText(/du 1er coup/)).toBeNull();
  });
});
