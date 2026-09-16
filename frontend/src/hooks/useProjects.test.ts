import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { useProjects } from "./useProjects";
import * as apiModule from "../lib/api";
import type { Project } from "../types/api";

const PROJECTS: Project[] = [
  {
    id: "proj-1",
    name: "Project 1",
    path: "/ws/proj-1",
    description: "First",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
  },
  {
    id: "proj-2",
    name: "Project 2",
    path: "/ws/proj-2",
    description: "Second",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
  },
];

vi.mock("../lib/api", () => ({
  api: {
    projects: {
      list: vi.fn(),
    },
  },
}));

describe("useProjects", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(apiModule.api.projects.list).mockResolvedValue(PROJECTS);
  });

  it("fetches projects on mount", async () => {
    const { result } = renderHook(() => useProjects());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.projects).toEqual(PROJECTS);
    expect(apiModule.api.projects.list).toHaveBeenCalledTimes(1);
  });

  it("starts with loading true", () => {
    const { result } = renderHook(() => useProjects());
    expect(result.current.loading).toBe(true);
  });

  it("sets error on API failure", async () => {
    vi.mocked(apiModule.api.projects.list).mockRejectedValue(
      new Error("Server down"),
    );
    const { result } = renderHook(() => useProjects());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Server down");
    expect(result.current.projects).toHaveLength(0);
  });

  it("handles non-Error rejection", async () => {
    vi.mocked(apiModule.api.projects.list).mockRejectedValue("oops");
    const { result } = renderHook(() => useProjects());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe("Unknown error");
  });

  it("refresh() triggers a new fetch", async () => {
    const { result } = renderHook(() => useProjects());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiModule.api.projects.list).toHaveBeenCalledTimes(1);

    act(() => {
      result.current.refresh();
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(apiModule.api.projects.list).toHaveBeenCalledTimes(2);
  });
});
