import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render } from "@testing-library/react";
import { INITIAL } from "../../hooks/streamState";
import { api } from "../../lib/api";
import Piece from "./Piece";
import Salle from "./Salle";
import { T0 } from "./etatsDeTest";

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

function rendreSalle(): HTMLElement {
  const { container } = render(
    <Salle
      titre="Salle de test"
      entete="Une salle pour le test"
      vide="Personne"
      mobilier={<svg data-sprite="mobilier-de-test" />}
      maintenant={T0}
    />,
  );
  return container;
}

function rendrePiece(): HTMLElement {
  const { container } = render(<Piece projet="ide-core" etat={INITIAL} maintenant={T0} />);
  return container;
}

function sprites(racine: HTMLElement): HTMLElement[] {
  return Array.from(racine.querySelectorAll<HTMLElement>("[data-sprite]"));
}

function horsEchelle(racine: HTMLElement): string[] {
  return sprites(racine)
    .filter((s) => s.closest("[data-agrandi]") === null)
    .map((s) => s.getAttribute("data-sprite") ?? "");
}

describe("the wall scale", () => {
  it("draws every sprite of a room inside a scaled wrapper", () => {
    const salle = rendreSalle();

    expect(sprites(salle).length).toBeGreaterThan(0);
    expect(horsEchelle(salle)).toEqual([]);
  });

  it("draws every sprite of a project room inside a scaled wrapper", () => {
    const piece = rendrePiece();

    expect(sprites(piece).length).toBeGreaterThan(0);
    expect(horsEchelle(piece)).toEqual([]);
  });

  it.each([
    ["a room", rendreSalle],
    ["a project room", rendrePiece],
  ])("draws windows, ceiling lamps and the switch in %s", (_nom, rendre) => {
    const racine = rendre();
    const noms = new Set(sprites(racine).map((s) => s.getAttribute("data-sprite")));

    expect(noms).toContain("fenetre");
    expect(noms).toContain("plafonnier");
    expect(noms).toContain("interrupteur");
  });

  it("keeps the order window, lamp, window, clock, frame, switch in a room", () => {
    const salle = rendreSalle();
    const mur = salle.querySelector('[data-mur="salle"]');

    const ordre = Array.from(mur?.querySelectorAll("[data-sprite]") ?? []).map((s) => s.getAttribute("data-sprite"));
    expect(ordre).toEqual(["fenetre", "plafonnier", "fenetre", "horloge", "cadre", "interrupteur"]);
  });

  it("toggles the lights from the switch of either wall", () => {
    const piece = rendrePiece();
    const lampe = () => piece.querySelector('[data-sprite="plafonnier"]');
    const avant = lampe()?.getAttribute("data-allume");

    const bouton = piece.querySelector<HTMLElement>('button[aria-pressed]');
    expect(bouton).not.toBeNull();
    if (bouton) fireEvent.click(bouton);

    expect(lampe()?.getAttribute("data-allume")).not.toBe(avant);
  });
});
