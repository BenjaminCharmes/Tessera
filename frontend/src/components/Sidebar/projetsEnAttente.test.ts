import { describe, expect, it } from "vitest";
import { projetsEnAttente } from "./projetsEnAttente";

const RUNS = [
  { run_id: "r1", project_id: "demineur" },
  { run_id: "r2", project_id: "ide-core" },
];

describe("projetsEnAttente", () => {
  it("retient le projet dont le run attend", () => {
    const attendent = projetsEnAttente(RUNS, (id) =>
      id === "r2" ? "on casse l'API ?" : null,
    );

    expect([...attendent]).toEqual(["ide-core"]);
  });

  it("ne retient rien quand aucun run n'attend", () => {
    expect(projetsEnAttente(RUNS, () => null).size).toBe(0);
  });

  it("ne compte un projet qu'une fois", () => {
    // ADR-038 n'autorise qu'un run par projet, mais un run fermé peut encore
    // figurer dans la liste le temps d'un événement.
    const doublon = [
      { run_id: "r1", project_id: "demineur" },
      { run_id: "r3", project_id: "demineur" },
    ];

    expect(projetsEnAttente(doublon, () => "?").size).toBe(1);
  });
});
