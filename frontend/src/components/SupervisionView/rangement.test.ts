import { describe, expect, it } from "vitest";
import { entreesDuMenu, idsARanger, runsClosDe } from "./rangement";
import { INITIAL } from "../../hooks/streamState";
import type { StreamState } from "../../hooks/streamState";
import type { RunActif } from "../../types/api";

function run(runId: string): RunActif {
  return {
    run_id: runId,
    project_id: "p",
    mode: "single",
    ticket_id: null,
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

function fini(finalStatus: string): StreamState {
  const evenement = {
    type: "pipeline_done" as const,
    agent: null,
    ticket_id: "ticket-001",
    data: { final_status: finalStatus },
    timestamp: "2026-10-26T10:00:00.000Z",
  };
  return { ...INITIAL, runClosed: true, events: [evenement] };
}

const ETATS: Record<string, StreamState> = {
  vivant: INITIAL,
  ok: fini("done"),
  bloque: fini("blocked"),
};
const etatDe = (runId: string) => ETATS[runId] ?? INITIAL;
const RUNS = [run("vivant"), run("ok"), run("bloque")];

describe("rangement", () => {
  it("keeps only closed runs", () => {
    expect(runsClosDe(RUNS, etatDe).map((r) => r.run_id)).toEqual(["ok", "bloque"]);
  });

  it("selects the runs of one outcome, or all the closed ones", () => {
    expect(idsARanger(RUNS, etatDe, "bloque")).toEqual(["bloque"]);
    expect(idsARanger(RUNS, etatDe, null)).toEqual(["ok", "bloque"]);
    expect(idsARanger(RUNS, etatDe, "erreur")).toEqual([]);
  });

  it("counts each outcome in the menu entries", () => {
    const comptes = entreesDuMenu(RUNS, etatDe).map((e) => [e.issue, e.count]);

    expect(comptes).toEqual([["termine", 1], ["bloque", 1], ["erreur", 0], [null, 2]]);
  });
});
