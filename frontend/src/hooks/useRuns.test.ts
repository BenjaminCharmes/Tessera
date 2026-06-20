import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useRuns } from "./useRuns";
import * as apiModule from "../lib/api";
import type { PipelineRun } from "../types/api";

const RUN_1: PipelineRun = {
  id: "run-001",
  ticket_id: "ticket-001",
  started_at: "2026-06-20T12:00:00Z",
  finished_at: "2026-06-20T12:01:23Z",
  rounds: 2,
  approved: true,
  final_status: "done",
};

const RUN_2: PipelineRun = {
  id: "run-002",
  ticket_id: "ticket-002",
  started_at: "2026-06-20T13:00:00Z",
  finished_at: null,
  rounds: null,
  approved: null,
  final_status: null,
};

vi.mock("../lib/api", () => ({
  api: {
    runs: {
      list: vi.fn(),
    },
  },
}));

describe("useRuns", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiModule.api.runs.list).mockResolvedValue([RUN_1, RUN_2]);
  });

  it("fetches runs on mount", async () => {
    const { result } = renderHook(() => useRuns("proj-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.runs).toHaveLength(2);
    expect(apiModule.api.runs.list).toHaveBeenCalledWith("proj-1");
  });

  it("starts with loading true", () => {
    const { result } = renderHook(() => useRuns("proj-1"));
    expect(result.current.loading).toBe(true);
  });

  it("returns empty state when projectId is null", () => {
    const { result } = renderHook(() => useRuns(null));
    expect(result.current.runs).toHaveLength(0);
    expect(result.current.loading).toBe(false);
  });

  it("refresh() re-fetches the list", async () => {
    const { result } = renderHook(() => useRuns("proj-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiModule.api.runs.list).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refresh();
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiModule.api.runs.list).toHaveBeenCalledTimes(2);
  });

  it("sets error on API failure", async () => {
    vi.mocked(apiModule.api.runs.list).mockRejectedValue(
      new Error("Network error"),
    );
    const { result } = renderHook(() => useRuns("proj-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network error");
    expect(result.current.runs).toHaveLength(0);
  });

  it("re-fetches when projectId changes", async () => {
    const { result, rerender } = renderHook(
      ({ id }: { id: string }) => useRuns(id),
      { initialProps: { id: "proj-1" } },
    );
    await waitFor(() => expect(result.current.loading).toBe(false));

    vi.mocked(apiModule.api.runs.list).mockResolvedValue([RUN_1]);

    act(() => {
      rerender({ id: "proj-2" });
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiModule.api.runs.list).toHaveBeenCalledWith("proj-2");
  });
});
