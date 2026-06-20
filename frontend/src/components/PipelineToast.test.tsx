import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import PipelineToast from "./PipelineToast";
import type { PipelineResult } from "../types/api";

const SUCCESS_RESULT: PipelineResult = {
  ticket_id: "ticket-001",
  final_status: "done",
  rounds: 2,
  approved: true,
};

const FAILURE_RESULT: PipelineResult = {
  ticket_id: "ticket-002",
  final_status: "blocked",
  rounds: 3,
  approved: false,
};

describe("PipelineToast", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders nothing when result is null", () => {
    const { container } = render(<PipelineToast result={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("shows success toast when result is approved", () => {
    render(<PipelineToast result={SUCCESS_RESULT} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText(/ticket-001/)).toBeInTheDocument();
    expect(screen.getByText(/2 tours/)).toBeInTheDocument();
  });

  it("shows singular 'tour' when rounds is 1", () => {
    const result: PipelineResult = { ...SUCCESS_RESULT, rounds: 1 };
    render(<PipelineToast result={result} />);
    expect(screen.getByText(/1 tour/)).toBeInTheDocument();
  });

  it("shows failure toast when result is not approved", () => {
    render(<PipelineToast result={FAILURE_RESULT} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText(/échoué/)).toBeInTheDocument();
    expect(screen.getByText(/blocked/)).toBeInTheDocument();
  });

  it("auto-dismisses after 3 seconds", async () => {
    render(<PipelineToast result={SUCCESS_RESULT} />);
    expect(screen.getByRole("status")).toBeInTheDocument();

    await act(async () => {
      vi.advanceTimersByTime(3000);
    });

    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("does not re-show when same result prop is re-rendered", async () => {
    const { rerender } = render(<PipelineToast result={SUCCESS_RESULT} />);
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<PipelineToast result={SUCCESS_RESULT} />);
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows again when a new result comes in after dismiss", async () => {
    const { rerender } = render(<PipelineToast result={SUCCESS_RESULT} />);
    await act(async () => {
      vi.advanceTimersByTime(3000);
    });
    expect(screen.queryByRole("status")).not.toBeInTheDocument();

    rerender(<PipelineToast result={FAILURE_RESULT} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});
