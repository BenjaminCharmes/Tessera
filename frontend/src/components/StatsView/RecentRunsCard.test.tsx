import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RecentRunsCard from "./RecentRunsCard";
import { api } from "../../lib/api";
import type { RecentRun } from "../../types/api";

vi.mock("../../lib/api");

function run(i: number, ticket = `ticket-${300 + i}`): RecentRun {
  return {
    id: `r${i}`,
    project_id: "ide-core",
    ticket_id: ticket,
    started_at: "2026-10-03T17:19:08+00:00",
    finished_at: "2026-10-03T17:33:00+00:00",
    approved: true,
    final_status: "done",
    cost_usd: 0.5,
    input_tokens: 100,
    output_tokens: 50,
    duration_ms: 1000,
  };
}

const dix = Array.from({ length: 10 }, (_, i) => run(i));

function lignes(): HTMLElement[] {
  // La ligne d'en-tête exclue.
  return within(screen.getByRole("table")).getAllByRole("row").slice(1);
}

beforeEach(() => {
  vi.mocked(api.usage.recentRuns).mockReset();
});

describe("RecentRunsCard — ticket-335", () => {
  it("shows the runs loaded with the statistics without asking for more", () => {
    render(<RecentRunsCard initial={dix} days={30} projectId={null} onSelect={() => {}} />);

    expect(lignes()).toHaveLength(10);
    expect(api.usage.recentRuns).not.toHaveBeenCalled();
  });

  it("loads twenty more runs on « Afficher plus »", async () => {
    vi.mocked(api.usage.recentRuns).mockResolvedValue(
      Array.from({ length: 30 }, (_, i) => run(i)),
    );
    render(<RecentRunsCard initial={dix} days={30} projectId="ide-core" onSelect={() => {}} />);

    await userEvent.click(screen.getByRole("button", { name: "Afficher plus" }));

    expect(api.usage.recentRuns).toHaveBeenCalledWith(30, "ide-core", 30, "");
    await vi.waitFor(() => expect(lignes()).toHaveLength(30));
  });

  it("searches by ticket or project once typing pauses", async () => {
    vi.mocked(api.usage.recentRuns).mockResolvedValue([run(17, "ticket-317")]);
    render(<RecentRunsCard initial={dix} days={7} projectId={null} onSelect={() => {}} />);

    await userEvent.type(screen.getByRole("searchbox", { name: "Chercher un run" }), "317");

    await vi.waitFor(() =>
      expect(api.usage.recentRuns).toHaveBeenLastCalledWith(7, null, 10, "317"),
    );
    // Une requête pour la recherche finale, pas une par caractère.
    expect(api.usage.recentRuns).toHaveBeenCalledTimes(1);
    await vi.waitFor(() => expect(lignes()).toHaveLength(1));
    expect(screen.queryByRole("button", { name: "Afficher plus" })).not.toBeInTheDocument();
  });

  it("does not offer more when the period holds fewer runs than shown", () => {
    render(
      <RecentRunsCard initial={dix.slice(0, 4)} days={30} projectId={null} onSelect={() => {}} />,
    );

    expect(screen.queryByRole("button", { name: "Afficher plus" })).not.toBeInTheDocument();
  });

  it("says when a search matches nothing", async () => {
    vi.mocked(api.usage.recentRuns).mockResolvedValue([]);
    render(<RecentRunsCard initial={dix} days={30} projectId={null} onSelect={() => {}} />);

    await userEvent.type(screen.getByRole("searchbox", { name: "Chercher un run" }), "zzz");

    expect(await screen.findByText("Aucun run ne correspond à « zzz ».")).toBeInTheDocument();
  });
});
