import { describe, expect, it } from "vitest";
import { heureDeReprise } from "./heureDeReprise";

const OPTIONS: Intl.DateTimeFormatOptions = { hour: "2-digit", minute: "2-digit" };

describe("heureDeReprise", () => {
  const maintenant = new Date(2026, 9, 26, 9, 0).getTime();

  it("gives the time alone when the window resumes today", () => {
    const reprise = new Date(2026, 9, 26, 14, 30);

    expect(heureDeReprise(reprise.toISOString(), maintenant)).toBe(reprise.toLocaleTimeString([], OPTIONS));
  });

  it("prefixes the weekday when the window resumes another day", () => {
    const reprise = new Date(2026, 9, 29, 8, 15);
    const attendu = `${reprise.toLocaleDateString([], { weekday: "short" })} ${reprise.toLocaleTimeString([], OPTIONS)}`;

    expect(heureDeReprise(reprise.toISOString(), maintenant)).toBe(attendu);
  });

  it("returns null for an unreadable date", () => {
    expect(heureDeReprise("pas une date", maintenant)).toBeNull();
  });
});
