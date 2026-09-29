import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AgentBlock from "./AgentBlock";

const COMPTE_RENDU = "Voici ce que le codeur a fait :\n- écrit le service\n- ajouté les tests";

describe("AgentBlock — codeur", () => {
  it("affiche le compte rendu depuis doneContent quand les tokens sont vides", async () => {
    render(
      <AgentBlock
        agent="codeur"
        tokens=""
        isActive={false}
        isDone={true}
        doneContent={COMPTE_RENDU}
      />,
    );

    // Le bouton de dépliage doit être visible (compte rendu replié par défaut).
    const bouton = screen.getByRole("button", { name: /voir le compte rendu/i });
    expect(bouton).toBeInTheDocument();

    // Après le clic, le contenu doit apparaître.
    await userEvent.click(bouton);
    expect(screen.getByText(/écrit le service/)).toBeInTheDocument();
  });

  it("est replié par défaut — le contenu n'est pas visible avant le clic", () => {
    render(
      <AgentBlock
        agent="codeur"
        tokens=""
        isActive={false}
        isDone={true}
        doneContent={COMPTE_RENDU}
      />,
    );

    expect(screen.queryByText(/écrit le service/)).toBeNull();
  });

  it("déplie puis replie le compte rendu au deuxième clic", async () => {
    render(
      <AgentBlock
        agent="codeur"
        tokens=""
        isActive={false}
        isDone={true}
        doneContent={COMPTE_RENDU}
      />,
    );

    const bouton = screen.getByRole("button", { name: /voir le compte rendu/i });
    await userEvent.click(bouton);
    expect(screen.getByText(/écrit le service/)).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /masquer/i }));
    expect(screen.queryByText(/écrit le service/)).toBeNull();
  });

  it("affiche les tokens en direct quand ils sont plus longs que doneContent (non-régression)", () => {
    const tokensLongs = "A".repeat(200);
    render(
      <AgentBlock
        agent="codeur"
        tokens={tokensLongs}
        isActive={true}
        isDone={false}
        doneContent="court"
      />,
    );

    // TokenStream doit être affiché, pas le bouton de compte rendu.
    expect(screen.queryByRole("button", { name: /voir le compte rendu/i })).toBeNull();
    expect(screen.getByText(tokensLongs)).toBeInTheDocument();
  });

  it("affiche les tokens quand le codeur est terminé et que les tokens sont plus longs que doneContent", () => {
    const tokensLongs = "A".repeat(200);
    render(
      <AgentBlock
        agent="codeur"
        tokens={tokensLongs}
        isActive={false}
        isDone={true}
        doneContent="court"
      />,
    );

    expect(screen.queryByRole("button", { name: /voir le compte rendu/i })).toBeNull();
    expect(screen.getByText(tokensLongs)).toBeInTheDocument();
  });

  it("n'affiche pas le bouton de compte rendu sans doneContent", () => {
    render(
      <AgentBlock
        agent="codeur"
        tokens=""
        isActive={false}
        isDone={true}
      />,
    );

    expect(screen.queryByRole("button", { name: /voir le compte rendu/i })).toBeNull();
  });
});
