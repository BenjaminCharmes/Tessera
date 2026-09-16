import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useUsage } from "./useUsage";
import * as apiModule from "../lib/api";
import type { ProjectUsage } from "../types/api";

const USAGE: ProjectUsage = {
  total_cost_usd: 0.05,
  total_tokens: 10000,
  total_runs: 2,
  per_ticket: [
    {
      ticket_id: "ticket-001",
      total_cost_usd: 0.03,
      input_tokens: 3000,
      output_tokens: 1000,
      cache_read_tokens: 200,
      call_count: 1,
    },
  ],
};

vi.mock("../lib/api", () => ({
  api: {
    usage: {
      get: vi.fn(),
    },
  },
}));

describe("useUsage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiModule.api.usage.get).mockResolvedValue(USAGE);
  });

  it("fetches usage on mount", async () => {
    const { result } = renderHook(() => useUsage("proj-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.usage).toEqual(USAGE);
    expect(apiModule.api.usage.get).toHaveBeenCalledWith("proj-1");
  });

  it("starts with loading true when projectId is set", () => {
    const { result } = renderHook(() => useUsage("proj-1"));
    expect(result.current.loading).toBe(true);
  });

  it("returns null usage when projectId is null", () => {
    const { result } = renderHook(() => useUsage(null));
    expect(result.current.usage).toBeNull();
    expect(result.current.loading).toBe(false);
    expect(apiModule.api.usage.get).not.toHaveBeenCalled();
  });

  it("refresh() re-fetches usage", async () => {
    const { result } = renderHook(() => useUsage("proj-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiModule.api.usage.get).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refresh();
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiModule.api.usage.get).toHaveBeenCalledTimes(2);
  });

  it("sets error on API failure", async () => {
    vi.mocked(apiModule.api.usage.get).mockRejectedValue(
      new Error("Network error"),
    );
    const { result } = renderHook(() => useUsage("proj-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network error");
    expect(result.current.usage).toBeNull();
  });

  it("handles non-Error rejection", async () => {
    vi.mocked(apiModule.api.usage.get).mockRejectedValue("raw string error");
    const { result } = renderHook(() => useUsage("proj-1"));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Unknown error");
  });

  it("clears usage when projectId changes to null", async () => {
    const { result, rerender } = renderHook(
      ({ id }: { id: string | null }) => useUsage(id),
      // Annoté : sans cela le type de Props est déduit comme `{ id: string }`,
      // et le rerender à null que ce test existe précisément pour couvrir ne
      // compile pas.
      { initialProps: { id: "proj-1" } as { id: string | null } },
    );
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.usage).toEqual(USAGE);

    act(() => {
      rerender({ id: null });
    });

    expect(result.current.usage).toBeNull();
  });
});
