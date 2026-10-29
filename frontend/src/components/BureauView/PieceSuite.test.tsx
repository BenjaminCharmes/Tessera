import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { api } from "../../lib/api";
import type { EventType } from "../../types/api";
import Piece from "./Piece";
import { T0, etatApresPipeline, nomme } from "./etatsDeTest";

beforeEach(() => {
  vi.stubGlobal("innerWidth", 1920);
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function etat(...suite: EventType[]) {
  return etatApresPipeline(suite);
}

function redacteurs(conteneur: HTMLElement): Element[] {
  return [...conteneur.querySelectorAll('[data-agent^="doc-"]')];
}

describe("Piece during the documentation", () => {
  it("stands the two writers at the library, then sends them away when it ends", () => {
    const { container, rerender } = render(
      <Piece projet="ide-core" etat={etat("documentation_started")} maintenant={T0} />,
    );

    const presents = redacteurs(container);
    expect(presents.map((r) => r.getAttribute("data-agent"))).toEqual(["doc-technique", "doc-fonctionnelle"]);
    expect(presents.every((r) => r.getAttribute("data-activite") === "redige")).toBe(true);
    expect(screen.getByRole("img", { name: nomme("Rédacteur technique, rédige la documentation", "doc-technique") })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: nomme("Rédacteur fonctionnel, rédige la documentation", "doc-fonctionnelle") })).toBeInTheDocument();

    rerender(<Piece projet="ide-core" etat={etat("documentation_started", "doc_updated")} maintenant={T0} />);
    expect(redacteurs(container)).toEqual([]);
  });

  it("sends them away on documentation_failed", () => {
    const { container } = render(
      <Piece projet="ide-core" etat={etat("documentation_started", "documentation_failed")} maintenant={T0} />,
    );

    expect(redacteurs(container)).toEqual([]);
  });

  it("sends them away when the delivery starts without a closing event", () => {
    const { container } = render(
      <Piece projet="ide-core" etat={etat("documentation_started", "livraison_started")} maintenant={T0} />,
    );

    expect(redacteurs(container)).toEqual([]);
  });

  it("draws no writer outside the documentation", () => {
    const { container, rerender } = render(<Piece projet="ide-core" etat={etat()} maintenant={T0} />);
    expect(redacteurs(container)).toEqual([]);

    rerender(<Piece projet="ide-core" etat={etat("livraison_started", "livraison_done")} maintenant={T0} />);
    expect(redacteurs(container)).toEqual([]);

    rerender(<Piece projet="ide-core" etat={etat("documentation_started", "run_closed")} maintenant={T0} />);
    expect(redacteurs(container)).toEqual([]);
  });
});

describe("Piece during the delivery", () => {
  it("stands the coder at the mailbox, away from its desk, until the delivery is done", () => {
    const { container, rerender } = render(
      <Piece projet="ide-core" etat={etat("livraison_started")} maintenant={T0} />,
    );

    expect(container.querySelector('[data-agent="codeur"]')?.getAttribute("data-activite")).toBe("depose");
    expect(screen.getByRole("img", { name: nomme("Codeur, dépose la PR", "codeur") })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /, codeur, / }).parentElement).toHaveAttribute("data-absent", "true");

    rerender(<Piece projet="ide-core" etat={etat("livraison_started", "livraison_done")} maintenant={T0} />);

    expect(container.querySelector('[data-agent="codeur"]')?.getAttribute("data-activite")).not.toBe("depose");
    expect(screen.queryByRole("img", { name: nomme("Codeur, dépose la PR", "codeur") })).toBeNull();
  });
});
