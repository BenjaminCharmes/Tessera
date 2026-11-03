import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { NOM_DES_RH, NOM_DU_DIRECTEUR, nomDeLAgent } from "../../lib/bureau/noms";
import AgentsDeLaPiece from "./AgentsDeLaPiece";
import BureauDuDirecteur from "./BureauDuDirecteur";
import SalleRh from "./SalleRh";

const T0 = Date.parse("2026-10-27T10:00:00.000Z");

describe("Names on hover, away from the desk", () => {
  it("gives a standing agent the same hover text as its aria-label, and takes the pointer back", () => {
    const { container } = render(
      <AgentsDeLaPiece
        projet="alpha"
        agents={[{ poste: "testeur", x: 100, decalage: 0, niveau: "rangee", activite: "tasse", parti: false }]}
      />,
    );
    const agent = container.querySelector<HTMLElement>('[data-agent="testeur"]');

    expect(agent?.getAttribute("title")).toBe(agent?.getAttribute("aria-label"));
    expect(agent?.getAttribute("title")).toContain(nomDeLAgent("alpha", "testeur"));
    expect(agent?.className).toContain("pointer-events-auto");
  });

  it("gives a departed agent no hover text", () => {
    const { container } = render(
      <AgentsDeLaPiece
        projet="alpha"
        agents={[{ poste: "testeur", x: 100, decalage: 0, niveau: "rangee", activite: null, parti: true }]}
      />,
    );

    expect(container.querySelector('[data-agent="testeur"]')?.hasAttribute("title")).toBe(false);
  });

  it("names the director, and the visitor with its project", () => {
    const { container } = render(
      <BureauDuDirecteur agents={[{ projet: "alpha", poste: "codeur" }]} maintenant={T0} />,
    );

    expect(container.querySelector(`[title="${NOM_DU_DIRECTEUR}, directeur"]`)).not.toBeNull();
    const visiteur = container.querySelector('[data-agent="codeur"]')?.getAttribute("title");
    expect(visiteur).toContain(nomDeLAgent("alpha", "codeur"));
    expect(visiteur).toContain("alpha");
  });

  it("names the HR person", () => {
    const { container } = render(<SalleRh agents={[]} maintenant={T0} />);

    expect(container.querySelector(`[title="${NOM_DES_RH}, RH"]`)).not.toBeNull();
  });
});
