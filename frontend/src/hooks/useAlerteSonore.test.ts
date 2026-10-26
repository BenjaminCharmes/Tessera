import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useAlerteSonore } from "./useAlerteSonore";

interface Props {
  cles: string[];
  son: boolean;
}

function monter(initial: Props, jouer = vi.fn()) {
  const vue = renderHook(({ cles, son }: Props) => useAlerteSonore(cles, son, jouer), {
    initialProps: initial,
  });
  return { jouer, ...vue };
}

describe("useAlerteSonore", () => {
  it("rings when a question appears after the first reading", () => {
    const { jouer, rerender } = monter({ cles: [], son: true });
    expect(jouer).not.toHaveBeenCalled();

    rerender({ cles: ["projet-a"], son: true });

    expect(jouer).toHaveBeenCalledTimes(1);
  });

  it("stays silent when the view opens on a question already posed", () => {
    const { jouer, rerender } = monter({ cles: ["projet-a"], son: true });

    rerender({ cles: ["projet-a"], son: true });

    expect(jouer).not.toHaveBeenCalled();
  });

  it("does not ring again while the same question stays posed", () => {
    const { jouer, rerender } = monter({ cles: [], son: true });
    rerender({ cles: ["projet-a"], son: true });
    rerender({ cles: ["projet-a"], son: true });

    expect(jouer).toHaveBeenCalledTimes(1);
  });

  it("stays silent when the setting is off", () => {
    const { jouer, rerender } = monter({ cles: [], son: false });

    rerender({ cles: ["projet-a"], son: false });

    expect(jouer).not.toHaveBeenCalled();
  });

  it("does not replay a question that arrived while the setting was off", () => {
    const { jouer, rerender } = monter({ cles: [], son: false });
    rerender({ cles: ["projet-a"], son: false });

    rerender({ cles: ["projet-a"], son: true });

    expect(jouer).not.toHaveBeenCalled();
  });

  it("rings again for a question that follows an answered one", () => {
    const { jouer, rerender } = monter({ cles: [], son: true });
    rerender({ cles: ["projet-a"], son: true });
    rerender({ cles: [], son: true });
    rerender({ cles: ["projet-a"], son: true });

    expect(jouer).toHaveBeenCalledTimes(2);
  });
});
