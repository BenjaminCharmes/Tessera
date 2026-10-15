import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useActionOuvrirTicket } from "./useOuvrirTicket";
import type { PrisesDuCockpit } from "./useOuvrirTicket";
import type { Project, Ticket } from "../types/api";

const { list } = vi.hoisted(() => ({ list: vi.fn() }));
vi.mock("../lib/api", () => ({ api: { tickets: { list } } }));

function projet(id: string): Project {
  return {
    id,
    name: id,
    path: `/workspace/${id}`,
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
    category: null,
  };
}

function ticket(id: string): Ticket {
  return {
    id,
    title: id,
    status: "done",
    type: "feat",
    priority: "medium",
    agent: "codeur",
    depends_on: [],
    created: "2026-10-01T00:00:00Z",
    github_issue_url: null,
    pr_number: null,
    body: "",
    project_id: "p1",
    file_path: "",
  };
}

function prises(actif: string | null): PrisesDuCockpit {
  return {
    projets: [projet("p1"), projet("p2")],
    projetActifId: actif,
    selectionnerProjet: vi.fn(),
    selectionnerTicket: vi.fn(),
    afficherLesTickets: vi.fn(),
  };
}

beforeEach(() => {
  list.mockReset();
  list.mockResolvedValue({ tickets: [ticket("ticket-1")], unreadable: [] });
});

describe("useActionOuvrirTicket (ticket-460)", () => {
  it("selects the ticket and shows the Tickets tab, in the active project", async () => {
    const cockpit = prises("p1");
    const { result } = renderHook(() => useActionOuvrirTicket(cockpit));

    expect(await result.current("p1", "ticket-1")).toBe("ok");

    expect(list).toHaveBeenCalledWith("p1");
    expect(cockpit.selectionnerProjet).not.toHaveBeenCalled();
    expect(cockpit.selectionnerTicket).toHaveBeenCalledWith(ticket("ticket-1"));
    expect(cockpit.afficherLesTickets).toHaveBeenCalledOnce();
  });

  it("activates another project before it selects the ticket", async () => {
    const cockpit = prises("p2");
    const { result } = renderHook(() => useActionOuvrirTicket(cockpit));

    expect(await result.current("p1", "ticket-1")).toBe("ok");

    expect(cockpit.selectionnerProjet).toHaveBeenCalledWith(projet("p1"));
    const [ordreProjet] = vi.mocked(cockpit.selectionnerProjet).mock.invocationCallOrder;
    const [ordreTicket] = vi.mocked(cockpit.selectionnerTicket).mock.invocationCallOrder;
    expect(ordreProjet).toBeLessThan(ordreTicket);
  });

  it("reports a missing ticket and changes nothing", async () => {
    const cockpit = prises("p2");
    const { result } = renderHook(() => useActionOuvrirTicket(cockpit));

    expect(await result.current("p1", "ticket-9")).toBe("introuvable");

    expect(cockpit.selectionnerProjet).not.toHaveBeenCalled();
    expect(cockpit.selectionnerTicket).not.toHaveBeenCalled();
    expect(cockpit.afficherLesTickets).not.toHaveBeenCalled();
  });

  it("reports a missing ticket when the API fails, without throwing", async () => {
    list.mockRejectedValue(new Error("down"));
    const cockpit = prises("p1");
    const { result } = renderHook(() => useActionOuvrirTicket(cockpit));

    expect(await result.current("p1", "ticket-1")).toBe("introuvable");
    expect(cockpit.selectionnerTicket).not.toHaveBeenCalled();
  });

  it("reports an unknown project without calling the API", async () => {
    const cockpit = prises("p1");
    const { result } = renderHook(() => useActionOuvrirTicket(cockpit));

    expect(await result.current("ghost", "ticket-1")).toBe("introuvable");
    expect(list).not.toHaveBeenCalled();
  });

  it("keeps the same function across renders and uses the latest handlers", async () => {
    const premiere = prises("p1");
    const { result, rerender } = renderHook(
      ({ cockpit }) => useActionOuvrirTicket(cockpit),
      { initialProps: { cockpit: premiere } },
    );
    const action = result.current;
    const suivante = prises("p1");

    rerender({ cockpit: suivante });
    await result.current("p1", "ticket-1");

    expect(result.current).toBe(action);
    expect(suivante.selectionnerTicket).toHaveBeenCalledOnce();
    expect(premiere.selectionnerTicket).not.toHaveBeenCalled();
  });
});
