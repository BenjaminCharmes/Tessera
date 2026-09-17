import { describe, expect, it } from "vitest";
import { decouperDiff } from "./parse";

const DIFF = [
  "diff --git a/app.py b/app.py",
  "index e87df15..397668e 100644",
  "--- a/app.py",
  "+++ b/app.py",
  "@@ -1,3 +1,3 @@",
  " inchange",
  "-ancien",
  "+nouveau",
  "diff --git a/README.md b/README.md",
  "--- a/README.md",
  "+++ b/README.md",
  "@@ -1 +1,2 @@",
  "+ajout",
].join("\n");

describe("decouperDiff", () => {
  it("separe les fichiers", () => {
    expect(decouperDiff(DIFF).map((f) => f.chemin)).toEqual([
      "app.py",
      "README.md",
    ]);
  });

  it("compte les ajouts et les retraits par fichier", () => {
    const [app, readme] = decouperDiff(DIFF);
    expect(app).toMatchObject({ ajouts: 1, retraits: 1 });
    expect(readme).toMatchObject({ ajouts: 1, retraits: 0 });
  });

  it("type chaque ligne pour que l'affichage n'ait qu'a peindre", () => {
    const [app] = decouperDiff(DIFF)!;
    expect(app!.lignes.map((l) => l.type)).toEqual([
      "hunk",
      "contexte",
      "retrait",
      "ajout",
    ]);
  });

  it("ecarte le bruit qui ne se lit pas", () => {
    const texte = decouperDiff(DIFF).flatMap((f) => f.lignes).map((l) => l.texte);
    expect(texte.some((t) => t.startsWith("index "))).toBe(false);
    expect(texte.some((t) => t.startsWith("+++"))).toBe(false);
  });

  it("rend une liste vide pour un diff vide", () => {
    expect(decouperDiff("")).toEqual([]);
  });
});
