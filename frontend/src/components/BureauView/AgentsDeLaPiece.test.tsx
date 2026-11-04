import { describe, it, expect } from "vitest";
import { render } from "@testing-library/react";
import AgentsDeLaPiece from "./AgentsDeLaPiece";
import type { AgentPlace } from "../../lib/bureau/activites";

/** Hauteur des pieds au-dessus du bas du sol, lue dans le style rendu. */
function hauteurDesPieds(el: HTMLElement): number {
  const bas = parseFloat(el.style.bottom);
  const monte = /translate\([^,]+,\s*(-?[\d.]+)px\)/.exec(el.style.transform);
  return bas - (monte ? parseFloat(monte[1] ?? "0") : 0);
}

const AU_FOND: AgentPlace = {
  poste: "codeur",
  x: 400,
  decalage: 0,
  niveau: "fond",
  activite: "machine",
  parti: false,
};

describe("AgentsDeLaPiece — un agent du fond se tient sur le sol (ticket-777)", () => {
  it("a les pieds sous la base des meubles du fond, devant eux", () => {
    const { container } = render(<AgentsDeLaPiece projet="p" agents={[AU_FOND]} />);
    const agent = container.querySelector<HTMLElement>('[data-agent="codeur"]');
    expect(agent).not.toBeNull();
    // Sol de la pièce : 160 px (`h-40` de `Piece`) ; les meubles du fond descendent de 4 px
    // sous le mur (`-bottom-1` de `Pose`) : leur base est à 156 px du bas.
    expect(hauteurDesPieds(agent as HTMLElement)).toBeLessThan(156);
    expect(hauteurDesPieds(agent as HTMLElement)).toBeGreaterThan(140);
  });

  it("laisse un agent de la rangée à hauteur des postes", () => {
    const { container } = render(
      <AgentsDeLaPiece projet="p" agents={[{ ...AU_FOND, niveau: "rangee", activite: "tasse" }]} />,
    );
    const agent = container.querySelector<HTMLElement>('[data-agent="codeur"]');
    expect(hauteurDesPieds(agent as HTMLElement)).toBe(28);
  });
});
