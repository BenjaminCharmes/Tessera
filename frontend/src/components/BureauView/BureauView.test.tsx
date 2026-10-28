import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import BureauView from "./index";
import type { ProjetDuBureau } from "./index";
import { api } from "../../lib/api";
import { apiQuota } from "../../lib/quota";
import type { UsageStats } from "../../types/api";
import Piece from "./Piece";
import { useSanteDuBureau } from "../../hooks/useSanteDuBureau";
import { T0, etatEnCodage, etatEnSecurite } from "./etatsDeTest";

const CANAL = { envoyer: vi.fn(), son: { actif: false, regler: vi.fn() } };

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
    vi.spyOn(api.services, "list").mockResolvedValue([]);
    vi.spyOn(api.github, "getPrStatuses").mockResolvedValue([]);
    vi.spyOn(api.runs, "list").mockResolvedValue([]);
    // Le tableau du jour lit la dépense et le quota : rien de réseau dans ces tests.
    vi.spyOn(api.usage, "stats").mockResolvedValue({
      daily: [],
    } as unknown as UsageStats);
    vi.spyOn(apiQuota, "fenetres").mockResolvedValue({ windows: {} });
    vi.useFakeTimers();
    vi.setSystemTime(T0 + 5_000);
  });
  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
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
    // L'image qui active la marche des agents passe d'abord : elle ne se répète pas (ticket-638).
    act(() => vi.advanceTimersToNextFrame());
    expect(vi.getTimerCount()).toBe(1);
  });

  it("mounts a single interval for a view of rooms", () => {
    render(<BureauView projets={projets(6)} {...CANAL} />);

    expect(screen.getAllByRole("region")).toHaveLength(6);
    // L'image qui active la marche des agents passe d'abord : elle ne se répète pas (ticket-638).
    act(() => vi.advanceTimersToNextFrame());
    expect(vi.getTimerCount()).toBe(1);
  });

  it("moves the words with the clock without any new event", () => {
    render(<BureauView projets={projets(1)} {...CANAL} />);
    expect(screen.queryByTestId("bulle")).toBeNull();
    expect(
      screen.getByRole("button", { name: "Codeur, travaille" }),
    ).toBeInTheDocument();

    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    expect(screen.getByTestId("bulle")).toHaveTextContent("…");

    act(() => {
      vi.advanceTimersByTime(150_000);
    });
    expect(screen.getByTestId("bulle")).toHaveTextContent("!");
  });

  it("keeps one full room per project, stacked, however many there are", () => {
    const { container } = render(
      <BureauView projets={projets(7)} {...CANAL} />,
    );

    expect(screen.getAllByRole("region")).toHaveLength(7);
    expect(
      container.querySelector('[data-mode="pieces"]')?.className,
    ).toContain("flex-col");
    // L'image qui active la marche des agents passe d'abord : elle ne se répète pas (ticket-638).
    act(() => vi.advanceTimersToNextFrame());
    expect(vi.getTimerCount()).toBe(1);
  });
});
