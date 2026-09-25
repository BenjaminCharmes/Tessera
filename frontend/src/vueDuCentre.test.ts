import { describe, it, expect } from "vitest";
import { vueDuCentre } from "./vueDuCentre";

describe("vueDuCentre (ticket-178)", () => {
  it("montre le run quand il démarre, sans qu'on le demande", () => {
    expect(
      vueDuCentre({
        runEnCours: true,
        runAuPremierPlan: true,
        openFilePath: null,
        showDiff: false,
        showKanban: true,
      }),
    ).toBe("run");
  });

  it("rend le centre au tableau quand on le demande, run ou pas", () => {
    // La cascade testait `RunView` en premier : « Vue tableau » n'avait aucun
    // effet tant qu'un run tournait, sans que rien ne l'explique.
    expect(
      vueDuCentre({
        runEnCours: true,
        runAuPremierPlan: false,
        openFilePath: null,
        showDiff: false,
        showKanban: true,
      }),
    ).toBe("kanban");
  });

  it("rend le centre à l'éditeur quand on a quitté le tableau", () => {
    expect(
      vueDuCentre({
        runEnCours: true,
        runAuPremierPlan: false,
        openFilePath: null,
        showDiff: false,
        showKanban: false,
      }),
    ).toBe("editor");
  });

  it("un fichier ouvert garde la main", () => {
    expect(
      vueDuCentre({
        runEnCours: true,
        runAuPremierPlan: true,
        openFilePath: "src/a.ts",
        showDiff: false,
        showKanban: true,
      }),
    ).toBe("editor");
  });

  it("un diff demandé garde la main", () => {
    expect(
      vueDuCentre({
        runEnCours: true,
        runAuPremierPlan: true,
        openFilePath: null,
        showDiff: true,
        showKanban: true,
      }),
    ).toBe("diff");
  });

  it("sans run, le premier plan ne ramène rien", () => {
    // La fin d'un run ne doit pas rouvrir une vue qu'on venait de quitter.
    expect(
      vueDuCentre({
        runEnCours: false,
        runAuPremierPlan: true,
        openFilePath: null,
        showDiff: false,
        showKanban: true,
      }),
    ).toBe("kanban");
  });
});
