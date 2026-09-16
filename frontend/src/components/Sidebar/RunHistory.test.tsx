import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RunHistory from "./RunHistory";
import type { PipelineRun } from "../../types/api";

const RUN_DONE: PipelineRun = {
  id: "run-001",
  ticket_id: "ticket-011",
  started_at: "2026-06-20T12:00:00Z",
  finished_at: "2026-06-20T12:01:23Z",
  rounds: 2,
  approved: true,
  final_status: "done",
  total_cost_usd: 0,
};

const RUN_BLOCKED: PipelineRun = {
  id: "run-002",
  ticket_id: "ticket-009",
  started_at: "2026-06-20T13:00:00Z",
  finished_at: "2026-06-20T13:04:01Z",
  rounds: 3,
  approved: false,
  final_status: "blocked",
  total_cost_usd: 0,
};

const RUN_IN_PROGRESS: PipelineRun = {
  id: "run-003",
  ticket_id: "ticket-012",
  started_at: "2026-06-20T14:00:00Z",
  finished_at: null,
  rounds: null,
  approved: null,
  final_status: null,
  total_cost_usd: 0,
};

describe("RunHistory", () => {
  it("shows loading state", () => {
    render(<RunHistory runs={[]} loading={true} error={null} />);
    expect(screen.getByText(/chargement/i)).toBeInTheDocument();
  });

  it("shows error state", () => {
    render(<RunHistory runs={[]} loading={false} error="API error" />);
    expect(screen.getByText("API error")).toBeInTheDocument();
  });

  it("shows empty state when no runs", () => {
    render(<RunHistory runs={[]} loading={false} error={null} />);
    expect(screen.getByText(/aucun pipeline/i)).toBeInTheDocument();
  });

  it("renders run list with ticket ids", () => {
    render(
      <RunHistory
        runs={[RUN_DONE, RUN_BLOCKED]}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByText("ticket-011")).toBeInTheDocument();
    expect(screen.getByText("ticket-009")).toBeInTheDocument();
  });

  it("formats duration correctly for finished run", () => {
    render(<RunHistory runs={[RUN_DONE]} loading={false} error={null} />);
    expect(screen.getByText("1m 23s")).toBeInTheDocument();
  });

  it("shows 'En cours…' for in-progress run", () => {
    render(
      <RunHistory runs={[RUN_IN_PROGRESS]} loading={false} error={null} />,
    );
    expect(screen.getByText("En cours…")).toBeInTheDocument();
  });

  it("expands run details on click", async () => {
    render(<RunHistory runs={[RUN_DONE]} loading={false} error={null} />);

    await userEvent.click(screen.getByText("ticket-011"));

    expect(screen.getByText("done")).toBeInTheDocument();
    expect(screen.getByText(/Approuvé/)).toBeInTheDocument();
  });

  it("calls onSelectTicket when 'Voir le ticket' is clicked", async () => {
    const onSelectTicket = vi.fn();
    render(
      <RunHistory
        runs={[RUN_DONE]}
        loading={false}
        error={null}
        onSelectTicket={onSelectTicket}
      />,
    );

    await userEvent.click(screen.getByText("ticket-011"));
    await userEvent.click(screen.getByText(/Voir le ticket/));

    expect(onSelectTicket).toHaveBeenCalledWith("ticket-011");
  });

  it("shows run count in header", () => {
    render(
      <RunHistory
        runs={[RUN_DONE, RUN_BLOCKED]}
        loading={false}
        error={null}
      />,
    );
    expect(screen.getByText("2 runs")).toBeInTheDocument();
  });
});
