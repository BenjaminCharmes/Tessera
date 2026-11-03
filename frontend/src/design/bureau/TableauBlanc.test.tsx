import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import TableauBlanc from "./TableauBlanc";

/** Les cases que le tableau dessine : son sprite les annonce (ticket-727) ; le dessin est testé dans `tableau.test.ts`. */
function cases(conteneur: HTMLElement): string | null {
  return conteneur.querySelector('[data-sprite="tableau-blanc"]')?.getAttribute("data-cases") ?? null;
}

describe("TableauBlanc", () => {
  it("draws one box per criterion, in the order of the ticket, with its state", () => {
    const { container } = render(<TableauBlanc cases={["attente", "passe", "echoue"]} />);

    expect(cases(container)).toBe("attente,passe,echoue");
  });

  it("stops at twelve boxes, and draws two tickets with the same states the same way", () => {
    const { container } = render(<TableauBlanc cases={Array.from({ length: 15 }, () => "passe" as const)} />);
    const { container: autre } = render(<TableauBlanc cases={Array.from({ length: 12 }, () => "passe" as const)} />);

    expect(cases(container)?.split(",")).toHaveLength(12);
    expect(container.querySelector("use")?.getAttribute("href")).toBe(autre.querySelector("use")?.getAttribute("href"));
  });

  it("stays blank without criteria", () => {
    const { container } = render(<TableauBlanc cases={[]} />);

    expect(cases(container)).toBe("");
  });
});
