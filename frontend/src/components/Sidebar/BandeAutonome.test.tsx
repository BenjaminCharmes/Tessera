import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import BandeAutonome from "./BandeAutonome";

describe("BandeAutonome", () => {
  it("ne s'affiche pas quand une file est sélectionnée", () => {
    const { container } = render(
      <BandeAutonome
        selectionVide={false}
        githubLie
        enCours={false}
        onLancer={() => {}}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it("laisse l'IDE choisir les tickets lui-même", async () => {
    const onLancer = vi.fn();
    const user = userEvent.setup();
    render(
      <BandeAutonome
        selectionVide
        githubLie={false}
        enCours={false}
        onLancer={onLancer}
      />,
    );

    await user.click(screen.getByRole("button", { name: /Laisser l'IDE/ }));

    expect(onLancer).toHaveBeenCalledWith({ depuisGithub: false });
  });

  it("propose de partir des issues quand le projet est lié à GitHub", async () => {
    const onLancer = vi.fn();
    const user = userEvent.setup();
    render(
      <BandeAutonome selectionVide githubLie enCours={false} onLancer={onLancer} />,
    );

    await user.click(screen.getByRole("checkbox", { name: /issues/i }));
    await user.click(screen.getByRole("button", { name: /Laisser l'IDE/ }));

    expect(onLancer).toHaveBeenCalledWith({ depuisGithub: true });
  });

  it("ne propose pas les issues sans dépôt GitHub", () => {
    // Un appel réseau vers un dépôt qui n'existe pas n'aurait aucun sens, et
    // la case cochée ne changerait rien : mieux vaut ne pas la montrer.
    render(
      <BandeAutonome
        selectionVide
        githubLie={false}
        enCours={false}
        onLancer={() => {}}
      />,
    );

    expect(screen.queryByRole("checkbox")).toBeNull();
  });

  it("ne relance pas pendant un run", () => {
    render(
      <BandeAutonome selectionVide githubLie enCours onLancer={() => {}} />,
    );

    expect(screen.getByRole("button", { name: /Laisser l'IDE/ })).toBeDisabled();
  });
});
