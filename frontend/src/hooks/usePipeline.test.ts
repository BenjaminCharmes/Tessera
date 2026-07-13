import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { usePipeline } from "./usePipeline";
import * as apiModule from "../lib/api";
import type { PipelineResult } from "../types/api";

const RESULT: PipelineResult = {
  ticket_id: "ticket-001",
  final_status: "done",
  rounds: 2,
  approved: true,
};

vi.mock("../lib/api", () => ({
  api: {
    orchestrator: {
      run: vi.fn(),
    },
  },
}));

describe("usePipeline", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiModule.api.orchestrator.run).mockResolvedValue(RESULT);
  });

  it("starts with empty running set and results map", () => {
    const { result } = renderHook(() => usePipeline("proj-1"));
    expect(result.current.running.size).toBe(0);
    expect(result.current.results.size).toBe(0);
  });

  it("does nothing when projectId is null", async () => {
    const { result } = renderHook(() => usePipeline(null));
    act(() => {
      result.current.run("ticket-001");
    });
    expect(apiModule.api.orchestrator.run).not.toHaveBeenCalled();
    expect(result.current.running.size).toBe(0);
  });

  it("adds ticketId to running during execution", async () => {
    let resolve!: (r: PipelineResult) => void;
    vi.mocked(apiModule.api.orchestrator.run).mockReturnValue(
      new Promise<PipelineResult>((res) => {
        resolve = res;
      }),
    );
    const { result } = renderHook(() => usePipeline("proj-1"));

    act(() => {
      result.current.run("ticket-001");
    });
    expect(result.current.running.has("ticket-001")).toBe(true);

    await act(async () => {
      resolve(RESULT);
    });
    expect(result.current.running.has("ticket-001")).toBe(false);
  });

  it("stores result after successful run", async () => {
    const { result } = renderHook(() => usePipeline("proj-1"));
    await act(async () => {
      result.current.run("ticket-001");
    });
    await waitFor(() => expect(result.current.running.size).toBe(0));
    expect(result.current.results.get("ticket-001")).toEqual(RESULT);
  });

  it("clears running after API failure", async () => {
    vi.mocked(apiModule.api.orchestrator.run).mockRejectedValue(
      new Error("Pipeline failed"),
    );
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    const { result } = renderHook(() => usePipeline("proj-1"));
    await act(async () => {
      result.current.run("ticket-001");
    });
    await waitFor(() => expect(result.current.running.size).toBe(0));
    expect(consoleSpy).toHaveBeenCalledWith(
      expect.stringContaining("ticket-001"),
    );
    consoleSpy.mockRestore();
  });

  it("does not add duplicate ticketId to running", async () => {
    let resolve!: (r: PipelineResult) => void;
    vi.mocked(apiModule.api.orchestrator.run).mockReturnValue(
      new Promise<PipelineResult>((res) => {
        resolve = res;
      }),
    );
    const { result } = renderHook(() => usePipeline("proj-1"));

    act(() => {
      result.current.run("ticket-001");
      result.current.run("ticket-001");
    });
    // Still only one entry
    expect(
      [...result.current.running].filter((id) => id === "ticket-001"),
    ).toHaveLength(1);

    await act(async () => {
      resolve(RESULT);
    });
  });
});
