import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  cheminAbsolu,
  cheminRelatif,
  filtrerFichiers,
  listerFichiers,
  MAX_RESULTATS,
} from "./indexFichiers";
import type { DirEntry } from "./fs";

vi.mock("./fs");
import { listEntries } from "./fs";

const lister = vi.mocked(listEntries);
const e = (name: string, path: string, is_dir = false): DirEntry => ({ name, path, is_dir });

describe("listerFichiers", () => {
  beforeEach(() => lister.mockReset());

  it("walks the folders and skips generated ones", async () => {
    const arbre: Record<string, DirEntry[]> = {
      "/p": [e("src", "/p/src", true), e("node_modules", "/p/node_modules", true), e("a.md", "/p/a.md")],
      "/p/src": [e("b.py", "/p/src/b.py")],
      "/p/node_modules": [e("junk.js", "/p/node_modules/junk.js")],
    };
    lister.mockImplementation((chemin) => Promise.resolve(arbre[chemin] ?? []));
    expect((await listerFichiers("/p")).sort()).toEqual(["/p/a.md", "/p/src/b.py"]);
  });

  it("ignores an unreadable folder instead of failing", async () => {
    lister
      .mockResolvedValueOnce([e("bad", "/p/bad", true), e("a.md", "/p/a.md")])
      .mockRejectedValueOnce(new Error("denied"));
    expect(await listerFichiers("/p")).toEqual(["/p/a.md"]);
  });
});

describe("cheminRelatif / cheminAbsolu", () => {
  it("strips the project root, whatever the separators", () => {
    expect(cheminRelatif("C:\\work\\p", "C:\\work\\p\\src\\a.py")).toBe("src/a.py");
    expect(cheminRelatif("/p/", "/p/a.py")).toBe("a.py");
    expect(cheminRelatif("/p", "/ailleurs/a.py")).toBe("/ailleurs/a.py");
  });

  it("joins a relative path to the project root", () => {
    expect(cheminAbsolu("/p/", "src/a.py")).toBe("/p/src/a.py");
  });
});

describe("filtrerFichiers", () => {
  const fichiers = ["/p/src/App.tsx", "/p/src/util.ts", "/p/README.md"];

  it("matches the relative path without regard to case", () => {
    expect(filtrerFichiers(fichiers, "/p", "app")).toEqual(["/p/src/App.tsx"]);
  });

  it("returns nothing for an empty query", () => {
    expect(filtrerFichiers(fichiers, "/p", "  ")).toEqual([]);
  });

  it("does not match the project root itself", () => {
    expect(filtrerFichiers(fichiers, "/p", "/p")).toEqual([]);
  });

  it("caps the number of results", () => {
    const beaucoup = Array.from({ length: 50 }, (_, i) => `/p/f${i}.py`);
    expect(filtrerFichiers(beaucoup, "/p", "f")).toHaveLength(MAX_RESULTATS);
  });
});
