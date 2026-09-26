import { describe, expect, it } from "vitest";
import { FILTRES_VIDES, appliquerFiltres, filtrerParStatut } from "./filtresTickets";
import type { Ticket } from "../types/api";

function ticket(partiel: Partial<Ticket> & { id: string }): Ticket {
  return {
    title: "",
    type: "feat",
    status: "todo",
    priority: "medium",
    agent: "codeur",
    depends_on: [],
    created: "2026-09-01",
    github_issue_url: null,
    pr_number: null,
    body: "",
    project_id: "p",
    file_path: "",
    ...partiel,
  };
}

const TICKETS = [
  ticket({ id: "ticket-012", title: "Notifications système", priority: "low", created: "2026-09-03" }),
  ticket({ id: "ticket-003", title: "Carte du dépôt", priority: "critical", type: "fix", created: "2026-09-02", body: "Glob partout" }),
  ticket({ id: "ticket-007", title: "Filtres", priority: "high", status: "done", created: "2026-09-01", agent: "architect" }),
];

describe("appliquerFiltres", () => {
  it("cherche sur un fragment d'id, du titre et du corps", () => {
    expect(appliquerFiltres(TICKETS, { ...FILTRES_VIDES, texte: "003" }).map((t) => t.id)).toEqual(["ticket-003"]);
    expect(appliquerFiltres(TICKETS, { ...FILTRES_VIDES, texte: "notif" }).map((t) => t.id)).toEqual(["ticket-012"]);
    expect(appliquerFiltres(TICKETS, { ...FILTRES_VIDES, texte: "glob" }).map((t) => t.id)).toEqual(["ticket-003"]);
  });

  it("combine un filtre par priorite et un tri par numero", () => {
    const ids = appliquerFiltres(TICKETS, { ...FILTRES_VIDES, priorite: "high", tri: "numero" }).map((t) => t.id);
    expect(ids).toEqual(["ticket-007"]);
    const tous = appliquerFiltres(TICKETS, { ...FILTRES_VIDES, tri: "numero" }).map((t) => t.id);
    expect(tous).toEqual(["ticket-003", "ticket-007", "ticket-012"]);
  });

  it("trie par priorite, la critique d'abord", () => {
    expect(appliquerFiltres(TICKETS, { ...FILTRES_VIDES, tri: "priorite" }).map((t) => t.id)).toEqual([
      "ticket-003", "ticket-007", "ticket-012",
    ]);
  });

  it("trie par date, le plus recent d'abord", () => {
    expect(appliquerFiltres(TICKETS, { ...FILTRES_VIDES, tri: "date" }).map((t) => t.id)).toEqual([
      "ticket-012", "ticket-003", "ticket-007",
    ]);
  });

  it("filtre par type et par agent", () => {
    expect(appliquerFiltres(TICKETS, { ...FILTRES_VIDES, type: "fix" }).map((t) => t.id)).toEqual(["ticket-003"]);
    expect(appliquerFiltres(TICKETS, { ...FILTRES_VIDES, agent: "architect" }).map((t) => t.id)).toEqual(["ticket-007"]);
  });
});

describe("filtrerParStatut", () => {
  it("dit combien les filtres cachent", () => {
    // Une liste vide sans explication se lit comme un projet sans tickets.
    const r = filtrerParStatut(TICKETS, { ...FILTRES_VIDES, texte: "introuvable" });
    expect(r.retenus).toBe(0);
    expect(r.total).toBe(3);
    expect(r.byStatus.todo).toEqual([]);
  });
});
