import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import ProjectHeader from "./ProjectHeader";
import type { Project } from "../../types/api";

const projet: Project = {
  id: "lyra",
  name: "Lyra",
  path: "C:\\Users\\moi\\Desktop\\projets\\Lyra",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

describe("ProjectHeader", () => {
  it("montre les actions du projet sans avoir a scroller", () => {
    // Panne d'usage : lier un depot, changer le mode des artefacts ou retirer
    // le projet vivaient sous la liste des tickets, donc en bas d'une colonne
    // qui defile. On ne les trouvait qu'en cherchant.
    render(<ProjectHeader project={projet} gitOuvert={false} onBasculerGit={() => {}} />);

    expect(screen.getByText("Lyra")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /VSCode/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Git" })).toBeInTheDocument();
  });

  it("ouvre le projet dans VSCode par son chemin sur le disque", () => {
    render(<ProjectHeader project={projet} gitOuvert={false} onBasculerGit={() => {}} />);

    expect(screen.getByRole("link", { name: /VSCode/i })).toHaveAttribute(
      "href",
      "vscode://file/C:/Users/moi/Desktop/projets/Lyra",
    );
  });

  it("bascule la section git", async () => {
    const onBasculerGit = vi.fn();
    render(<ProjectHeader project={projet} gitOuvert={false} onBasculerGit={onBasculerGit} />);

    await userEvent.click(screen.getByRole("button", { name: "Git" }));

    expect(onBasculerGit).toHaveBeenCalled();
  });

  it("invite a choisir un projet quand aucun n'est actif", () => {
    render(<ProjectHeader project={null} gitOuvert={false} onBasculerGit={() => {}} />);

    expect(screen.getByText(/Aucun projet/i)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /VSCode/i })).not.toBeInTheDocument();
  });

  it("survit a un projet sans chemin au lieu d'emporter la sidebar", () => {
    // Panne vecue (E2E flow 4 et 5) : `lienVSCode(undefined)` levait une
    // TypeError, que l'ErrorBoundary transformait en « Une erreur inattendue
    // s'est produite » a la place de toute la colonne. Un champ absent ne doit
    // couter que le bouton qui en depend.
    const sansChemin = { ...projet, path: undefined as unknown as string };

    render(
      <ProjectHeader project={sansChemin} gitOuvert={false} onBasculerGit={() => {}} />,
    );

    expect(screen.getByText("Lyra")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /VSCode/i })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Git" })).toBeInTheDocument();
  });
});
