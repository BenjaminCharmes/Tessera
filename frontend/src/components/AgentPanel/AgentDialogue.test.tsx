import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AgentDialogue from "./AgentDialogue";

describe("AgentDialogue", () => {
  it("met la question de l'agent en avant", () => {
    render(
      <AgentDialogue
        pendingQuestion="On casse l'API ?"
        enCours
        onAnswer={() => {}}
        onInterject={() => {}}
      />,
    );

    expect(screen.getByText("On casse l'API ?")).toBeInTheDocument();
  });

  it("envoie la reponse et vide le champ", async () => {
    const onAnswer = vi.fn();
    render(
      <AgentDialogue
        pendingQuestion="On casse l'API ?"
        enCours
        onAnswer={onAnswer}
        onInterject={() => {}}
      />,
    );

    const champ = screen.getByLabelText(/Votre réponse/i);
    await userEvent.type(champ, "non, on ajoute un champ");
    await userEvent.click(screen.getByRole("button", { name: /Répondre/i }));

    expect(onAnswer).toHaveBeenCalledWith("non, on ajoute un champ");
    expect(champ).toHaveValue("");
  });

  it("refuse d'envoyer une reponse vide", async () => {
    const onAnswer = vi.fn();
    render(
      <AgentDialogue
        pendingQuestion="On casse l'API ?"
        enCours
        onAnswer={onAnswer}
        onInterject={() => {}}
      />,
    );

    await userEvent.click(screen.getByRole("button", { name: /Répondre/i }));

    expect(onAnswer).not.toHaveBeenCalled();
  });

  it("permet d'intervenir meme sans question en cours", async () => {
    const onInterject = vi.fn();
    render(
      <AgentDialogue
        pendingQuestion={null}
        enCours
        onAnswer={() => {}}
        onInterject={onInterject}
      />,
    );

    await userEvent.type(screen.getByLabelText(/Consigne/i), "pense aux tests");
    await userEvent.click(screen.getByRole("button", { name: /Envoyer/i }));

    expect(onInterject).toHaveBeenCalledWith("pense aux tests");
  });

  it("disparait quand aucun run ne tourne", () => {
    // Hors run, il n'y a personne a qui parler : un champ de saisie laisserait
    // croire le contraire.
    const { container } = render(
      <AgentDialogue
        pendingQuestion={null}
        enCours={false}
        onAnswer={() => {}}
        onInterject={() => {}}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});
