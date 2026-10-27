import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { api } from "../../lib/api";
import { DUREE_DE_LA_FETE_MS } from "../../lib/bureau/fete";
import Piece from "./Piece";
import { T0, etatApresPhase2 } from "./etatsDeTest";

const LIVRAISON = { type: "livraison_done", data: { pr_number: 42, arret: null } } as const;
const MERGEE = { type: "ci_merge_done", data: { merged: true } } as const;
const REFUSEE = { type: "ci_merge_done", data: { merged: false } } as const;

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function section(conteneur: HTMLElement): HTMLElement {
  const piece = conteneur.querySelector<HTMLElement>("section");
  if (piece === null) throw new Error("no room rendered");
  return piece;
}

describe("Piece celebration of a merged pull request", () => {
  it("drops 18 confetti and raises the arms of the agents once the PR is merged", () => {
    const etat = etatApresPhase2([LIVRAISON, MERGEE]);
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 1_000} />);

    expect(container.querySelectorAll('[data-sprite="confetti"]')).toHaveLength(18);
    const agents = [...container.querySelectorAll<HTMLElement>("[data-agent]")];
    expect(agents).toHaveLength(5);
    for (const agent of agents) {
      expect(agent.dataset.activite).toBe("fete");
      expect(agent.querySelector('[data-bras="leves"]')).not.toBeNull();
    }
  });

  it("paints the outline green and says the PR is merged in the pill", () => {
    const etat = etatApresPhase2([LIVRAISON, MERGEE]);
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 1_000} />);

    expect(section(container)).toHaveAttribute("data-contour", "vert");
    expect(screen.getByText("PR mergée")).toHaveAttribute("data-etat", "reussi");
  });

  it("stops the celebration 10 s after the merge", () => {
    const etat = etatApresPhase2([LIVRAISON, MERGEE]);
    const { container, rerender } = render(
      <Piece projet="ide-core" etat={etat} maintenant={T0 + DUREE_DE_LA_FETE_MS - 1} />,
    );
    expect(container.querySelectorAll('[data-sprite="confetti"]')).toHaveLength(18);

    rerender(<Piece projet="ide-core" etat={etat} maintenant={T0 + DUREE_DE_LA_FETE_MS} />);

    expect(container.querySelectorAll('[data-sprite="confetti"]')).toHaveLength(0);
    expect(screen.queryByText("PR mergée")).toBeNull();
    expect(container.querySelector('[data-activite="fete"]')).toBeNull();
  });

  it("draws no confetti while the PR is only waiting for the CI", () => {
    const etat = etatApresPhase2([LIVRAISON]);
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 1_000} />);

    expect(container.querySelectorAll('[data-sprite="confetti"]')).toHaveLength(0);
  });
});

describe("Piece alarm of a red CI", () => {
  it("lights the beacon and paints the outline red after a refused merge", () => {
    const etat = etatApresPhase2([LIVRAISON, REFUSEE]);
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 60_000} />);

    expect(container.querySelectorAll('[data-sprite="gyrophare"]')).toHaveLength(1);
    expect(section(container)).toHaveAttribute("data-contour", "rouge");
    expect(container.querySelectorAll('[data-sprite="confetti"]')).toHaveLength(0);
  });

  it("keeps the beacon lit as long as nothing restarts the delivery", () => {
    const etat = etatApresPhase2([LIVRAISON, REFUSEE]);
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 3_600_000} />);

    expect(container.querySelectorAll('[data-sprite="gyrophare"]')).toHaveLength(1);
  });

  it("puts the beacon out at the next livraison_started", () => {
    const etat = etatApresPhase2([LIVRAISON, REFUSEE, { type: "livraison_started" }]);
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 60_000} />);

    expect(container.querySelectorAll('[data-sprite="gyrophare"]')).toHaveLength(0);
  });

  it("draws no beacon after a merge", () => {
    const etat = etatApresPhase2([LIVRAISON, MERGEE]);
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 60_000} />);

    expect(container.querySelectorAll('[data-sprite="gyrophare"]')).toHaveLength(0);
  });
});
