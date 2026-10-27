import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen, within } from "@testing-library/react";
import TableauDesCriteres from "./TableauDesCriteres";
import { api } from "../../lib/api";
import { INITIAL, applyEvent } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { EventType, Ticket } from "../../types/api";

function etatApres(evenements: { type: EventType; data?: Record<string, unknown> }[]): StreamState {
  return evenements.reduce<StreamState>(
    (s, e) =>
      applyEvent(s, {
        type: e.type,
        agent: null,
        ticket_id: "ticket-001",
        data: e.data ?? {},
        timestamp: "2026-10-27T10:00:00.000Z",
      }),
    INITIAL,
  );
}

function verdict(passes: boolean[]): { type: EventType; data: Record<string, unknown> } {
  return {
    type: "validation_done",
    data: { criteria: passes.map((passed, i) => ({ criterion: `Critère ${i + 1} du ticket`, passed, note: "" })) },
  };
}

function ticket(corps: string): Ticket {
  return {
    id: "ticket-001",
    title: "Titre",
    type: "feat",
    status: "in-progress",
    priority: "medium",
    agent: "codeur",
    depends_on: [],
    created: "2026-10-27",
    github_issue_url: null,
    pr_number: null,
    body: corps,
    project_id: "ide-core",
    file_path: "/tmp/ticket-001.md",
  };
}

const CORPS = "## Critères d'acceptation\n- [ ] Un\n- [ ] Deux\n- [ ] Trois\n";

function cases(conteneur: HTMLElement, etat: string): number {
  return conteneur.querySelectorAll(`[data-case="${etat}"]`).length;
}

beforeEach(() => {
  vi.spyOn(api.tickets, "list").mockResolvedValue({ tickets: [], unreadable: [] });
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("TableauDesCriteres", () => {
  it("draws four green lines and one red after a verdict of five criteria, four passed", () => {
    const etat = etatApres([verdict([true, true, false, true, true])]);

    const { container } = render(<TableauDesCriteres projet="ide-core" etat={etat} />);

    expect(cases(container, "passe")).toBe(4);
    expect(cases(container, "echoue")).toBe(1);
    expect(cases(container, "attente")).toBe(0);
    expect(screen.getByRole("group", { name: "Tableau blanc : 4 critères sur 5 validés" })).toBeInTheDocument();
  });

  it("reads no ticket file once the verdict is in", () => {
    render(<TableauDesCriteres projet="ide-core" etat={etatApres([verdict([true])])} />);

    expect(api.tickets.list).not.toHaveBeenCalled();
  });

  it("renders a blank board with no line when neither a verdict nor a count is known", () => {
    const { container } = render(<TableauDesCriteres projet="ide-core" etat={INITIAL} />);

    expect(container.querySelector('[data-sprite="tableau-blanc"]')).not.toBeNull();
    expect(container.querySelectorAll("[data-case]")).toHaveLength(0);
    expect(screen.getByRole("img", { name: "Tableau blanc : aucun critère connu" })).toBeInTheDocument();
    expect(api.tickets.list).not.toHaveBeenCalled();
  });

  it("lists each criterion with its state in the tooltip on focus", () => {
    const etat = etatApres([verdict([true, false])]);
    render(<TableauDesCriteres projet="ide-core" etat={etat} />);

    act(() => screen.getByRole("group", { name: "Tableau blanc : 1 critère sur 2 validés" }).focus());

    const lignes = within(screen.getByRole("tooltip")).getAllByRole("listitem");
    expect(lignes.map((li) => li.textContent)).toEqual([
      "Critère 1 du ticket — validé",
      "Critère 2 du ticket — refusé",
    ]);
  });

  it("hides the tooltip when the board loses focus", () => {
    render(<TableauDesCriteres projet="ide-core" etat={etatApres([verdict([true])])} />);
    const tableau = screen.getByRole("group", { name: "Tableau blanc : 1 critère sur 1 validés" });
    act(() => tableau.focus());
    act(() => tableau.blur());

    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
  });

  it("draws one grey line per criterion of the ticket file before the verdict", async () => {
    vi.spyOn(api.tickets, "list").mockResolvedValue({ tickets: [ticket(CORPS)], unreadable: [] });
    const etat = etatApres([{ type: "agent_started" }]);

    const { container } = render(<TableauDesCriteres projet="ide-core" etat={etat} />);

    expect(await screen.findByRole("group", { name: "Tableau blanc : 0 critère sur 3 validés" })).toBeInTheDocument();
    expect(cases(container, "attente")).toBe(3);
    expect(api.tickets.list).toHaveBeenCalledWith("ide-core");
  });

  it("names the criteria of the file in the tooltip, still unjudged", async () => {
    vi.spyOn(api.tickets, "list").mockResolvedValue({ tickets: [ticket(CORPS)], unreadable: [] });
    render(<TableauDesCriteres projet="ide-core" etat={etatApres([{ type: "agent_started" }])} />);

    const tableau = await screen.findByRole("group", { name: "Tableau blanc : 0 critère sur 3 validés" });
    act(() => tableau.focus());

    const lignes = within(screen.getByRole("tooltip")).getAllByRole("listitem");
    expect(lignes[0]?.textContent).toBe("Un — pas encore jugé");
  });

  it("stays blank when the ticket file has no acceptance section", async () => {
    vi.spyOn(api.tickets, "list").mockResolvedValue({ tickets: [ticket("rien")], unreadable: [] });

    const { container } = render(
      <TableauDesCriteres projet="ide-core" etat={etatApres([{ type: "agent_started" }])} />,
    );
    await act(async () => {});

    expect(container.querySelectorAll("[data-case]")).toHaveLength(0);
  });

  it("draws at most twelve lines but counts every criterion", () => {
    const etat = etatApres([verdict(Array.from({ length: 14 }, () => true))]);

    const { container } = render(<TableauDesCriteres projet="ide-core" etat={etat} />);

    expect(cases(container, "passe")).toBe(12);
    expect(screen.getByRole("group", { name: "Tableau blanc : 14 critères sur 14 validés" })).toBeInTheDocument();
  });
});
