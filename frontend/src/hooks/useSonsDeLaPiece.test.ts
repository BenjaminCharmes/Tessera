import { renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { SignauxSonores } from "../lib/bureau/sons";
import { useSonsDeLaPiece } from "./useSonsDeLaPiece";

const CALME: SignauxSonores = { fete: false, alarme: false, machine: 0, demarrages: 0 };

interface Props {
  signaux: SignauxSonores;
  actif: boolean;
}

beforeEach(() => {
  vi.useFakeTimers({ now: 1_000_000 });
});

afterEach(() => {
  vi.useRealTimers();
});

function monter(actif: boolean) {
  const jouer = vi.fn();
  const vue = renderHook(({ signaux, actif: on }: Props) => useSonsDeLaPiece(signaux, on, jouer), {
    initialProps: { signaux: CALME, actif } as Props,
  });
  vi.advanceTimersByTime(2_500);
  return { jouer, ...vue };
}

describe("useSonsDeLaPiece", () => {
  it("plays the glouglou when an agent reaches the coffee machine", () => {
    const { jouer, rerender } = monter(true);

    rerender({ signaux: { ...CALME, machine: 1 }, actif: true });

    expect(jouer).toHaveBeenCalledExactlyOnceWith("glouglou");
  });

  it("does not play what happened while the sound was off once it is turned on", () => {
    const { jouer, rerender } = monter(false);
    rerender({ signaux: { ...CALME, machine: 1 }, actif: false });

    rerender({ signaux: { ...CALME, machine: 1 }, actif: true });

    expect(jouer).not.toHaveBeenCalled();
  });

  it("plays only the most important sound when several rise together", () => {
    const { jouer, rerender } = monter(true);

    rerender({ signaux: { fete: true, alarme: false, machine: 1, demarrages: 1 }, actif: true });

    expect(jouer).toHaveBeenCalledExactlyOnceWith("fanfare");
  });
});
