import { describe, expect, it } from "vitest";
import { lumiereAllumee } from "./lumiere";

describe("lumiereAllumee", () => {
  it("lights the room at night and leaves it off by day", () => {
    expect(lumiereAllumee("nuit", null)).toBe(true);
    expect(lumiereAllumee("jour", null)).toBe(false);
  });

  it("follows the switch while the moment of the day has not changed", () => {
    expect(lumiereAllumee("nuit", { moment: "nuit", allume: false })).toBe(false);
    expect(lumiereAllumee("jour", { moment: "jour", allume: true })).toBe(true);
  });

  it("forgets a switch made during the other moment of the day", () => {
    expect(lumiereAllumee("jour", { moment: "nuit", allume: true })).toBe(false);
    expect(lumiereAllumee("nuit", { moment: "jour", allume: false })).toBe(true);
  });
});
