import { beforeEach, describe, expect, it } from "vitest";
import { lireRecents, MAX_RECENTS, noterRecent } from "./fichiersRecents";

describe("fichiersRecents", () => {
  beforeEach(() => localStorage.clear());

  it("keeps the recent files per project", () => {
    noterRecent("a", "/a/x.py");
    noterRecent("b", "/b/y.py");
    expect(lireRecents("a")).toEqual(["/a/x.py"]);
    expect(lireRecents("b")).toEqual(["/b/y.py"]);
    expect(lireRecents("c")).toEqual([]);
  });

  it("keeps only the five most recent files, newest first", () => {
    for (let i = 1; i <= 7; i += 1) noterRecent("a", `/a/f${i}.py`);
    const liste = lireRecents("a");
    expect(liste).toHaveLength(MAX_RECENTS);
    expect(liste).toEqual([
      "/a/f7.py",
      "/a/f6.py",
      "/a/f5.py",
      "/a/f4.py",
      "/a/f3.py",
    ]);
  });

  it("moves a file reopened to the front without duplicating it", () => {
    noterRecent("a", "/a/x.py");
    noterRecent("a", "/a/y.py");
    expect(noterRecent("a", "/a/x.py")).toEqual(["/a/x.py", "/a/y.py"]);
  });

  it("falls back to an empty list when the stored value is unreadable", () => {
    localStorage.setItem("tessera.ui.fichiers-recents.a", "{pas du json");
    expect(lireRecents("a")).toEqual([]);
    localStorage.setItem("tessera.ui.fichiers-recents.a", JSON.stringify([1, 2]));
    expect(lireRecents("a")).toEqual([]);
  });
});
