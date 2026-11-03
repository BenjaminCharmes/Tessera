import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { INITIAL } from "../../hooks/streamState";
import { PORTE_X } from "../../lib/bureau/activites";
import { api } from "../../lib/api";
import Piece from "./Piece";
import { T0, etatApresPipeline, etatEnSecurite, etatQuatreFaits, nomme } from "./etatsDeTest";

const TASSE = () => 0;
const ETIRE = () => 0.5;
const MACHINE = () => 0.99;

beforeEach(() => {
  // Les décalages des agents suivent l'échelle des sprites, qui dépend de la largeur : celle d'un grand écran.
  vi.stubGlobal("innerWidth", 2400);
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function agents(conteneur: HTMLElement): HTMLElement[] {
  return [...conteneur.querySelectorAll<HTMLElement>("[data-agent]")];
}

describe("Piece break activities", () => {
  it.each([
    { nom: "coffee at the post", hasard: TASSE, libelle: "boit un café à son poste" },
    { nom: "stretching", hasard: ETIRE, libelle: "fait une pause" },
    { nom: "coffee at the machine", hasard: MACHINE, libelle: "prend un café à la machine" },
  ])("names an agent who is done $nom", ({ hasard, libelle }) => {
    render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} hasard={hasard} />);

    expect(screen.getByRole("img", { name: nomme(`Codeur, ${libelle}`, "codeur") })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: nomme(`Testeur, ${libelle}`, "testeur") })).toBeInTheDocument();
  });

  it("raises the arms of an agent who stretches, and gives a cup to the others", () => {
    const { container: a } = render(
      <Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} hasard={ETIRE} />,
    );
    const { container: b } = render(
      <Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} hasard={TASSE} />,
    );

    const dessin = (c: HTMLElement) => c.querySelector('[data-agent="codeur"]')?.innerHTML;
    expect(dessin(a)).toBeDefined();
    expect(dessin(a)).not.toBe(dessin(b));
  });

  it("gives no break activity to a busy or a waiting agent", () => {
    const { container } = render(
      <Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} hasard={MACHINE} />,
    );

    expect(agents(container).map((a) => a.dataset.agent)).toEqual(["codeur", "testeur"]);
    expect(screen.getByRole("button", { name: nomme("Sécurité, travaille", "securite") })).toBeInTheDocument();
  });

  it("keeps the break while the clock does not move and replays it on a tick", () => {
    const tirages = [0.99, 0.99, 0.1, 0, 0.9];
    const hasard = vi.fn(() => tirages.shift() ?? 0.9);
    const { rerender } = render(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} hasard={hasard} />);
    const appels = hasard.mock.calls.length;

    rerender(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} hasard={hasard} />);
    expect(hasard.mock.calls.length).toBe(appels);

    rerender(<Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0 + 5_000} hasard={hasard} />);
    expect(screen.getByRole("img", { name: nomme("Codeur, boit un café à son poste", "codeur") })).toBeInTheDocument();
  });
});

describe("Piece coffee machine", () => {
  it("sends three agents to the machine and the fourth to his post", () => {
    const { container } = render(
      <Piece projet="ide-core" etat={etatQuatreFaits()} maintenant={T0} hasard={MACHINE} />,
    );

    const activites = agents(container).map((a) => [a.dataset.agent, a.dataset.activite]);
    expect(activites).toEqual([
      ["codeur", "machine"],
      ["testeur", "machine"],
      ["securite", "machine"],
      ["reviewer", "tasse"],
    ]);
    expect(screen.getByRole("img", { name: nomme("Reviewer, boit un café à son poste", "reviewer") })).toBeInTheDocument();
  });

  it("steams if and only if an agent is at the machine", () => {
    const { container: avec } = render(
      <Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} hasard={MACHINE} />,
    );
    const { container: sans } = render(
      <Piece projet="ide-core" etat={etatEnSecurite()} maintenant={T0} hasard={TASSE} />,
    );
    const { container: personne } = render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />);

    expect(avec.querySelectorAll('[data-sprite="vapeur"]')).toHaveLength(1);
    expect(sans.querySelectorAll('[data-sprite="vapeur"]')).toHaveLength(0);
    expect(personne.querySelectorAll('[data-sprite="vapeur"]')).toHaveLength(0);
  });

  it("always draws the machine and the door, still, in a room without run", () => {
    const { container } = render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />);

    expect(container.querySelectorAll('[data-sprite="machine-a-cafe"]')).toHaveLength(1);
    expect(container.querySelectorAll('[data-sprite="porte"]')).toHaveLength(1);
    expect(agents(container)).toHaveLength(0);
  });
});

describe("Piece end of run", () => {
  function pieceClose() {
    return render(
      <Piece projet="ide-core" etat={etatApresPipeline(["run_closed"])} maintenant={T0} hasard={MACHINE} />,
    );
  }

  it("takes all five agents to the door, with no opacity", () => {
    const { container } = pieceClose();

    const tous = agents(container);
    expect(tous).toHaveLength(5);
    for (const agent of tous) {
      expect(agent.style.transform).toContain(`translate(${PORTE_X + 9}px`);
      expect(agent.style.opacity).toBe("0");
    }
  });

  it("makes the agents who left unreachable", () => {
    const { container } = pieceClose();

    for (const agent of agents(container)) {
      expect(agent).toHaveAttribute("inert");
      expect(agent).toHaveAttribute("aria-hidden", "true");
      expect(agent).toHaveAttribute("tabindex", "-1");
    }
    expect(screen.queryAllByRole("img", { name: /café|étire/ })).toHaveLength(0);
  });

  it("empties every chair and puts the steam out", () => {
    const { container } = pieceClose();

    expect(container.querySelectorAll('[data-pose="assis"]')).toHaveLength(0);
    expect(container.querySelectorAll('[data-sprite="vapeur"]')).toHaveLength(0);
  });

  it("keeps the five posts as buttons, clickable underneath the agents", () => {
    pieceClose();

    // L'interrupteur est le seul autre bouton de la pièce.
    const postes = screen.getAllByRole("button").filter((b) => !/lumière/.test(b.getAttribute("aria-label") ?? ""));
    expect(postes).toHaveLength(5);
  });
});
