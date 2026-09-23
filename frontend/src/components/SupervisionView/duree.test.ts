import { describe, it, expect } from "vitest";
import { formater } from "./duree";

describe("formater", () => {
  it("rend les secondes seules sous la minute", () => {
    expect(formater(42_000)).toBe("42s");
  });

  it("rend minutes et secondes, comme la carte d'agents de l'editeur", () => {
    expect(formater(179_000)).toBe("2m 59s");
  });

  it("passe aux heures quand un run autonome dure", () => {
    expect(formater(3_723_000)).toBe("1h 2m");
  });

  it("ne pretend rien sur une date invalide", () => {
    // `Date.parse` d'une chaine vide rend NaN : « NaNs » a l'ecran serait pire
    // que de ne rien dire.
    expect(formater(NaN)).toBe("—");
    expect(formater(-5)).toBe("—");
  });
});
