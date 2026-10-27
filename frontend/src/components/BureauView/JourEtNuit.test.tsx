import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";
import { INITIAL } from "../../hooks/streamState";
import { api } from "../../lib/api";
import Piece from "./Piece";
import SallesCommunes from "./SallesCommunes";

/** Un instant à l'heure locale donnée : l'horloge de la vue est injectée, jamais lue. */
function at(hour: number): number {
  return new Date(2026, 9, 27, hour).getTime();
}

function ciels(conteneur: HTMLElement): (string | undefined)[] {
  return [...conteneur.querySelectorAll<HTMLElement>('[data-sprite="fenetre"]')].map((f) => f.dataset.moment);
}

function plafonniers(conteneur: HTMLElement): (string | undefined)[] {
  return [...conteneur.querySelectorAll<HTMLElement>('[data-sprite="plafonnier"]')].map((p) => p.dataset.allume);
}

beforeEach(() => {
  vi.spyOn(api.services, "list").mockResolvedValue([]);
  vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("Piece day and night", () => {
  it("shows two daytime windows, three unlit lamps and no veil at 14:00", () => {
    const { container } = render(<Piece projet="ide-core" etat={INITIAL} maintenant={at(14)} />);

    expect(ciels(container)).toEqual(["jour", "jour"]);
    expect(plafonniers(container)).toEqual(["false", "false", "false"]);
    expect(container.querySelector("[data-voile]")).toBeNull();
    expect(container.querySelector('[data-detail="soleil"]')).not.toBeNull();
  });

  it("shows two night windows, a veil and three lit lamps at 22:00", () => {
    const { container } = render(<Piece projet="ide-core" etat={INITIAL} maintenant={at(22)} />);

    expect(ciels(container)).toEqual(["nuit", "nuit"]);
    expect(plafonniers(container)).toEqual(["true", "true", "true"]);
    expect(container.querySelectorAll("[data-voile]")).toHaveLength(1);
    expect(container.querySelectorAll('[data-detail="halo"]')).toHaveLength(3);
    expect(container.querySelector('[data-detail="etoiles"]')).not.toBeNull();
  });

  it("lets clicks through the veil", () => {
    const { container } = render(<Piece projet="ide-core" etat={INITIAL} maintenant={at(22)} />);

    expect(container.querySelector("[data-voile]")?.className).toContain("pointer-events-none");
  });
});

describe("SallesCommunes day and night", () => {
  it("gives each of the four rooms two windows, a lamp and, at night, a veil", () => {
    const { container } = render(<SallesCommunes projets={[]} maintenant={at(22)} />);

    expect(ciels(container)).toEqual(Array(8).fill("nuit"));
    expect(plafonniers(container)).toEqual(Array(4).fill("true"));
    expect(container.querySelectorAll("[data-voile]")).toHaveLength(4);
  });

  it("keeps the rooms daylit, with unlit lamps, at 14:00", () => {
    const { container } = render(<SallesCommunes projets={[]} maintenant={at(14)} />);

    expect(ciels(container)).toEqual(Array(8).fill("jour"));
    expect(plafonniers(container)).toEqual(Array(4).fill("false"));
    expect(container.querySelector("[data-voile]")).toBeNull();
  });
});
