import { afterEach, describe, expect, it, vi } from "vitest";
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
        onStop={() => {}}
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
        onStop={() => {}}
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
        onStop={() => {}}
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
        onStop={() => {}}
      />,
    );

    await userEvent.type(screen.getByLabelText(/Consigne/i), "pense aux tests");
    await userEvent.click(screen.getByRole("button", { name: /Envoyer/i }));

    expect(onInterject).toHaveBeenCalledWith("pense aux tests");
  });

  it("affiche l'accusé 'déposée pour le tour suivant' après une réponse tardive", () => {
    render(
      <AgentDialogue
        pendingQuestion={null}
        enCours
        answerAck="deposited"
        onAnswer={() => {}}
        onInterject={() => {}}
        onStop={() => {}}
      />,
    );

    expect(
      screen.getByTestId("answer-ack-deposited"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/déposée pour le tour suivant/i),
    ).toBeInTheDocument();
  });

  it("n'affiche pas l'accusé pour une réponse transmise", () => {
    render(
      <AgentDialogue
        pendingQuestion="On casse l'API ?"
        enCours
        answerAck="transmitted"
        onAnswer={() => {}}
        onInterject={() => {}}
        onStop={() => {}}
      />,
    );

    expect(screen.queryByTestId("answer-ack-deposited")).toBeNull();
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
        onStop={() => {}}
      />,
    );

    expect(container).toBeEmptyDOMElement();
  });
});

describe("AgentDialogue — question expirée (ticket-320)", () => {
  afterEach(() => {
    vi.useRealTimers();
  });

  it("affiche la question expirée comme expirée, pas en attente", () => {
    vi.useFakeTimers();
    vi.setSystemTime(Date.parse("2026-10-02T14:00:00Z"));

    render(
      <AgentDialogue
        pendingQuestion="On casse l'API ?"
        questionExpireA="2026-10-02T13:14:58Z"
        enCours
        onAnswer={() => {}}
        onInterject={() => {}}
        onStop={() => {}}
      />,
    );

    expect(screen.getByTestId("question-expiree")).toBeInTheDocument();
    expect(screen.queryByText(/L'agent attend votre réponse/i)).toBeNull();
  });

  it("affiche la question non expirée normalement", () => {
    vi.useFakeTimers();
    vi.setSystemTime(Date.parse("2026-10-02T13:10:00Z"));

    render(
      <AgentDialogue
        pendingQuestion="On casse l'API ?"
        questionExpireA="2026-10-02T13:14:58Z"
        enCours
        onAnswer={() => {}}
        onInterject={() => {}}
        onStop={() => {}}
      />,
    );

    expect(screen.getByText(/L'agent attend votre réponse/i)).toBeInTheDocument();
    expect(screen.queryByTestId("question-expiree")).toBeNull();
  });
});
