import { describe, it, expect, vi, beforeEach } from "vitest";
import { api } from "./api";

const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

beforeEach(() => {
  mockFetch.mockReset();
});

describe("api.projects.list", () => {
  it("returns parsed projects on 200", async () => {
    const projects = [{ id: "ide-core", name: "IDE Core" }];
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(projects),
    });

    const result = await api.projects.list();

    expect(result).toEqual(projects);
    expect(mockFetch).toHaveBeenCalledWith("/api/v1/projects", undefined);
  });

  it("throws ApiError on non-200", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not Found"),
    });

    await expect(api.projects.list()).rejects.toThrow("API 404");
  });
});

describe("api.tickets.list", () => {
  it("calls the correct endpoint", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve([]),
    });

    await api.tickets.list("ide-core");

    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects/ide-core/tickets",
      undefined,
    );
  });

  it("throws on server error", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 500,
      text: () => Promise.resolve("Internal Server Error"),
    });

    await expect(api.tickets.list("ide-core")).rejects.toThrow("API 500");
  });
});

describe("api.projects.create", () => {
  it("sends POST with name, project_id and description", async () => {
    const project = { id: "my-app", name: "my-app", description: "desc" };
    const creationResult = { project, agents_created: [] };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(creationResult),
    });

    const result = await api.projects.create("my-app", "desc");

    expect(result).toEqual(creationResult);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          project_id: "my-app",
          name: "my-app",
          description: "desc",
        }),
      }),
    );
  });

  it("throws on conflict", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 409,
      text: () => Promise.resolve("Project already exists"),
    });

    await expect(api.projects.create("existing", "")).rejects.toThrow(
      "API 409",
    );
  });
});

describe("api.orchestrator.run", () => {
  it("sends POST with project_id and ticket_id", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          ticket_id: "ticket-001",
          final_status: "done",
          rounds: 1,
          approved: true,
        }),
    });

    const result = await api.orchestrator.run("ide-core", "ticket-001");

    expect(result.approved).toBe(true);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/orchestrator/run",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          project_id: "ide-core",
          ticket_id: "ticket-001",
        }),
      }),
    );
  });
});

describe("api.runs.list", () => {
  it("calls the correct endpoint with default limit", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve([]) });
    await api.runs.list("ide-core");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects/ide-core/runs?limit=20",
      undefined,
    );
  });

  it("respects custom limit", async () => {
    mockFetch.mockResolvedValue({ ok: true, json: () => Promise.resolve([]) });
    await api.runs.list("ide-core", 5);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects/ide-core/runs?limit=5",
      undefined,
    );
  });
});

describe("api.usage.get", () => {
  it("calls the usage endpoint for the project", async () => {
    const usage = {
      total_cost_usd: 0.01,
      total_tokens: 1000,
      total_runs: 1,
      per_ticket: [],
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(usage),
    });
    const result = await api.usage.get("ide-core");
    expect(result).toEqual(usage);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects/ide-core/usage",
      undefined,
    );
  });
});

describe("api.tickets.create", () => {
  it("POSTs a new ticket", async () => {
    const ticket = {
      id: "ticket-001",
      title: "Fix bug",
      status: "todo",
      description: "",
    };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(ticket),
    });
    const result = await api.tickets.create("ide-core", {
      title: "Fix bug",
      description: "",
    });
    expect(result).toEqual(ticket);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects/ide-core/tickets",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("api.agents.list", () => {
  it("returns the agents array from the registry response", async () => {
    const agents = [{ role: "coder", model: "claude-sonnet-4-6" }];
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ agents }),
    });
    const result = await api.agents.list();
    expect(result).toEqual(agents);
  });
});

describe("api.github.createPr", () => {
  it("POSTs to the create-pr endpoint", async () => {
    const pr = { pr_url: "https://github.com/foo/bar/pull/1", pr_number: 1 };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(pr),
    });
    const result = await api.github.createPr(
      "ide-core",
      "ticket-001",
      "ticket-001-fix",
    );
    expect(result).toEqual(pr);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects/ide-core/tickets/ticket-001/create-pr",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ head_branch: "ticket-001-fix", base: "develop" }),
      }),
    );
  });
});

describe("api.github.getPrStatus", () => {
  it("calls the pr-status endpoint", async () => {
    const status = { state: "open", pr_number: 1 };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(status),
    });
    const result = await api.github.getPrStatus("ide-core", "ticket-001");
    expect(result).toEqual(status);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects/ide-core/tickets/ticket-001/pr-status",
      undefined,
    );
  });
});

describe("api.agents.remove", () => {
  it("sends DELETE to the registry endpoint", async () => {
    mockFetch.mockResolvedValue({ ok: true });
    await api.agents.remove("coder");
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/agents/registry/coder",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("throws on non-ok DELETE", async () => {
    mockFetch.mockResolvedValue({
      ok: false,
      status: 404,
      text: () => Promise.resolve("Not Found"),
    });
    await expect(api.agents.remove("ghost")).rejects.toThrow("API 404");
  });
});

describe("api.projects.import", () => {
  it("POSTs to the import endpoint", async () => {
    const response = { project: { id: "imported" }, agents_created: [] };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(response),
    });
    const result = await api.projects.import({ source_path: "/local/project", mode: "copy" });
    expect(result).toEqual(response);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects/import",
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("api.tickets.batch", () => {
  it("POSTs multiple tickets at once", async () => {
    const response = { created: [], errors: [] };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(response),
    });
    const result = await api.tickets.batch("ide-core", [
      {
        title: "T1",
        type: "feat",
        priority: "medium",
        agent: "codeur",
        description: "",
        acceptance_criteria: [],
        depends_on_index: [],
      },
    ]);
    expect(result).toEqual(response);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects/ide-core/tickets/batch",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
