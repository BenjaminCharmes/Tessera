import { describe, expect, it } from "vitest";
import { estModeDeZoom, zoomPourAjuster, zoomVoisin } from "./zoomDuBureau";

describe("zoomDuBureau", () => {
  it("steps by ten percent between 40 and 125 percent", () => {
    expect(zoomVoisin(1, -1)).toBe(0.9);
    expect(zoomVoisin(1.2, 1)).toBe(1.25);
    expect(zoomVoisin(0.45, -1)).toBe(0.4);
  });

  it("fits the rooms in the available height without ever enlarging them", () => {
    expect(zoomPourAjuster(900, 1800)).toBe(0.5);
    expect(zoomPourAjuster(900, 600)).toBe(1);
    expect(zoomPourAjuster(900, 9000)).toBe(0.4);
    expect(zoomPourAjuster(0, 1800)).toBe(1);
  });

  it("accepts only a known mode from storage", () => {
    expect(estModeDeZoom("ajuste")).toBe(true);
    expect(estModeDeZoom(0.8)).toBe(true);
    expect(estModeDeZoom(3)).toBe(false);
    expect(estModeDeZoom("grand")).toBe(false);
  });
});
