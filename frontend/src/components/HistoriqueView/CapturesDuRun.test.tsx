import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import DetailDuRun from "./DetailDuRun";
import { oublierJeton, saisirJeton } from "../../lib/auth";
import { _viderCacheResource } from "../../hooks/useResource";
import type { PipelineRun, Project } from "../../types/api";

// Le fil rejoué appelle l'API aussi : une doublure, on ne teste que les captures.
vi.mock("../StatsView/RunHistorique", () => ({ default: () => <div /> }));

const RUN: PipelineRun = {
  id: "r1",
  ticket_id: "ticket-620",
  started_at: "2026-10-29T07:00:00Z",
  finished_at: "2026-10-29T07:10:00Z",
  rounds: 1,
  approved: true,
  final_status: "done",
  total_cost_usd: 1,
};

const PROJET: Project = {
  id: "p1",
  name: "P1",
  path: "/p1",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

function repondre(captures: string[]) {
  const fetchSimule = vi.fn<typeof fetch>(
    async () => new Response(JSON.stringify({ captures })),
  );
  vi.stubGlobal("fetch", fetchSimule);
  return fetchSimule;
}

function afficher() {
  render(<DetailDuRun run={RUN} ticket={null} project={PROJET} />);
}

describe("DetailDuRun — captures du run (ticket-620)", () => {
  beforeEach(() => _viderCacheResource());
  afterEach(() => vi.unstubAllGlobals());

  it("shows no Captures section for a run that captured nothing", async () => {
    const fetchSimule = repondre([]);
    afficher();
    await waitFor(() => expect(fetchSimule).toHaveBeenCalled());
    expect(screen.queryByRole("region", { name: "Captures" })).not.toBeInTheDocument();
    expect(screen.queryByText("Captures")).not.toBeInTheDocument();
  });

  it("shows no section when the list cannot be read", async () => {
    const fetchSimule = vi.fn(async () => new Response("boom", { status: 500 }));
    vi.stubGlobal("fetch", fetchSimule);
    afficher();
    await waitFor(() => expect(fetchSimule).toHaveBeenCalled());
    expect(screen.queryByText("Captures")).not.toBeInTheDocument();
  });

  it("asks for the images of the run's ticket", async () => {
    const fetchSimule = repondre([]);
    afficher();
    await waitFor(() => expect(fetchSimule).toHaveBeenCalled());
    expect(String(fetchSimule.mock.calls[0]?.[0])).toBe(
      "/api/v1/projects/p1/captures?ticket=ticket-620",
    );
  });

  it("draws one thumbnail per image, grouped by screen, with width and theme", async () => {
    repondre(["accueil-1280-sombre.png", "accueil-390-clair.png", "liste-390-clair.png"]);
    afficher();

    const section = await screen.findByRole("region", { name: "Captures" });
    const vignettes = within(section).getAllByRole("button");
    expect(vignettes).toHaveLength(3);
    expect(within(section).getByText("accueil")).toBeInTheDocument();
    expect(within(section).getByText("liste")).toBeInTheDocument();
    // Au sein d'un écran : largeur croissante.
    expect(vignettes[0]).toHaveTextContent("390 px · clair");
    expect(vignettes[1]).toHaveTextContent("1280 px · sombre");
    expect(vignettes[0].querySelector("img")).toHaveAttribute(
      "src",
      "/api/v1/projects/p1/captures/accueil-390-clair.png?ticket=ticket-620",
    );
  });

  describe("with a session token", () => {
    const creer = URL.createObjectURL;
    const revoquer = URL.revokeObjectURL;

    afterEach(() => {
      oublierJeton();
      URL.createObjectURL = creer;
      URL.revokeObjectURL = revoquer;
    });

    it("loads each image with the Authorization header, shows an object URL, and revokes it on unmount", async () => {
      saisirJeton("secret-de-test");
      const revoque = vi.fn<(url: string) => void>();
      URL.createObjectURL = vi.fn(() => "blob:http://localhost/capture");
      URL.revokeObjectURL = revoque;
      const fetchSimule = vi.fn<typeof fetch>(async (adresse) =>
        String(adresse).includes("/captures/")
          ? new Response(new Uint8Array([137, 80, 78, 71]))
          : new Response(JSON.stringify({ captures: ["accueil-390-clair.png"] })),
      );
      vi.stubGlobal("fetch", fetchSimule);
      const { container, unmount } = render(<DetailDuRun run={RUN} ticket={null} project={PROJET} />);

      await waitFor(() => expect(container.querySelector("img")).not.toBeNull());
      const image = fetchSimule.mock.calls.find(([a]) => String(a).includes("/captures/accueil"));
      expect(String(image?.[0])).toBe("/api/v1/projects/p1/captures/accueil-390-clair.png?ticket=ticket-620");
      expect(new Headers(image?.[1]?.headers).get("Authorization")).toBe("Bearer secret-de-test");
      for (const img of container.querySelectorAll("img")) {
        expect(img.getAttribute("src")).toBe("blob:http://localhost/capture");
        expect(img.getAttribute("src")).not.toContain("token=");
      }

      unmount();
      expect(revoque).toHaveBeenCalledWith("blob:http://localhost/capture");
    });
  });

  it("opens a thumbnail in large and closes it", async () => {
    repondre(["accueil-390-clair.png"]);
    afficher();

    await userEvent.click(await screen.findByRole("button", { name: "accueil — 390 px · clair" }));
    const fenetre = screen.getByRole("dialog");
    expect(within(fenetre).getByRole("img", { name: "accueil, 390 px · clair" })).toHaveAttribute(
      "src",
      "/api/v1/projects/p1/captures/accueil-390-clair.png?ticket=ticket-620",
    );

    await userEvent.click(within(fenetre).getByRole("button", { name: "Fermer" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
