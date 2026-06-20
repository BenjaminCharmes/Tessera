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
  it("sends POST with name and description", async () => {
    const project = { id: "my-app", name: "my-app", description: "desc" };
    mockFetch.mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(project),
    });

    const result = await api.projects.create("my-app", "desc");

    expect(result).toEqual(project);
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/v1/projects",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ name: "my-app", description: "desc" }),
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
