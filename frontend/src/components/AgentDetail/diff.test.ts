import { describe, it, expect } from "vitest";
import { diffLignes } from "./diff";

describe("diffLignes", () => {
  it("keeps unchanged lines as context and marks the edit", () => {
    const d = diffLignes("a\nb\nc", "a\nB\nc");
    expect(d).toEqual([
      { type: "contexte", texte: "a" },
      { type: "retrait", texte: "b" },
      { type: "ajout", texte: "B" },
      { type: "contexte", texte: "c" },
    ]);
  });

  it("handles one small edit inside a very long prompt", () => {
    // ticket-226 : le préfixe et le suffixe communs sortent du calcul, sinon
    // la table LCS pesait n × m cellules pour une seule ligne changée.
    const lignes = Array.from({ length: 20_000 }, (_, i) => `ligne ${i}`);
    const apres = [...lignes];
    apres[10_000] = "modifiée";
    const d = diffLignes(lignes.join("\n"), apres.join("\n"));
    expect(d.filter((l) => l.type !== "contexte")).toEqual([
      { type: "retrait", texte: "ligne 10000" },
      { type: "ajout", texte: "modifiée" },
    ]);
  });

  it("falls back to a whole replacement when both texts differ everywhere", () => {
    // Audit sécurité du ticket-226 : sans borne, deux textes de 5 000 lignes
    // toutes différentes allouaient 25 millions de cellules.
    const avant = Array.from({ length: 5_000 }, (_, i) => `a${i}`).join("\n");
    const apres = Array.from({ length: 5_000 }, (_, i) => `b${i}`).join("\n");
    const d = diffLignes(avant, apres);
    expect(d.filter((l) => l.type === "retrait")).toHaveLength(5_000);
    expect(d.filter((l) => l.type === "ajout")).toHaveLength(5_000);
    expect(d[0]).toEqual({ type: "retrait", texte: "a0" });
  });
});
