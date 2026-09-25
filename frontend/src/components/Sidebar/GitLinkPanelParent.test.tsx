import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { api } from "../../lib/api";
import GitLinkPanel from "./GitLinkPanel";
import type { Project } from "../../types/api";

const project: Project = {
  id: "ide-core",
  name: "ide-core",
  path: "/w/tessera/projects/ide-core",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

beforeEach(() => vi.restoreAllMocks());

function statutParent() {
  return {
    is_repository: false,
    has_commits: true,
    remote_url: null,
    nested_in: "/w/tessera",
    uses_parent_repository: true,
  };
}

describe("GitLinkPanel — le dépôt parent est déclaré (ticket-171)", () => {
  it("n'annonce pas le projet comme non versionné", async () => {
    vi.spyOn(api.git, "status").mockResolvedValue(statutParent());

    render(<GitLinkPanel project={project} />);

    await waitFor(() =>
      expect(screen.getByText(/travaille dans le dépôt/)).toBeInTheDocument(),
    );
    expect(screen.queryByText(/n'est pas versionné/)).toBeNull();
  });

  it("n'offre pas d'initialiser un dépôt, qui serait imbriqué", async () => {
    // Cliquer créait un dépôt dans celui de Tessera — ce qu'ADR-024 empêche.
    vi.spyOn(api.git, "status").mockResolvedValue(statutParent());

    render(<GitLinkPanel project={project} />);

    await waitFor(() =>
      expect(screen.getByText(/travaille dans le dépôt/)).toBeInTheDocument(),
    );
    expect(screen.queryByRole("button", { name: /Initialiser/ })).toBeNull();
  });

  it("nomme le dépôt dans lequel il travaille", async () => {
    vi.spyOn(api.git, "status").mockResolvedValue(statutParent());

    render(<GitLinkPanel project={project} />);

    await waitFor(() =>
      expect(screen.getByText("/w/tessera")).toBeInTheDocument(),
    );
  });

  it("un projet ordinaire sans dépôt garde son message et son bouton", async () => {
    vi.spyOn(api.git, "status").mockResolvedValue({
      is_repository: false,
      has_commits: false,
      remote_url: null,
      nested_in: null,
      uses_parent_repository: false,
    });

    render(<GitLinkPanel project={project} />);

    await waitFor(() =>
      expect(screen.getByText(/n'est pas versionné/)).toBeInTheDocument(),
    );
    expect(
      screen.getByRole("button", { name: /Initialiser/ }),
    ).toBeInTheDocument();
  });
});
