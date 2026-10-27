import { describe, expect, it } from "vitest";
import { dayMoment } from "./dayMoment";

/** Un instant à l'heure locale donnée : les bornes se lisent en heure locale, pas en UTC. */
function at(hour: number, minute = 0): number {
  return new Date(2026, 9, 27, hour, minute).getTime();
}

describe("dayMoment", () => {
  it("says day at 14:00", () => {
    expect(dayMoment(at(14))).toBe("jour");
  });

  it("says night at 22:00", () => {
    expect(dayMoment(at(22))).toBe("nuit");
  });

  it("starts the day at 07:00 and ends it at 19:00", () => {
    expect(dayMoment(at(6, 59))).toBe("nuit");
    expect(dayMoment(at(7))).toBe("jour");
    expect(dayMoment(at(18, 59))).toBe("jour");
    expect(dayMoment(at(19))).toBe("nuit");
  });

  it("says night around midnight", () => {
    expect(dayMoment(at(0))).toBe("nuit");
    expect(dayMoment(at(3))).toBe("nuit");
  });
});
