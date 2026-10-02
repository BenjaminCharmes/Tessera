import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, act } from "@testing-library/react";
import Chrono from "./Chrono";

describe("Chrono — fige la duree apres run_closed (ticket-279)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("n'avance plus quand termineA est fourni", () => {
    // Run : démarré il y a 60s, terminé il y a 30s.
    const maintenant = Date.now();
    const depuis = new Date(maintenant - 60_000).toISOString();
    const termineA = new Date(maintenant - 30_000).toISOString();

    const { container } = render(<Chrono depuis={depuis} termineA={termineA} />);
    const initial = container.textContent ?? "";

    // 5 secondes s'écoulent — le chrono ne doit pas bouger.
    act(() => {
      vi.advanceTimersByTime(5_000);
    });

    expect(container.textContent).toBe(initial);
  });

  it("avance quand termineA est absent", () => {
    // Run en cours depuis 60s.
    const depuis = new Date(Date.now() - 60_000).toISOString();

    const { container } = render(<Chrono depuis={depuis} />);
    const initial = container.textContent ?? "";

    // On avance d'une minute, le contenu doit changer.
    act(() => {
      vi.advanceTimersByTime(60_000);
    });

    expect(container.textContent).not.toBe(initial);
  });
});
