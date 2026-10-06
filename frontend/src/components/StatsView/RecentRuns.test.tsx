import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RecentRuns from "./RecentRuns";
import type { RecentRun } from "../../types/api";

function run(over: Partial<RecentRun> = {}): RecentRun {
  return {
    id: "r1",
    project_id: "proj",
    ticket_id: "ticket-007",
    started_at: "2026-09-28T08:00:00+00:00",
    finished_at: "2026-09-28T08:10:00+00:00",
    approved: true,
    final_status: "done",
    cost_usd: 0.5,
    input_tokens: 2000,
    output_tokens: 1000,
    duration_ms: 600_000,
    ...over,
  };
}

describe("RecentRuns — onSelect (ticket-281)", () => {
  it("calls onSelect with the run when clicking a row", async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();
    const r = run({ id: "run-abc", ticket_id: "ticket-042" });

    render(<RecentRuns runs={[r]} showProject={false} onSelect={handleSelect} />);

    await user.click(screen.getByText("ticket-042").closest("tr")!);

    expect(handleSelect).toHaveBeenCalledOnce();
    expect(handleSelect).toHaveBeenCalledWith(r);
  });

  it("shows a pointer cursor when onSelect is provided", () => {
    render(
      <RecentRuns runs={[run()]} showProject={false} onSelect={vi.fn()} />,
    );

    const row = screen.getByText("ticket-007").closest("tr");
    expect(row?.className).toContain("cursor-pointer");
  });

  it("does not show a pointer cursor when no onSelect is given", () => {
    render(<RecentRuns runs={[run()]} showProject={false} />);

    const row = screen.getByText("ticket-007").closest("tr");
    expect(row?.className).not.toContain("cursor-pointer");
  });
});
