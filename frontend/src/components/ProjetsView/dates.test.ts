import { describe, expect, it } from "vitest";
import { dateExacte, ilYa } from "./dates";

const MAINTENANT = Date.parse("2026-10-12T12:00:00Z");

describe("ilYa", () => {
  it("writes the elapsed time in the largest fitting unit", () => {
    const il = (iso: string) => ilYa(iso, MAINTENANT);
    expect(il("2026-10-12T11:59:40Z")).toBe("à l'instant");
    expect(il("2026-10-12T11:55:00Z")).toBe("il y a 5 min");
    expect(il("2026-10-12T09:00:00Z")).toBe("il y a 3 h");
    expect(il("2026-10-10T12:00:00Z")).toBe("il y a 2 j");
    expect(il("2026-07-12T12:00:00Z")).toBe("il y a 3 mois");
    expect(il("2024-10-12T12:00:00Z")).toBe("il y a 2 ans");
  });

  it("returns an empty string for a missing or unreadable date", () => {
    expect(ilYa(null, MAINTENANT)).toBe("");
    expect(ilYa("pas une date", MAINTENANT)).toBe("");
  });

  it("never reports a future date as negative", () => {
    expect(ilYa("2026-10-13T12:00:00Z", MAINTENANT)).toBe("à l'instant");
  });
});

describe("dateExacte", () => {
  it("formats a readable date for the tooltip", () => {
    expect(dateExacte("2026-10-12T12:00:00Z")).toContain("2026");
  });

  it("returns an empty string for a missing date", () => {
    expect(dateExacte(null)).toBe("");
  });
});
