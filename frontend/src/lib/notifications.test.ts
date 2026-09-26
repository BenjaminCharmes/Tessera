import { describe, expect, it } from "vitest";
import { notificationsPour, type Instantane } from "./notifications";
import { INITIAL } from "../hooks/streamState";
import type { RunActif } from "../types/api";

function run(id: string, project = "demineur"): RunActif {
  return {
    run_id: id, project_id: project, mode: "single", ticket_id: "ticket-004",
    etape: null, agent: null, tour: 1, tokens_entree: 0, tokens_sortie: 0,
    cout_usd: 0, verdict: null, demarre_a: "2026-09-26T08:00:00Z",
  };
}

const AILLEURS = { projetActif: "ide-core", visible: true };
const VIDE: Instantane = { runs: [], etats: {} };

describe("notificationsPour", () => {
  it("annonce une question d'agent en nommant le projet et le ticket", () => {
    // Une question expire (ADR-025) pendant qu'on est ailleurs : c'est le cas
    // que le ticket existe pour couvrir.
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running" } } };
    const apres: Instantane = {
      runs: [run("r1")],
      etats: { r1: { ...INITIAL, status: "running", pendingQuestion: "On casse l'API ?" } },
    };
    const [n] = notificationsPour(avant, apres, AILLEURS);
    expect(n.titre).toBe("demineur · ticket-004 : un agent pose une question");
    expect(n.corps).toBe("On casse l'API ?");
  });

  it("n'annonce rien pour un agent qui finit son tour", () => {
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running", currentAgent: "codeur" } } };
    const apres: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running", currentAgent: null, appels: 1 } } };
    expect(notificationsPour(avant, apres, AILLEURS)).toEqual([]);
  });

  it("annonce un run bloqué et un run terminé", () => {
    const bloque = notificationsPour(
      { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running" } } },
      { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "error", errorMessage: "budget" } } },
      AILLEURS,
    );
    expect(bloque[0].titre).toMatch(/bloqué/);

    const fini = notificationsPour(
      {
        runs: [run("r1")],
        etats: { r1: { ...INITIAL, status: "done", lastResult: { ticket_id: "ticket-004", final_status: "done", rounds: 2, approved: true } as never } },
      },
      VIDE,
      AILLEURS,
    );
    expect(fini[0].titre).toBe("demineur · ticket-004 : terminé");
    expect(fini[0].corps).toBe("ticket-004 approuvé en 2 tours");
  });

  it("se tait quand la fenêtre est visible et le projet affiché", () => {
    const avant: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running" } } };
    const apres: Instantane = { runs: [run("r1")], etats: { r1: { ...INITIAL, status: "running", pendingQuestion: "?" } } };
    expect(notificationsPour(avant, apres, { projetActif: "demineur", visible: true })).toEqual([]);
    expect(notificationsPour(avant, apres, { projetActif: "demineur", visible: false })).toHaveLength(1);
  });
});
