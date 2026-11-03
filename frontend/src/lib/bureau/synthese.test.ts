import { afterEach, describe, expect, it, vi } from "vitest";
import { jouerSon } from "./synthese";
import type { Son } from "./synthese";

let oscillateurs = 0;

class FauxContexte {
  currentTime = 0;
  destination = {};
  close = vi.fn();
  createOscillator() {
    oscillateurs += 1;
    return { type: "sine", frequency: { value: 0 }, connect: vi.fn(), start: vi.fn(), stop: vi.fn(), onended: null };
  }
  createGain() {
    return { gain: { setValueAtTime: vi.fn(), exponentialRampToValueAtTime: vi.fn() }, connect: vi.fn() };
  }
}

afterEach(() => {
  oscillateurs = 0;
  vi.unstubAllGlobals();
});

describe("jouerSon", () => {
  it.each<[Son, number]>([
    ["fanfare", 3],
    ["alarme", 2],
    ["glouglou", 2],
    ["frappes", 3],
  ])("plays %s with %i oscillators", (son, attendu) => {
    vi.stubGlobal("AudioContext", FauxContexte);

    jouerSon(son);

    expect(oscillateurs).toBe(attendu);
  });

  it("stays silent and does not throw when the browser has no AudioContext", () => {
    vi.stubGlobal("AudioContext", undefined);

    expect(() => jouerSon("fanfare")).not.toThrow();
  });
});
