import { describe, it, expect } from "vitest";
import type { PipelineRun } from "../../types/api";
import {
  etatDuRun,
  filtrerRuns,
  formatDuree,
  lienPr,
  runAffiche,
  runsDeTicket,
} from "./runs";

function run(id: string, extra: Partial<PipelineRun> = {}): PipelineRun {
  return {
    id,
    ticket_id: `ticket-${id}`,
    started_at: "2026-10-14T07:00:00Z",
    finished_at: "2026-10-14T07:01:05Z",
    rounds: 1,
    approved: true,
    final_status: "done",
    total_cost_usd: 0,
    ...extra,
  };
}

describe("runs helpers", () => {
  it("classifies approved, blocked, refused and running runs", () => {
    expect(etatDuRun(run("a"))).toBe("approuve");
    expect(etatDuRun(run("b", { approved: false, final_status: "blocked" }))).toBe("bloque");
    expect(etatDuRun(run("c", { approved: false, final_status: "in-review" }))).toBe("refuse");
    expect(
      etatDuRun(run("d", { approved: null, final_status: null, finished_at: null })),
    ).toBe("en-cours");
  });

  it("filters by verdict and by number of rounds", () => {
    const runs = [run("a"), run("b", { approved: false, rounds: 3 }), run("c", { rounds: 2 })];
    expect(filtrerRuns(runs, "tous")).toHaveLength(3);
    expect(filtrerRuns(runs, "approuves").map((r) => r.id)).toEqual(["a", "c"]);
    expect(filtrerRuns(runs, "refuses").map((r) => r.id)).toEqual(["b"]);
    expect(filtrerRuns(runs, "tours").map((r) => r.id)).toEqual(["b", "c"]);
  });

  it("picks the selected run, else the most recent, else nothing", () => {
    const ancien = run("old", { started_at: "2026-10-01T00:00:00Z" });
    const recent = run("new");
    expect(runAffiche([ancien, recent], "old")?.id).toBe("old");
    expect(runAffiche([ancien, recent], null)?.id).toBe("new");
    expect(runAffiche([ancien, recent], "inconnu")?.id).toBe("new");
    expect(runAffiche([], null)).toBeNull();
  });

  it("formats the duration of a run", () => {
    expect(formatDuree(run("a"))).toBe("1m 05s");
    expect(formatDuree(run("a", { finished_at: null }))).toBe("En cours…");
  });

  it("drops a queue's parent run and keeps one row per ticket", () => {
    const file = run("file", { parent_run_id: null });
    const enfants = [
      run("a", { parent_run_id: "file" }),
      run("b", { parent_run_id: "file" }),
    ];
    expect(runsDeTicket([file, ...enfants]).map((r) => r.id)).toEqual(["a", "b"]);
  });

  it("keeps a single-ticket run with neither parent nor child", () => {
    expect(runsDeTicket([run("seul", { parent_run_id: null }), run("x")])).toHaveLength(2);
  });

  it("flags a run closed without a round as interrupted, with no duration", () => {
    const interrompu = run("i", {
      approved: false,
      final_status: "blocked",
      rounds: 0,
      arret: "backend restarted: the run's process is gone",
      finished_at: "2026-10-14T22:25:00Z",
    });
    expect(etatDuRun(interrompu)).toBe("interrompu");
    expect(formatDuree(interrompu)).toBe("—");
    // Un blocage avec sa propre cause, ou après un tour, n'est pas une interruption.
    expect(etatDuRun({ ...interrompu, arret: "tests failed" })).toBe("bloque");
    expect(etatDuRun({ ...interrompu, rounds: 1 })).toBe("bloque");
  });

  it("builds a pull request link for GitHub remotes only", () => {
    expect(lienPr("moi/depot", 4)).toBe("https://github.com/moi/depot/pull/4");
    expect(lienPr("https://github.com/moi/depot.git", 4)).toBe(
      "https://github.com/moi/depot/pull/4",
    );
    expect(lienPr("https://dev.azure.com/org/p/_git/p", 4)).toBeNull();
    expect(lienPr(null, 4)).toBeNull();
    expect(lienPr("moi/depot", null)).toBeNull();
  });
});
