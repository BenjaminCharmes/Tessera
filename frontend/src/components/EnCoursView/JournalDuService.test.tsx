import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { ServiceActif } from "../../types/api";
import JournalDuService from "./JournalDuService";

function service(over: Partial<ServiceActif>): ServiceActif {
  return {
    nom: "api",
    project_id: "demo",
    pid: 1,
    demarre_a: "2026-01-01T00:00:00Z",
    en_cours: true,
    code_de_sortie: null,
    sortie: [],
    arrete_a_la_main: false,
    ...over,
  };
}

describe("JournalDuService", () => {
  it("numbers lines after the ones the backend buffer dropped", () => {
    render(
      <JournalDuService
        projectName="Demo"
        service={service({ sortie: ["a", "b"], lignes_ecartees: 30 })}
        onFermer={() => undefined}
      />,
    );
    expect(screen.getByText("31")).toBeTruthy();
    expect(screen.getByText("32")).toBeTruthy();
  });

  it("does not count a clean build line as an error", () => {
    render(
      <JournalDuService
        projectName="Demo"
        service={service({ sortie: ["✓ built, 0 error", "Error: boom"] })}
        onFermer={() => undefined}
      />,
    );
    expect(screen.getByText("Erreurs · 1")).toBeTruthy();
  });
});
