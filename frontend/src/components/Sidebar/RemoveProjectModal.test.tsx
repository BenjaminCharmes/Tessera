import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { api } from "../../lib/api";
import RemoveProjectModal from "./RemoveProjectModal";
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

describe("RemoveProjectModal", () => {
  it("nomme le chemin réellement visé", async () => {
    vi.spyOn(api.git, "removalPlan").mockResolvedValue({
      project_id: "mon-projet",
      real_path: "C:/Users/moi/workspace/mon-projet",
      is_symlink: false,
      unpushed_commits: 0,
    });

    render(
      <RemoveProjectModal project={project} onClose={() => {}} onRemoved={() => {}} />,
    );

    await waitFor(() =>
      expect(
        screen.getByText("C:/Users/moi/workspace/mon-projet"),
      ).toBeInTheDocument(),
    );
  });

  it("rassure explicitement sur la cible d'un lien symbolique", async () => {
    // Le point critique : `projects/fluentdb` EST `Desktop/fluentdb`.
    vi.spyOn(api.git, "removalPlan").mockResolvedValue({
      project_id: "mon-projet",
      real_path: "C:/Users/moi/Desktop/fluentdb",
      is_symlink: true,
      unpushed_commits: 0,
    });

    render(
      <RemoveProjectModal project={project} onClose={() => {}} onRemoved={() => {}} />,
    );

    await waitFor(() =>
      expect(screen.getByText(/ne touchera à son contenu/)).toBeInTheDocument(),
    );
  });

  it("avertit des commits non poussés", async () => {
    vi.spyOn(api.git, "removalPlan").mockResolvedValue({
      project_id: "mon-projet",
      real_path: "/w/mon-projet",
      is_symlink: false,
      unpushed_commits: 3,
    });

    render(
      <RemoveProjectModal project={project} onClose={() => {}} onRemoved={() => {}} />,
    );

    await waitFor(() =>
      expect(screen.getByText(/3 commit\(s\) non poussé\(s\)/)).toBeInTheDocument(),
    );
  });

  it("retire sans supprimer au clic sur « Retirer de l'IDE »", async () => {
    vi.spyOn(api.git, "removalPlan").mockResolvedValue({
      project_id: "mon-projet",
      real_path: "/w/mon-projet",
      is_symlink: false,
      unpushed_commits: 0,
    });
    const detach = vi
      .spyOn(api.git, "detach")
      .mockResolvedValue({ detached: true, moved_to: "/ailleurs/mon-projet" });
    const onRemoved = vi.fn();

    const user = userEvent.setup();
    render(
      <RemoveProjectModal project={project} onClose={() => {}} onRemoved={onRemoved} />,
    );

    await user.click(await screen.findByRole("button", { name: /Retirer de l'IDE/ }));

    expect(detach).toHaveBeenCalledWith("mon-projet");
    await waitFor(() => expect(onRemoved).toHaveBeenCalled());
  });

  it("exige une seconde confirmation pour la suppression définitive", async () => {
    vi.spyOn(api.git, "removalPlan").mockResolvedValue({
      project_id: "mon-projet",
      real_path: "/w/mon-projet",
      is_symlink: false,
      unpushed_commits: 0,
    });
    const remove = vi.spyOn(api.git, "remove").mockResolvedValue(undefined);

    const user = userEvent.setup();
    render(
      <RemoveProjectModal project={project} onClose={() => {}} onRemoved={() => {}} />,
    );

    await user.click(
      await screen.findByRole("button", { name: /Supprimer définitivement/ }),
    );
    // Le premier clic ne supprime rien : il déplie la confirmation.
    expect(remove).not.toHaveBeenCalled();

    await user.click(
      screen.getByRole("button", { name: "Confirmer la suppression" }),
    );
    expect(remove).toHaveBeenCalledWith("mon-projet");
  });
});
