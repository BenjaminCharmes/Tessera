import { describe, it, expect } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useActiveProject } from "./useActiveProject";
import type { Project, Ticket } from "../types/api";

const mockProject: Project = {
  id: "ide-core",
  name: "IDE Core",
  description: "Bootstrap project",
  active_agents: ["codeur"],
  stack: null,
  raw_claude_md: "# IDE Core",
  github_remote: null,
};

const mockTicket: Ticket = {
  id: "ticket-001",
  title: "Test ticket",
  type: "feat",
  status: "todo",
  priority: "medium",
  agent: "codeur",
  depends_on: [],
  created: "2026-06-20",
  github_issue_url: null,
  pr_number: null,
  body: "Body content",
  project_id: "ide-core",
  file_path: "/path/to/ticket.md",
};

describe("useActiveProject", () => {
  it("starts with null project and ticket", () => {
    const { result } = renderHook(() => useActiveProject());
    expect(result.current.project).toBeNull();
    expect(result.current.ticket).toBeNull();
  });

  it("setProject stores the project", () => {
    const { result } = renderHook(() => useActiveProject());
    act(() => {
      result.current.setProject(mockProject);
    });
    expect(result.current.project).toEqual(mockProject);
  });

  it("setProject resets ticket to null", () => {
    const { result } = renderHook(() => useActiveProject());
    act(() => {
      result.current.setTicket(mockTicket);
    });
    expect(result.current.ticket).toEqual(mockTicket);

    act(() => {
      result.current.setProject(mockProject);
    });
    expect(result.current.ticket).toBeNull();
  });

  it("setTicket stores the ticket independently", () => {
    const { result } = renderHook(() => useActiveProject());
    act(() => {
      result.current.setProject(mockProject);
      result.current.setTicket(mockTicket);
    });
    expect(result.current.project).toEqual(mockProject);
    expect(result.current.ticket).toEqual(mockTicket);
  });

  it("setProject(null) clears both project and ticket", () => {
    const { result } = renderHook(() => useActiveProject());
    act(() => {
      result.current.setProject(mockProject);
      result.current.setTicket(mockTicket);
    });
    act(() => {
      result.current.setProject(null);
    });
    expect(result.current.project).toBeNull();
    expect(result.current.ticket).toBeNull();
  });
});
