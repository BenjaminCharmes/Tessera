import { describe, expect, it } from "vitest";
import type { PipelineRun } from "../../types/api";
import type { VentilationDuProjet } from "../ventilation";
import { ventilation } from "../../test/contrat/exemples";
import { ligneDesRuns, ligneDuCout, lignesDuBilan } from "./bilanDeLAgent";
import { weekRunCount } from "./weekEmployee";

const MAINTENANT = Date.parse("2026-10-23T10:00:00.000Z");

function run(debut: string, tours: number | null, approuve: boolean | null, ticket = "ticket-001"): PipelineRun {
  return {
    id: `${ticket}-${debut}`,
    ticket_id: ticket,
    started_at: debut,
    finished_at: null,
    rounds: tours,
    approved: approuve,
    final_status: null,
    total_cost_usd: 0,
  };
}

const VENTILATION: VentilationDuProjet = ventilation({
  per_agent: [{ role: "codeur", total_cost_usd: 0.9, total_tokens: 10, call_count: 2 }],
});

describe("weekRunCount", () => {
  it("counts the runs started in the last 7 days, whatever their outcome", () => {
    const runs = [
      run("2026-10-22T10:00:00.000Z", 1, true),
      run("2026-10-20T10:00:00.000Z", null, null),
      run("2026-10-10T10:00:00.000Z", 1, true),
      run("2026-10-24T10:00:00.000Z", 1, true),
    ];

    expect(weekRunCount(runs, MAINTENANT)).toBe(2);
  });
});

describe("ligneDesRuns", () => {
  it("says how many runs of the week, and how many were approved on the first round", () => {
    const runs = [
      run("2026-10-22T10:00:00.000Z", 1, true, "ticket-001"),
      run("2026-10-21T10:00:00.000Z", 2, true, "ticket-002"),
    ];

    expect(ligneDesRuns(runs, MAINTENANT)).toEqual({
      libelle: "Runs de la semaine",
      valeur: "2, dont 1 approuvé au premier tour",
    });
  });

  it("writes zero first-round approvals when runs exist but none passed at once", () => {
    const ligne = ligneDesRuns([run("2026-10-22T10:00:00.000Z", 2, false)], MAINTENANT);

    expect(ligne?.valeur).toBe("1, dont 0 approuvé au premier tour");
  });

  it("gives no line without a reading or without a run this week", () => {
    expect(ligneDesRuns(null, MAINTENANT)).toBeNull();
    expect(ligneDesRuns([], MAINTENANT)).toBeNull();
    expect(ligneDesRuns([run("2026-09-01T10:00:00.000Z", 1, true)], MAINTENANT)).toBeNull();
  });
});

describe("ligneDuCout", () => {
  it("reads the role's cumulated cost in the breakdown", () => {
    expect(ligneDuCout(VENTILATION, "codeur")).toEqual({ libelle: "Coût cumulé", valeur: "0,90 $" });
  });

  it("gives no line without a reading or without a call of that role", () => {
    expect(ligneDuCout(null, "codeur")).toBeNull();
    expect(ligneDuCout(VENTILATION, "reviewer")).toBeNull();
  });
});

describe("lignesDuBilan", () => {
  it("keeps the cost line when the runs reading is missing, and the reverse", () => {
    const runs = [run("2026-10-22T10:00:00.000Z", 1, true)];

    expect(lignesDuBilan(null, VENTILATION, "codeur", MAINTENANT).map((l) => l.libelle)).toEqual(["Coût cumulé"]);
    expect(lignesDuBilan(runs, null, "codeur", MAINTENANT).map((l) => l.libelle)).toEqual(["Runs de la semaine"]);
    expect(lignesDuBilan(null, null, "codeur", MAINTENANT)).toEqual([]);
  });
});
