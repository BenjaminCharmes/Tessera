import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useActivites } from "./useActivites";
import type { PosteId } from "../lib/bureau/postesDuRun";

type Props = { faits: PosteId[]; maintenant: number };

describe("useActivites", () => {
  it("gives an activity to each done agent in the first render, and none to the others", () => {
    const { result } = renderHook(() => useActivites(["codeur"], 0, () => 0.5));

    expect(result.current).toEqual({ codeur: "etire" });
  });

  it("keeps the activities while the clock does not move", () => {
    const hasard = vi.fn(() => 0.5);
    const { result, rerender } = renderHook(
      ({ faits, maintenant }: Props) => useActivites(faits, maintenant, hasard),
      { initialProps: { faits: ["codeur"], maintenant: 0 } as Props },
    );
    const appels = hasard.mock.calls.length;

    rerender({ faits: ["codeur"], maintenant: 0 });

    expect(result.current).toEqual({ codeur: "etire" });
    expect(hasard.mock.calls.length).toBe(appels);
  });

  it("replays the draw on each tick of the clock", () => {
    // Premier tour : étire. Au tick suivant : 0.1 < 0.25, il change, et le tirage donne machine.
    const tirages = [0.5, 0.1, 0.99];
    const hasard = vi.fn(() => tirages.shift() ?? 0.9);
    const { result, rerender } = renderHook(
      ({ faits, maintenant }: Props) => useActivites(faits, maintenant, hasard),
      { initialProps: { faits: ["codeur"], maintenant: 0 } as Props },
    );
    expect(result.current.codeur).toBe("etire");

    rerender({ faits: ["codeur"], maintenant: 5_000 });

    expect(result.current.codeur).toBe("machine");
  });

  it("draws for an agent that finishes between two ticks", () => {
    const { result, rerender } = renderHook(
      ({ faits, maintenant }: Props) => useActivites(faits, maintenant, () => 0.99),
      { initialProps: { faits: [], maintenant: 0 } as Props },
    );
    expect(result.current).toEqual({});

    rerender({ faits: ["testeur"], maintenant: 0 });

    expect(result.current).toEqual({ testeur: "machine" });
  });

  it("caps the machine at three places", () => {
    const faits: PosteId[] = ["codeur", "testeur", "securite", "reviewer"];
    const { result } = renderHook(() => useActivites(faits, 0, () => 0.99));

    expect(Object.values(result.current).filter((a) => a === "machine")).toHaveLength(3);
    expect(result.current.reviewer).toBe("tasse");
  });
});
