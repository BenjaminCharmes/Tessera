import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import TableauBlanc from "./TableauBlanc";

function marques(conteneur: HTMLElement, etat: string): number {
  // La case vide fait deux rectangles ; une case jugée ajoute son fond et ses pixels de marque.
  const groupe = conteneur.querySelector(`[data-case="${etat}"]`);
  return groupe ? groupe.querySelectorAll("rect").length : 0;
}

describe("TableauBlanc", () => {
  it("draws an empty box before judgement, a tick when the criterion passes and a cross when it fails", () => {
    const { container } = render(
      <TableauBlanc cases={["attente", "passe", "echoue"]} />,
    );

    // case vide : contour + centre, puis la ligne
    expect(marques(container, "attente")).toBe(3);
    // contour + centre + fond + 4 pixels de coche, puis la ligne
    expect(marques(container, "passe")).toBe(8);
    // contour + centre + fond + 5 pixels de croix, puis la ligne
    expect(marques(container, "echoue")).toBe(9);
  });

  it("keeps a margin between the sixth row and the frame, as at the top", () => {
    const { container } = render(
      <TableauBlanc
        cases={Array.from({ length: 6 }, () => "passe" as const)}
      />,
    );

    const fond = container.querySelectorAll("rect")[1];
    const basDuFond =
      Number(fond.getAttribute("y")) + Number(fond.getAttribute("height"));
    const basDesCases = Math.max(
      ...[...container.querySelectorAll("[data-case] rect")].map(
        (r) => Number(r.getAttribute("y")) + Number(r.getAttribute("height")),
      ),
    );
    const hautDesCases = Math.min(
      ...[...container.querySelectorAll("[data-case] rect")].map((r) =>
        Number(r.getAttribute("y")),
      ),
    );

    expect(basDuFond - basDesCases).toBe(
      hautDesCases - Number(fond.getAttribute("y")),
    );
  });
});
