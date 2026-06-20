import { describe, it, expect } from "vitest";
import { moveTicket, groupByStatus } from "./ticketBoard";
import type { ByStatus } from "./ticketBoard";
import type { Ticket } from "../types/api";

function makeTicket(id: string, status: Ticket["status"]): Ticket {
  return {
    id,
    title: `Ticket ${id}`,
    type: "feat",
    status,
    priority: "medium",
    agent: "codeur",
    depends_on: [],
    created: "2026-06-20",
    github_issue_url: null,
    body: "",
    project_id: "test",
    file_path: `/tmp/${id}.md`,
  };
}

const t1 = makeTicket("ticket-001", "todo");
const t2 = makeTicket("ticket-002", "in-progress");
const t3 = makeTicket("ticket-003", "done");

const BASE: ByStatus = {
  todo: [t1],
  "in-progress": [t2],
  "in-review": [],
  done: [t3],
  blocked: [],
  cancelled: [],
};

describe("moveTicket", () => {
  it("moves a ticket from todo to in-progress", () => {
    const result = moveTicket(BASE, "ticket-001", "in-progress");

    expect(result.todo).toHaveLength(0);
    expect(result["in-progress"]).toHaveLength(2);
    expect(result["in-progress"].some((t) => t.id === "ticket-001")).toBe(true);
  });

  it("updates the ticket status field on the moved ticket", () => {
    const result = moveTicket(BASE, "ticket-001", "in-review");

    const moved = result["in-review"].find((t) => t.id === "ticket-001");
    expect(moved?.status).toBe("in-review");
  });

  it("does not mutate the input byStatus object", () => {
    const before = { ...BASE, todo: [...BASE.todo] };
    moveTicket(BASE, "ticket-001", "done");

    expect(BASE.todo).toHaveLength(1);
    expect(BASE.todo).toEqual(before.todo);
  });

  it("does not mutate peer buckets", () => {
    const originalInProgress = BASE["in-progress"];
    const result = moveTicket(BASE, "ticket-001", "done");

    expect(result["in-progress"]).not.toBe(originalInProgress);
    expect(result["in-progress"]).toEqual(originalInProgress);
  });

  it("returns unchanged object when ticket is not found", () => {
    const result = moveTicket(BASE, "ticket-999", "done");

    expect(result).toBe(BASE);
  });

  it("handles moving to the same status gracefully", () => {
    const result = moveTicket(BASE, "ticket-001", "todo");

    expect(result.todo).toHaveLength(1);
    expect(result.todo[0].id).toBe("ticket-001");
  });
});

describe("groupByStatus", () => {
  it("groups tickets by their status", () => {
    const tickets = [t1, t2, t3];
    const result = groupByStatus(tickets);

    expect(result.todo).toEqual([t1]);
    expect(result["in-progress"]).toEqual([t2]);
    expect(result.done).toEqual([t3]);
    expect(result["in-review"]).toHaveLength(0);
  });
});
