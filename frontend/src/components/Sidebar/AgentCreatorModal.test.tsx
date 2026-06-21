import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AgentCreatorModal from "./AgentCreatorModal";
import { api } from "../../lib/api";

vi.mock("../../lib/api", () => ({
  api: {
    agents: {
      createConversational: vi.fn(),
    },
  },
}));

const mockCreate = vi.mocked(api.agents.createConversational);

describe("AgentCreatorModal", () => {
  const onClose = vi.fn();
  const onCreated = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders textarea and action buttons", () => {
    render(<AgentCreatorModal onClose={onClose} onCreated={onCreated} />);
    expect(screen.getByLabelText(/décrivez/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /créer/i })).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /annuler/i }),
    ).toBeInTheDocument();
  });

  it("calls onCreated with role when created: true", async () => {
    mockCreate.mockResolvedValue({
      created: true,
      message: "",
      agent: { role: "securite", description: null },
    });

    render(<AgentCreatorModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(
      screen.getByLabelText(/décrivez/i),
      "Un agent de sécurité",
    );
    await userEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() => {
      expect(onCreated).toHaveBeenCalledWith("securite");
    });
  });

  it("shows AI clarification message and follow-up input when created: false", async () => {
    mockCreate.mockResolvedValue({
      created: false,
      message: "Quel langage cible ?",
      agent: null,
    });

    render(<AgentCreatorModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(
      screen.getByLabelText(/décrivez/i),
      "Un agent de sécurité",
    );
    await userEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() => {
      expect(screen.getByText("Quel langage cible ?")).toBeInTheDocument();
    });
    expect(screen.getByLabelText(/votre réponse/i)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /envoyer/i }),
    ).toBeInTheDocument();
  });

  it("sends full conversation history on follow-up", async () => {
    mockCreate
      .mockResolvedValueOnce({
        created: false,
        message: "Quel langage cible ?",
        agent: null,
      })
      .mockResolvedValueOnce({
        created: true,
        message: "",
        agent: { role: "securite-ts", description: null },
      });

    render(<AgentCreatorModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(
      screen.getByLabelText(/décrivez/i),
      "Un agent de sécurité",
    );
    await userEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() =>
      expect(screen.getByText("Quel langage cible ?")).toBeInTheDocument(),
    );

    await userEvent.type(screen.getByLabelText(/votre réponse/i), "TypeScript");
    await userEvent.click(screen.getByRole("button", { name: /envoyer/i }));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledTimes(2);
      const secondCall = mockCreate.mock.calls[1][0];
      expect(secondCall).toHaveLength(3);
      expect(secondCall[0]).toMatchObject({
        role: "user",
        content: "Un agent de sécurité",
      });
      expect(secondCall[1]).toMatchObject({
        role: "assistant",
        content: "Quel langage cible ?",
      });
      expect(secondCall[2]).toMatchObject({
        role: "user",
        content: "TypeScript",
      });
      expect(onCreated).toHaveBeenCalledWith("securite-ts");
    });
  });

  it("disables submit button while loading", async () => {
    let resolve!: (
      v: ReturnType<typeof mockCreate> extends Promise<infer T> ? T : never,
    ) => void;
    mockCreate.mockReturnValue(
      new Promise((r) => {
        resolve = r;
      }),
    );

    render(<AgentCreatorModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/décrivez/i), "test");
    await userEvent.click(screen.getByRole("button", { name: /créer/i }));

    // After submit the conversation has one user message → button becomes "Envoyer" and is disabled
    expect(screen.getByRole("button", { name: /envoyer/i })).toBeDisabled();

    resolve({ created: false, message: "clarification needed", agent: null });
    // Loading ends → AI message appears in conversation
    await waitFor(() =>
      expect(screen.getByText("clarification needed")).toBeInTheDocument(),
    );
  });

  it("shows API error on failure", async () => {
    mockCreate.mockRejectedValue(new Error("API 500: Internal error"));

    render(<AgentCreatorModal onClose={onClose} onCreated={onCreated} />);

    await userEvent.type(screen.getByLabelText(/décrivez/i), "test");
    await userEvent.click(screen.getByRole("button", { name: /créer/i }));

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "API 500: Internal error",
      );
    });
    expect(onCreated).not.toHaveBeenCalled();
  });

  it("calls onClose when Annuler is clicked", async () => {
    render(<AgentCreatorModal onClose={onClose} onCreated={onCreated} />);
    await userEvent.click(screen.getByRole("button", { name: /annuler/i }));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when clicking the overlay backdrop", async () => {
    render(<AgentCreatorModal onClose={onClose} onCreated={onCreated} />);
    await userEvent.click(screen.getByRole("dialog"));
    expect(onClose).toHaveBeenCalledTimes(1);
  });

  it("calls onClose when pressing Escape", async () => {
    render(<AgentCreatorModal onClose={onClose} onCreated={onCreated} />);
    await userEvent.keyboard("{Escape}");
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
