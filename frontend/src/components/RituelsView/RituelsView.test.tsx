import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import RituelsView from ".";
import { useRituels } from "../../hooks/useRituels";
import type { UseRituelsResult } from "../../hooks/useRituels";
import type { Rituel } from "../../lib/apiRituels";
import type { Project } from "../../types/api";

function rituel(surcharge: Partial<Rituel>): Rituel {
  return {
    id: "r1",
    titre: "Point revenus",
    rythme: { type: "hebdo", jour: "lundi", heure: "18:30:00" },
    duree_min: 30,
    phrase: "point revenus",
    detail: "Chiffres de la semaine.",
    projets: [],
    statut: "en_retard",
    derniere: "2026-11-09T18:30:00",
    prochaine: "2026-11-16T18:30:00",
    depasse: false,
    fait_le: null,
    reporte_jusqua: null,
    ...surcharge,
  };
}

function etat(rituels: Rituel[], erreur: string | null = null): UseRituelsResult {
  return {
    rituels,
    enRetard: rituels.filter((r) => r.statut === "en_retard").length,
    erreur,
    fait: vi.fn().mockResolvedValue(undefined),
    reporter: vi.fn().mockResolvedValue(undefined),
  };
}

describe("RituelsView", () => {
  it("ranges a late ritual under « À faire » and an upcoming one under « À venir »", () => {
    const rituels = etat([
      rituel({ id: "a", titre: "Retard" }),
      rituel({ id: "b", titre: "Demain", statut: "a_venir" }),
    ]);
    render(<RituelsView rituels={rituels} projets={[]} />);
    const aFaire = screen.getByRole("region", { name: "À faire" });
    const aVenir = screen.getByRole("region", { name: "À venir" });
    expect(within(aFaire).getByText("Retard")).toBeInTheDocument();
    expect(within(aFaire).queryByText("Demain")).toBeNull();
    expect(within(aVenir).getByText("Demain")).toBeInTheDocument();
  });

  it("shows the error of the answer at the top", () => {
    render(<RituelsView rituels={etat([], "rituels.md illisible")} projets={[]} />);
    expect(screen.getByRole("alert")).toHaveTextContent("rituels.md illisible");
  });

  it("calls fait with the ritual id on « Fait »", async () => {
    const rituels = etat([rituel({ id: "abc" })]);
    render(<RituelsView rituels={rituels} projets={[]} />);
    await userEvent.click(screen.getByRole("button", { name: "Fait" }));
    expect(rituels.fait).toHaveBeenCalledWith("abc");
  });

  it("writes the phrase to the clipboard on « Copier »", async () => {
    const writeText = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    // userEvent.setup installe son propre presse-papiers : on le surveille après coup.
    vi.spyOn(navigator.clipboard, "writeText").mockImplementation(writeText);
    render(<RituelsView rituels={etat([rituel({ phrase: "ouvrir Vigie" })])} projets={[]} />);
    await user.click(screen.getByRole("button", { name: "Copier" }));
    expect(writeText).toHaveBeenCalledWith("ouvrir Vigie");
  });

  it("opens the project of an entry of `projets`", async () => {
    const projet = { id: "vigie", name: "Vigie" } as Project;
    const onOpenProject = vi.fn();
    render(
      <RituelsView
        rituels={etat([rituel({ projets: ["vigie"] })])}
        projets={[projet]}
        onOpenProject={onOpenProject}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Ouvrir Vigie" }));
    expect(onOpenProject).toHaveBeenCalledWith(projet);
  });

  it("shows an overdue ritual in red", () => {
    render(<RituelsView rituels={etat([rituel({ depasse: true })])} projets={[]} />);
    expect(screen.getByText(/Dépassé/).className).toMatch(/text-red-/);
  });
});

describe("useRituels", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  function Sonde() {
    const r = useRituels();
    return (
      <>
        <span data-testid="retard">{r.enRetard}</span>
        <button onClick={() => void r.fait("abc")}>fait</button>
      </>
    );
  }

  it("posts to /fait then reads the list again", async () => {
    const appels: string[] = [];
    const liste = { rituels: [rituel({ id: "abc" })], erreur: null };
    vi.stubGlobal(
      "fetch",
      vi.fn(async (url: string, init?: RequestInit) => {
        appels.push(`${init?.method ?? "GET"} ${url.slice(url.indexOf("/api/v1"))}`);
        if (init?.method === "POST") return new Response(null, { status: 204 });
        return new Response(JSON.stringify(liste), { status: 200 });
      }),
    );
    render(<Sonde />);
    await waitFor(() => expect(screen.getByTestId("retard")).toHaveTextContent("1"));
    await userEvent.click(screen.getByText("fait"));
    await waitFor(() => expect(appels).toHaveLength(3));
    expect(appels).toEqual([
      "GET /api/v1/rituels",
      "POST /api/v1/rituels/abc/fait",
      "GET /api/v1/rituels",
    ]);
    vi.unstubAllGlobals();
  });
});
