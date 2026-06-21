import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useAgents } from "./useAgents";
import * as apiModule from "../lib/api";
import type { AgentInfo } from "../types/api";

const AGENT_BUILTIN: AgentInfo = {
  role: "codeur",
  description: null,
  is_builtin: true,
  prompt_preview: "Tu es un codeur expert…",
};

const AGENT_CUSTOM: AgentInfo = {
  role: "securite",
  description: "Audit de sécurité",
  is_builtin: false,
  prompt_preview: "Tu audites la sécurité…",
};

vi.mock("../lib/api", () => ({
  api: {
    agents: {
      list: vi.fn(),
    },
  },
}));

describe("useAgents", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiModule.api.agents.list).mockResolvedValue([
      AGENT_BUILTIN,
      AGENT_CUSTOM,
    ]);
  });

  it("fetches agents on mount", async () => {
    const { result } = renderHook(() => useAgents());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.agents).toHaveLength(2);
    expect(apiModule.api.agents.list).toHaveBeenCalledTimes(1);
  });

  it("starts with loading true", () => {
    const { result } = renderHook(() => useAgents());
    expect(result.current.loading).toBe(true);
  });

  it("refresh() re-fetches the list", async () => {
    const { result } = renderHook(() => useAgents());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiModule.api.agents.list).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refresh();
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiModule.api.agents.list).toHaveBeenCalledTimes(2);
  });

  it("sets error on API failure", async () => {
    vi.mocked(apiModule.api.agents.list).mockRejectedValue(
      new Error("Network error"),
    );
    const { result } = renderHook(() => useAgents());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Network error");
    expect(result.current.agents).toHaveLength(0);
  });

  it("exposes built-in and custom agents", async () => {
    const { result } = renderHook(() => useAgents());
    await waitFor(() => expect(result.current.loading).toBe(false));
    const builtin = result.current.agents.find((a) => a.is_builtin);
    const custom = result.current.agents.find((a) => !a.is_builtin);
    expect(builtin?.role).toBe("codeur");
    expect(custom?.role).toBe("securite");
  });
});
