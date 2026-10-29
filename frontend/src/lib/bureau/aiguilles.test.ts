import { describe, expect, it } from "vitest";
import { aiguillesDeLHorloge } from "./aiguilles";

function a(heure: number, minute = 0): number {
  return new Date(2026, 9, 29, heure, minute).getTime();
}

describe("aiguillesDeLHorloge", () => {
  it("points the hour hand at 90 degrees at 3 h and 270 degrees at 9 h", () => {
    expect(aiguillesDeLHorloge(a(3)).heure).toBe(90);
    expect(aiguillesDeLHorloge(a(9)).heure).toBe(270);
  });

  it("reads the same hand at 3 h and 15 h: a twelve-hour dial", () => {
    expect(aiguillesDeLHorloge(a(15)).heure).toBe(aiguillesDeLHorloge(a(3)).heure);
  });

  it("moves the minute hand by six degrees a minute and the hour hand by half a degree", () => {
    const { heure, minute } = aiguillesDeLHorloge(a(3, 30));

    expect(minute).toBe(180);
    expect(heure).toBe(105);
  });
});
