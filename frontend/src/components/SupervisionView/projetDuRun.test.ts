import { describe, it, expect } from "vitest";
import { projetDuRun } from "./projetDuRun";
import type { Project, RunActif } from "../../types/api";

function projet(over: Partial<Project> = {}): Project {
  return {
    id: "demineur",
    name: "Démineur",
    path: "C:/p/demineur",
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
    ...over,
  };
}

function run(over: Partial<RunActif> = {}): RunActif {
  return {
    run_id: "r1",
    project_id: "demineur",
    mode: "single",
    ticket_id: "ticket-001",
    etape: null,
    agent: null,
    tour: 0,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    question: null,
    demarre_a: new Date().toISOString(),
    ...over,
  };
}

describe("projetDuRun (ticket-164)", () => {
  it("rend le projet de la liste quand il y est", () => {
    expect(projetDuRun([projet()], run())?.name).toBe("Démineur");
  });

  it("rend un projet minimal quand la liste ne le porte pas", () => {
    // Le panneau recevait `null` et affichait « sélectionne un projet » alors
    // qu'un run était sélectionné. La carte sait de quel projet il s'agit.
    const p = projetDuRun([], run());

    expect(p).not.toBeNull();
    expect(p?.id).toBe("demineur");
  });

  it("sans run, il n'y a rien à montrer", () => {
    expect(projetDuRun([projet()], null)).toBeNull();
  });
});
