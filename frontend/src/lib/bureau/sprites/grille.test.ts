import { describe, expect, it } from "vitest";
import { E, Grille, R, cuire, delai, sprite, tracer } from "./grille";

describe("Grille", () => {
  it("ignores pixels outside the grid and clears a pixel", () => {
    const g = new Grille(4, 4);
    g.set(-1, 0, "metal.b");
    g.rect(0, 0, 2, 2, "metal.b");
    g.clr(1, 1);
    expect(g.get(0, 0)).toBe("metal.b");
    expect(g.get(1, 1)).toBeNull();
    expect(g.get(9, 9)).toBeNull();
  });

  it("draws a Bresenham line end to end", () => {
    const g = new Grille(8, 8);
    g.line(0, 0, 7, 7, "encre.b");
    expect([0, 3, 7].map((i) => g.get(i, i))).toEqual(["encre.b", "encre.b", "encre.b"]);
  });

  it("shades a disc light at the top left, dark at the bottom right, or flat on demand", () => {
    const g = new Grille(12, 12);
    g.disc(6, 6, 5, "plante");
    expect(g.get(3, 3)).toBe("plante.hi");
    expect(g.get(9, 9)).toMatch(/plante\.(s|d)/);
    const plat = new Grille(12, 12);
    plat.disc(6, 6, 5, "soleil", { ombre: false });
    expect(new Set(plat.p.filter(Boolean))).toEqual(new Set(["soleil.b"]));
  });

  it("stamps a text pattern through its table, dots left empty", () => {
    const g = new Grille(3, 1);
    g.stamp(0, 0, ["b.h"], { b: "nuage.b", h: "nuage.hi" });
    expect(g.p).toEqual(["nuage.b", null, "nuage.hi"]);
  });
});

describe("sprite and tones", () => {
  it("stacks layers with their class and style", () => {
    const s = sprite(2, 2);
    s.calque();
    s.calque("anim-vapeur", delai(-0.4));
    expect(s.calques.map((c) => c.classe)).toEqual(["", "anim-vapeur"]);
    expect(s.calques[1]?.style?.animationDelay).toBe("-0.4s");
  });

  it("names the five tones of a family and of a state", () => {
    expect(R("bois").s).toBe("bois.s");
    expect(E("fait").hi).toBe("etat-fait.hi");
  });
});

describe("cuire", () => {
  it("outlines the silhouette and lights its top-left edge, but never a state token", () => {
    const s = sprite(6, 6);
    s.calque().rect(1, 1, 2, 2, "metal.b");
    s.calque().rect(4, 4, 1, 1, "etat-actif.b");
    cuire(s);
    expect(s.calques[0]?.g.get(0, 1)).toBe("metal.ol");
    expect(s.calques[0]?.g.get(1, 1)).toBe("metal.b~r");
    expect(s.calques[1]?.g.get(4, 4)).toBe("etat-actif.b");
    expect(s.calques[1]?.g.get(3, 4)).toBeNull();
  });
});

describe("tracer", () => {
  it("gives one path per bare token, one rim path and one path per glow step", () => {
    const g = new Grille(3, 1);
    g.p[0] = "metal.b~r";
    g.p[1] = "metal.b^actif^2";
    g.p[2] = "bois.b";
    const { fond, lisere, lueurs } = tracer(g);
    expect(fond.map((f) => f.jeton)).toEqual(["metal.b", "bois.b"]);
    expect(lisere).toBe("M0 0h1v1h-1z");
    expect(lueurs).toEqual([{ etat: "actif", palier: 2, d: "M1 0h1v1h-1z" }]);
  });
});
