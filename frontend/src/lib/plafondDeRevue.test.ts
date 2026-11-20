import { describe, expect, it } from "vitest";
import { plafondDeRevue, ticketEnCours } from "./plafondDeRevue";

describe("plafondDeRevue", () => {
  it("takes the smaller of three dollars and the run cap", () => {
    expect(plafondDeRevue(5)).toBe(3);
    expect(plafondDeRevue(1.5)).toBe(1.5);
  });

  it("keeps three dollars when the run cap is zero", () => {
    expect(plafondDeRevue(0)).toBe(3);
  });
});

describe("ticketEnCours", () => {
  it("reads the ticket a busy-project error names", () => {
    expect(
      ticketEnCours("API 409: Un pipeline tourne déjà sur le projet 'serpent' (ticket-042). Attends."),
    ).toBe("ticket-042");
  });

  it("answers null when no ticket is named", () => {
    expect(ticketEnCours("API 409: Un pipeline tourne déjà")).toBeNull();
  });
});
