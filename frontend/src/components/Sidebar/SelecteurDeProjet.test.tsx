import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../../lib/api";
import SelecteurDeProjet from "./SelecteurDeProjet";
import type { Project } from "../../types/api";

function projet(id: string, name = id): Project {
  return {
    id,
    name,
    path: `/w/${id}`,
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
  };
}

beforeEach(() => {
  vi.restoreAllMocks();
  vi.spyOn(api.projects, "list").mockResolvedValue([
    projet("demineur", "Démineur"),
    projet("ide-core"),
    projet("fluentdb"),
  ]);
});

describe("SelecteurDeProjet (ticket-174)", () => {
  it("montre le projet actif sans rien ouvrir", () => {
    render(
      <SelecteurDeProjet project={projet("demineur", "Démineur")} onSelectProject={vi.fn()} />,
    );

    expect(screen.getByRole("button", { expanded: false })).toBeInTheDocument();
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("ouvre la liste des projets au clic", async () => {
    render(
      <SelecteurDeProjet project={projet("demineur", "Démineur")} onSelectProject={vi.fn()} />,
    );

    await userEvent.click(screen.getByRole("button"));

    await waitFor(() =>
      expect(screen.getByRole("option", { name: /ide-core/ })).toBeInTheDocument(),
    );
  });

  it("choisir un projet le remonte et referme la liste", async () => {
    const onSelectProject = vi.fn();
    render(
      <SelecteurDeProjet project={projet("demineur", "Démineur")} onSelectProject={onSelectProject} />,
    );
    await userEvent.click(screen.getByRole("button"));
    const option = await screen.findByRole("option", { name: /fluentdb/ });

    await userEvent.click(option);

    expect(onSelectProject).toHaveBeenCalledWith(
      expect.objectContaining({ id: "fluentdb" }),
    );
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("identifie le projet actif dans la liste", async () => {
    render(
      <SelecteurDeProjet project={projet("demineur", "Démineur")} onSelectProject={vi.fn()} />,
    );

    await userEvent.click(screen.getByRole("button"));

    const actif = await screen.findByRole("option", { name: /Démineur/ });
    expect(actif.getAttribute("aria-selected")).toBe("true");
  });

  it("se referme sur Échap", async () => {
    render(
      <SelecteurDeProjet project={projet("demineur", "Démineur")} onSelectProject={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button"));
    await screen.findByRole("listbox");

    await userEvent.keyboard("{Escape}");

    await waitFor(() => expect(screen.queryByRole("listbox")).toBeNull());
  });

  it("se referme au clic en dehors", async () => {
    render(
      <div>
        <SelecteurDeProjet project={projet("demineur", "Démineur")} onSelectProject={vi.fn()} />
        <button type="button">ailleurs</button>
      </div>,
    );
    await userEvent.click(screen.getByRole("button", { expanded: false }));
    await screen.findByRole("listbox");

    await userEvent.click(screen.getByRole("button", { name: "ailleurs" }));

    await waitFor(() => expect(screen.queryByRole("listbox")).toBeNull());
  });
});

describe("SelecteurDeProjet (ticket-205)", () => {
  it("retire le projet depuis le menu", async () => {
    // L'action vivait au pied du panneau Git, où rien ne l'annonçait.
    const plan = vi.spyOn(api.git, "removalPlan").mockResolvedValue({
      project_id: "demineur",
      real_path: "/w/demineur",
      is_symlink: false,
      unpushed_commits: 0,
    });
    render(
      <SelecteurDeProjet project={projet("demineur", "Démineur")} onSelectProject={vi.fn()} />,
    );
    await userEvent.click(screen.getByRole("button"));

    await userEvent.click(
      await screen.findByRole("button", { name: /Retirer ce projet de l'IDE/ }),
    );

    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(plan).toHaveBeenCalledWith("demineur");
    expect(screen.queryByRole("listbox")).toBeNull();
  });

  it("borne le déclencheur à la largeur de l'en-tête", () => {
    // Un `<button>` prend la largeur de son contenu : sans borne, un nom long
    // passait sous « VSCode » et « Git » au lieu d'être tronqué.
    render(
      <SelecteurDeProjet
        project={projet("portfolio", "Portfolio — un nom beaucoup trop long")}
        onSelectProject={vi.fn()}
      />,
    );

    expect(screen.getByRole("button").className).toContain("max-w-full");
  });
});
