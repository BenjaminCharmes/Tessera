import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ChoixDuProjet from "./ChoixDuProjet";
import { api } from "../lib/api";
import { titreEtSousTitre } from "../lib/titreDuProjet";
import type { Project } from "../types/projets";

function projet(id: string, name: string): Project {
  return { id, name, path: `/p/${id}`, description: "", active_agents: [], stack: null, raw_claude_md: "", github_remote: null };
}

describe("titreEtSousTitre", () => {
  it("splits a name on its em dash", () => {
    expect(titreEtSousTitre("Kadoomi — listes d'envies")).toEqual({ titre: "Kadoomi", sousTitre: "listes d'envies" });
  });

  it("keeps a name without dash whole", () => {
    expect(titreEtSousTitre("FluentDB")).toEqual({ titre: "FluentDB", sousTitre: null });
  });
});

describe("ChoixDuProjet", () => {
  beforeEach(() => {
    vi.spyOn(api.projects, "overview").mockResolvedValue([]);
  });

  it("says which view waits for a project and lists the projects by name", () => {
    render(<ChoixDuProjet vue="ses tickets" projets={[projet("v", "Vigie"), projet("a", "Affût")]} onSelectProject={vi.fn()} />);

    expect(screen.getByRole("heading", { name: "Sur quel projet travailles-tu ?" })).toBeInTheDocument();
    expect(screen.getByText(/voir ses tickets/)).toBeInTheDocument();
    const noms = screen.getAllByRole("button").map((b) => b.textContent);
    // L'initiale précède le nom tant que les icônes ne sont pas lues.
    expect(noms).toEqual(["AAffût", "VVigie"]);
  });

  it("selects the clicked project", async () => {
    const choisir = vi.fn();
    const vigie = projet("v", "Vigie — veille tech");
    render(<ChoixDuProjet vue="ses fichiers" projets={[vigie]} onSelectProject={choisir} />);

    await userEvent.click(screen.getByRole("button", { name: /Vigie/ }));
    expect(choisir).toHaveBeenCalledWith(vigie);
  });
});

describe("ChoixDuProjet — icône", () => {
  it("shows the project's icon once the overviews are read", async () => {
    vi.spyOn(api.projects, "overview").mockResolvedValue([{ id: "v", icon: true } as never]);
    render(<ChoixDuProjet vue="ses tickets" projets={[projet("v", "Vigie")]} onSelectProject={vi.fn()} />);

    expect(await screen.findByRole("button", { name: /Vigie/ })).toContainElement(document.querySelector("img"));
  });
});
