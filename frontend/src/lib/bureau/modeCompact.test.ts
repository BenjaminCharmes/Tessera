import { describe, it, expect } from "vitest";
import { modeCompact } from "./modeCompact";

describe("modeCompact", () => {
  it("is false up to six projects", () => {
    expect(modeCompact(0)).toBe(false);
    expect(modeCompact(6)).toBe(false);
  });

  it("is true beyond six projects", () => {
    expect(modeCompact(7)).toBe(true);
    expect(modeCompact(12)).toBe(true);
  });
});
