import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import BureauView from "./index";
import type { ProjetDuBureau } from "./index";
import Piece from "./Piece";
import { useSanteDuBureau } from "../../hooks/useSanteDuBureau";
import { T0, etatEnCodage, etatEnSecurite } from "./etatsDeTest";

function projets(nombre: number): ProjetDuBureau[] {
  return Array.from({ length: nombre }, (_, i) => ({
    nom: `projet-${i}`,
    etat: i % 2 === 0 ? etatEnCodage() : etatEnSecurite(),
  }));
}

/** Dix pièces sous une seule horloge, sans passer par le mode compact. */
function DixPieces() {
  const maintenant = useSanteDuBureau();
  return (
    <>
      {projets(10).map(({ nom, etat }) => (
        <Piece key={nom} projet={nom} etat={etat} maintenant={maintenant} />
      ))}
    </>
  );
}

describe("BureauView", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(T0 + 5_000);
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders ten rooms under 2000 SVG nodes", () => {
    const { container } = render(<DixPieces />);

    expect(screen.getAllByRole("region")).toHaveLength(10);
    const noeuds = container.querySelectorAll("svg *").length;
    expect(noeuds).toBeGreaterThan(0);
    expect(noeuds).toBeLessThan(2000);
  });

  it("mounts a single interval for ten rooms", () => {
    const setIntervalEspion = vi.spyOn(globalThis, "setInterval");
    render(<DixPieces />);

    expect(setIntervalEspion).toHaveBeenCalledTimes(1);
    expect(vi.getTimerCount()).toBe(1);
  });

  it("mounts a single interval for a view of rooms", () => {
    render(<BureauView projets={projets(6)} />);

    expect(screen.getAllByRole("region")).toHaveLength(6);
    expect(vi.getTimerCount()).toBe(1);
  });

  it("moves the words with the clock without any new event", () => {
    render(<BureauView projets={projets(1)} />);
    expect(screen.getByTestId("bulle")).toHaveTextContent("travaille");

    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    expect(screen.getByTestId("bulle")).toHaveTextContent("silencieux");

    act(() => {
      vi.advanceTimersByTime(150_000);
    });
    expect(screen.getByTestId("bulle")).toHaveTextContent("figé ?");
  });

  it("switches to one compact row per project above the threshold", () => {
    const { container } = render(<BureauView projets={projets(7)} />);

    expect(screen.queryAllByRole("region")).toHaveLength(0);
    expect(screen.getAllByRole("group")).toHaveLength(7);
    expect(container.querySelectorAll("svg")).toHaveLength(0);
    expect(screen.getAllByRole("img", { name: "Codeur, travaille" }).length).toBeGreaterThan(0);
    expect(vi.getTimerCount()).toBe(1);
  });
});
