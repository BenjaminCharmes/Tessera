import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { api } from "../../lib/api";
import { DUREE_DE_LA_COPIE_MS } from "../../lib/bureau/copie";
import Piece from "./Piece";
import { T0, etatAuTourDeux } from "./etatsDeTest";

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function agent(conteneur: HTMLElement, poste: string): HTMLElement {
  const noeud = conteneur.querySelector<HTMLElement>(`[data-agent="${poste}"]`);
  if (noeud === null) throw new Error(`no ${poste} agent drawn`);
  return noeud;
}

describe("Piece review handed back to the coder", () => {
  it("stands the reviewer by the coder's desk with a sheet once the coder restarts at round 2", () => {
    const etat = etatAuTourDeux("reviewer");
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 1_000} />);

    const reviewer = agent(container, "reviewer");
    expect(reviewer).toHaveAttribute("data-objet", "feuille");
    expect(reviewer).toHaveAttribute("data-activite", "copie");
    expect(reviewer.querySelector('[data-detail="feuille"]')).not.toBeNull();
    // Le poste du codeur est la première colonne : l'agent se tient à sa droite, pas devant le sien.
    expect(reviewer.style.transform).toBe("translate(118.4px, 0px)");
    expect(container.querySelectorAll('[data-objet="feuille"]')).toHaveLength(1);
  });

  it("says in the pill which round it is and who hands the copy back", () => {
    const etat = etatAuTourDeux("reviewer");
    render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 1_000} />);

    expect(screen.getByText("tour 2 — le reviewer rend sa copie")).toBeInTheDocument();
  });

  it("sends the reviewer back to its own desk 15 s later", () => {
    const etat = etatAuTourDeux("reviewer");
    const { container, rerender } = render(
      <Piece projet="ide-core" etat={etat} maintenant={T0 + DUREE_DE_LA_COPIE_MS - 1} />,
    );
    expect(agent(container, "reviewer")).toHaveAttribute("data-objet", "feuille");

    rerender(<Piece projet="ide-core" etat={etat} maintenant={T0 + DUREE_DE_LA_COPIE_MS} />);

    const reviewer = agent(container, "reviewer");
    expect(reviewer).not.toHaveAttribute("data-objet");
    expect(reviewer.dataset.activite).not.toBe("copie");
    expect(reviewer.style.transform).not.toBe("translate(118.4px, 0px)");
    expect(screen.queryByText(/rend sa copie/)).toBeNull();
  });

  it("makes the same trip for the validator after a refused validation", () => {
    const etat = etatAuTourDeux("validateur");
    const { container } = render(<Piece projet="ide-core" etat={etat} maintenant={T0 + 1_000} />);

    const validateur = agent(container, "validateur");
    expect(validateur).toHaveAttribute("data-objet", "feuille");
    expect(validateur.style.transform).toBe("translate(118.4px, 0px)");
    expect(screen.getByText("tour 2 — le validateur rend sa copie")).toBeInTheDocument();
    expect(container.querySelector('[data-agent="reviewer"]')).not.toHaveAttribute("data-objet");
  });
});
