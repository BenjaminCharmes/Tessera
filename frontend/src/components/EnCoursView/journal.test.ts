import { describe, expect, it } from "vitest";
import { niveauDeLigne } from "./journal";

describe("niveauDeLigne", () => {
  it("reads an error, a warning or plain information from the line's words", () => {
    expect(niveauDeLigne("Error: connect ECONNREFUSED")).toBe("erreur");
    expect(niveauDeLigne("Traceback (most recent call last):")).toBe("erreur");
    expect(niveauDeLigne("WARN slow query")).toBe("avertissement");
    expect(niveauDeLigne("GET /api 200 OK")).toBe("info");
  });

  it("does not take a count of failures or a word containing error for an error", () => {
    expect(niveauDeLigne("watch round 10: 7 checked, 0 failed")).toBe("info");
    expect(niveauDeLigne("0 errors")).toBe("info");
  });
});
