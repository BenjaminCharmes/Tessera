import { afterEach, describe, expect, it, vi } from "vitest";
import { grouperParEcran, listerLesCaptures, lireUneCapture, urlDeCapture } from "./capturesDuRun";

describe("capturesDuRun", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("reads the screen, width and theme of a capture name", () => {
    expect(lireUneCapture("page-d-accueil-390-sombre.png")).toEqual({
      fichier: "page-d-accueil-390-sombre.png",
      ecran: "page-d-accueil",
      largeur: 390,
      theme: "sombre",
    });
  });

  it("refuses a name that is not a capture", () => {
    expect(lireUneCapture("notes.txt")).toBeNull();
    expect(lireUneCapture("../x-390-clair.png")).toBeNull();
  });

  it("groups by screen, ordering by width then theme", () => {
    const groupes = grouperParEcran([
      "b-1280-clair.png",
      "a-390-sombre.png",
      "a-390-clair.png",
      "b-390-clair.png",
      "illisible.png",
    ]);
    expect(groupes.map((g) => g.ecran)).toEqual(["b", "a"]);
    expect(groupes[1].captures.map((c) => c.fichier)).toEqual(["a-390-clair.png", "a-390-sombre.png"]);
    expect(groupes[0].captures.map((c) => c.largeur)).toEqual([390, 1280]);
  });

  it("builds the image address with the ticket as a query", () => {
    expect(urlDeCapture("p 1", "ticket-620", "a-390-clair.png")).toBe(
      "/api/v1/projects/p%201/captures/a-390-clair.png?ticket=ticket-620",
    );
  });

  it("lists the names the endpoint returns and fails on an error status", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({ captures: ["a-390-clair.png"] }))));
    await expect(listerLesCaptures("p1", "ticket-620")).resolves.toEqual(["a-390-clair.png"]);

    vi.stubGlobal("fetch", vi.fn(async () => new Response("non", { status: 404 })));
    await expect(listerLesCaptures("p1", "ticket-620")).rejects.toThrow("API 404");
  });
});
