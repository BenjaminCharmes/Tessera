import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { useProjetMemorise } from "./useProjetMemorise";
import type { Project } from "../types/api";

function projet(id: string): Project {
  return {
    id,
    name: id,
    path: `/ws/${id}`,
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
  };
}

describe("useProjetMemorise", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("reselectionne le projet memorise quand la liste arrive", () => {
    window.localStorage.setItem("tessera.ui.projet", JSON.stringify("demineur"));
    const selectionner = vi.fn();
    const projets = [projet("ide-core"), projet("demineur")];

    renderHook(() => useProjetMemorise(projets, null, selectionner));

    expect(selectionner).toHaveBeenCalledWith(projets[1]);
  });

  it("ne selectionne rien quand le projet memorise a disparu", () => {
    window.localStorage.setItem("tessera.ui.projet", JSON.stringify("supprime"));
    const selectionner = vi.fn();

    renderHook(() => useProjetMemorise([projet("ide-core")], null, selectionner));

    expect(selectionner).not.toHaveBeenCalled();
  });

  it("ne restaure qu'une fois, pas apres que l'utilisateur a deselectionne", () => {
    window.localStorage.setItem("tessera.ui.projet", JSON.stringify("ide-core"));
    const selectionner = vi.fn();
    const projets = [projet("ide-core")];

    const { rerender } = renderHook(
      ({ courant }: { courant: Project | null }) =>
        useProjetMemorise(projets, courant, selectionner),
      { initialProps: { courant: null as Project | null } },
    );
    rerender({ courant: projets[0] });
    rerender({ courant: null });

    expect(selectionner).toHaveBeenCalledTimes(1);
  });
});
