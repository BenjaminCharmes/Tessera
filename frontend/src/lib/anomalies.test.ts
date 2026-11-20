import { describe, expect, it } from "vitest";
import { libelleDeRegle } from "./anomalies";

describe("libelleDeRegle", () => {
  it("labels the serial documentation refusal rule", () => {
    expect(libelleDeRegle("documentation_refusee_en_serie")).toBe("documentation refusée en série");
  });

  it("falls back to the raw identifier for an unknown rule", () => {
    expect(libelleDeRegle("regle_inconnue")).toBe("regle_inconnue");
  });
});
