import { describe, expect, it } from "vitest";
import { projetsDuBureau } from "./projetsDuBureau";
import { INITIAL } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";

function run(runId: string, projet: string, mode = "single"): RunActif {
  return {
    run_id: runId,
    project_id: projet,
    mode,
    ticket_id: "ticket-001",
    etape: null,
    agent: null,
    tour: 0,
    tokens_entree: 0,
    tokens_sortie: 0,
    cout_usd: 0,
    verdict: null,
    demarre_a: "2026-10-26T10:00:00.000Z",
  };
}

const etatDe = (runId: string): StreamState => ({ ...INITIAL, currentAgent: runId === "a" ? "codeur" : null });

describe("projetsDuBureau", () => {
  it("returns one project per project with a run, in order of appearance", () => {
    const { projets } = projetsDuBureau([run("a", "x"), run("b", "y")], etatDe, ["x", "y"]);

    expect(projets.map((p) => p.nom)).toEqual(["x", "y"]);
    expect(projets[0]).toMatchObject({ runId: "a", run: run("a", "x") });
    expect(projets[0]?.etat.currentAgent).toBe("codeur");
  });

  it("lists the known projects without a run as at rest", () => {
    const { auRepos } = projetsDuBureau([run("a", "x")], etatDe, ["x", "y", "z"]);

    expect(auRepos).toEqual(["y", "z"]);
  });

  it("prefers the pipeline run over a chat run, whatever their order", () => {
    const chatPuisPipeline = projetsDuBureau([run("c", "x", "chat"), run("p", "x")], etatDe, ["x"]);
    const pipelinePuisChat = projetsDuBureau([run("p", "x"), run("c", "x", "chat")], etatDe, ["x"]);

    expect(chatPuisPipeline.projets).toHaveLength(1);
    expect(chatPuisPipeline.projets[0]?.runId).toBe("p");
    expect(pipelinePuisChat.projets[0]?.runId).toBe("p");
  });

  it("keeps a lone chat run", () => {
    const { projets } = projetsDuBureau([run("c", "x", "chat")], etatDe, ["x"]);

    expect(projets[0]?.runId).toBe("c");
  });

  it("returns nothing for no run", () => {
    expect(projetsDuBureau([], etatDe, ["x"])).toEqual({ projets: [], auRepos: ["x"] });
  });
});
