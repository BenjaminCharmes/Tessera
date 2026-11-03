import { describe, expect, it } from "vitest";
import { generique, liaisons, lueur, lueurGenerique, variable, variableGenerique } from "./jeton";

describe("jeton", () => {
  it("maps a token to its sprite variable", () => {
    expect(variable("peau2.b")).toBe("var(--sprite-peau2-b)");
  });

  it("tints a screen glow with the light tone of the state", () => {
    expect(lueur("actif", 3).fill).toBe("var(--sprite-etat-actif-hi)");
  });

  it("names the generic family of skin, hair and role tops only", () => {
    expect(generique("peau3")).toBe("peau");
    expect(generique("cheveux7")).toBe("cheveux");
    expect(generique("haut-doc-technique")).toBe("haut");
    expect(generique("bureau")).toBeNull();
    expect(generique("etat-actif")).toBeNull();
  });

  it("reads a generic family from the use and the others directly", () => {
    expect(variableGenerique("cheveux4.ol")).toBe("var(--sp-cheveux-ol)");
    expect(variableGenerique("chaise.s")).toBe("var(--sprite-chaise-s)");
  });

  it("takes the glow hue from the use", () => {
    expect(lueurGenerique(2).fill).toBe("var(--sp-lueur)");
    expect(lueurGenerique(2).opacity).toContain("--sprite-lueur-force");
  });

  it("binds every tone of a generic family, and the glow to its state", () => {
    const style = liaisons(["peau3", "bureau"], "fait");
    expect(style["--sp-peau-hi"]).toBe("var(--sprite-peau3-hi)");
    expect(style["--sp-peau-ol"]).toBe("var(--sprite-peau3-ol)");
    expect(style["--sp-lueur"]).toBe("var(--sprite-etat-fait-hi)");
    expect(Object.keys(style).some((k) => k.includes("bureau"))).toBe(false);
  });
});
