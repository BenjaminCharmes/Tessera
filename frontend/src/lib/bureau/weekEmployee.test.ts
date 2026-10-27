import { describe, expect, it } from "vitest";
import type { PipelineRun } from "../../types/api";
import { employeeLabel, firstTryCount, weekEmployee } from "./weekEmployee";

const NOW = Date.parse("2026-10-27T12:00:00Z");
const DAY_MS = 24 * 60 * 60 * 1000;

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

function approved(count: number, over: Partial<PipelineRun> = {}): PipelineRun[] {
  return Array.from({ length: count }, (_, i) => run(String(i + 1), over));
}

describe("weekEmployee", () => {
  it("names the project with the most first-try approvals", () => {
    const winner = weekEmployee(
      [
        { project: "alpha", runs: approved(3) },
        { project: "beta", runs: approved(5) },
      ],
      NOW,
    );

    expect(winner).toEqual({ project: "beta", count: 5 });
  });

  it("does not count a ticket approved at round 2 or eight days ago", () => {
    const runs = [
      run("1"),
      run("2", { rounds: 2 }),
      run("3", { started_at: new Date(NOW - 8 * DAY_MS).toISOString() }),
      run("4", { approved: false }),
      run("5", { rounds: null, approved: null }),
    ];

    expect(firstTryCount(runs, NOW)).toBe(1);
  });

  it("counts a ticket once even with two first-try runs", () => {
    const runs = [run("1"), run("1", { id: "run-1b" })];

    expect(firstTryCount(runs, NOW)).toBe(1);
  });

  it("keeps a run of exactly seven days out and a run just inside in", () => {
    const edge = run("1", { started_at: new Date(NOW - 7 * DAY_MS).toISOString() });
    const inside = run("2", { started_at: new Date(NOW - 7 * DAY_MS + 1_000).toISOString() });

    expect(firstTryCount([edge, inside], NOW)).toBe(1);
  });

  it("ignores an unreadable date", () => {
    expect(firstTryCount([run("1", { started_at: "not a date" })], NOW)).toBe(0);
  });

  it("returns null when nothing was approved at the first try this week", () => {
    const stale = approved(2, { rounds: 2 });

    expect(weekEmployee([{ project: "alpha", runs: stale }, { project: "beta", runs: [] }], NOW)).toBeNull();
    expect(weekEmployee([], NOW)).toBeNull();
  });

  it("leaves a tie to the first project listed", () => {
    const winner = weekEmployee(
      [
        { project: "alpha", runs: approved(2) },
        { project: "beta", runs: approved(2) },
      ],
      NOW,
    );

    expect(winner?.project).toBe("alpha");
  });
});

describe("employeeLabel", () => {
  it("writes the plural and the singular", () => {
    expect(employeeLabel({ project: "beta", count: 5 })).toBe("beta · codeur, 5 tickets du 1er coup");
    expect(employeeLabel({ project: "beta", count: 1 })).toBe("beta · codeur, 1 ticket du 1er coup");
  });
});
