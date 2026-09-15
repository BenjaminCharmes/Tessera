import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../../lib/api";
import GitLinkPanel from "./GitLinkPanel";
import type { Project } from "../../types/api";

const project: Project = {
  id: "mon-projet",
  name: "mon-projet",
  path: "/w/mon-projet",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

beforeEach(() => vi.restoreAllMocks());

describe("GitLinkPanel", () => {
  it("n'affiche rien sans projet sélectionné", () => {
    const { container } = render(<GitLinkPanel project={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it("avertit qu'un projet non versionné ne produira ni branche ni commit", async () => {
    vi.spyOn(api.git, "status").mockResolvedValue({
      is_repository: false,
      has_commits: false,
      remote_url: null,
      nested_in: null,
    });

    render(<GitLinkPanel project={project} />);

    await waitFor(() =>
      expect(screen.getByText(/n'est pas versionné/)).toBeInTheDocument(),
    );
    expect(screen.getByText(/ni branche ni commit/)).toBeInTheDocument();
  });

  it("signale un projet imbriqué dans un dépôt qui n'est pas le sien", async () => {
    vi.spyOn(api.git, "status").mockResolvedValue({
      is_repository: false,
      has_commits: false,
      remote_url: null,
      nested_in: "C:/Users/moi/Desktop/project",
    });

    render(<GitLinkPanel project={project} />);

    await waitFor(() =>
      expect(screen.getByText("C:/Users/moi/Desktop/project")).toBeInTheDocument(),
    );
  });

  it("propose de lier un dépôt quand le projet est versionné sans remote", async () => {
    vi.spyOn(api.git, "status").mockResolvedValue({
      is_repository: true,
      has_commits: true,
      remote_url: null,
      nested_in: null,
    });
    const link = vi.spyOn(api.git, "link").mockResolvedValue({
      is_repository: true,
      has_commits: true,
      remote_url: "https://github.com/moi/repo.git",
      nested_in: null,
    });

    const user = userEvent.setup();
    render(<GitLinkPanel project={project} />);

    const input = await screen.findByLabelText("URL du dépôt GitHub");
    await user.type(input, "https://github.com/moi/repo.git");
    await user.click(screen.getByRole("button", { name: "Lier à ce dépôt" }));

    // Le troisième argument est la confirmation, explicitement à false : lier
    // sans confirmer est le cas nominal, confirmer est l'exception.
    expect(link).toHaveBeenCalledWith(
      "mon-projet",
      "https://github.com/moi/repo.git",
      false,
    );
  });

  it("montre le remote quand le projet est déjà lié", async () => {
    vi.spyOn(api.git, "status").mockResolvedValue({
      is_repository: true,
      has_commits: true,
      remote_url: "https://github.com/moi/repo.git",
      nested_in: null,
    });

    render(<GitLinkPanel project={project} />);

    await waitFor(() =>
      expect(screen.getByText("https://github.com/moi/repo.git")).toBeInTheDocument(),
    );
  });

  it("propose de confirmer quand le dépôt distant n'est pas vide", async () => {
    // Un 409 n'est pas une erreur : c'est une décision qui revient à
    // l'utilisateur.
    vi.spyOn(api.git, "status").mockResolvedValue({
      is_repository: true,
      has_commits: true,
      remote_url: null,
      nested_in: null,
    });
    vi.spyOn(api.git, "link").mockRejectedValue(
      new Error("API 409: le dépôt n'est pas vide"),
    );

    const user = userEvent.setup();
    render(<GitLinkPanel project={project} />);

    const input = await screen.findByLabelText("URL du dépôt GitHub");
    await user.type(input, "https://github.com/moi/repo.git");
    await user.click(screen.getByRole("button", { name: "Lier à ce dépôt" }));

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Lier quand même" }),
      ).toBeInTheDocument(),
    );
  });
});
