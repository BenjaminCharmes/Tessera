import { describe, it, expect, vi, beforeEach } from "vitest";
import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MockWebSocket } from "../../test/mockWebSocket";
import { api } from "../../lib/api";
import ChatPanel from "./index";
import type { Project } from "../../types/api";

vi.stubGlobal("WebSocket", MockWebSocket);

const project: Project = {
  id: "ide-core",
  name: "ide-core",
  path: "/w/ide-core",
  description: "",
  active_agents: [],
  stack: null,
  raw_claude_md: "",
  github_remote: null,
};

beforeEach(() => {
  MockWebSocket.instance = null;
  vi.restoreAllMocks();
  vi.spyOn(api.chat, "history").mockResolvedValue({
    project_id: "ide-core",
    conversation_id: "default",
    messages: [],
    spent_usd: 0,
    max_usd: 2,
  });
});

describe("ChatPanel", () => {
  it("invite à choisir un projet quand aucun n'est sélectionné", () => {
    render(<ChatPanel project={null} />);
    expect(screen.getByText(/Sélectionne un projet/)).toBeInTheDocument();
  });

  it("affiche le coût cumulé de la conversation", async () => {
    vi.spyOn(api.chat, "history").mockResolvedValue({
      project_id: "ide-core",
      conversation_id: "default",
      messages: [],
      spent_usd: 0.25,
      max_usd: 2,
    });

    render(<ChatPanel project={project} />);

    await waitFor(() =>
      expect(screen.getByText(/0\.250 \/ 2\.00/)).toBeInTheDocument(),
    );
  });

  it("envoie le message saisi et l'affiche dans le fil", async () => {
    const user = userEvent.setup();
    render(<ChatPanel project={project} />);

    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    const input = screen.getByLabelText("Message");
    await user.type(input, "Explique le pipeline");

    // Le bouton n'est actif qu'une fois la socket ouverte ET le brouillon
    // non vide : attendre cet état évite un clic sur un bouton désactivé.
    const sendButton = screen.getByRole("button", { name: "Envoyer" });
    await waitFor(() => expect(sendButton).toBeEnabled());
    await user.click(sendButton);

    expect(screen.getByText("Explique le pipeline")).toBeInTheDocument();
    expect(MockWebSocket.instance!.sent).toHaveLength(1);
  });

  it("signale la branche sur laquelle le travail a été commité", async () => {
    render(<ChatPanel project={project} />);
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    act(() =>
      MockWebSocket.instance!.triggerMessage({
        type: "done",
        content: "C'est fait.",
        cost_usd: 0.01,
        spent_usd: 0.01,
        max_usd: 2,
        branch: "chat-20260915-120000",
      }),
    );

    await waitFor(() =>
      expect(screen.getByText("chat-20260915-120000")).toBeInTheDocument(),
    );
  });
});

describe("ChatPanel — lancement de pipeline (ticket-055)", () => {
  it("propose un bouton quand l'agent suggère un lancement", async () => {
    render(<ChatPanel project={project} />);
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    act(() =>
      MockWebSocket.instance!.triggerMessage({
        type: "done",
        content: "Le ticket est prêt.",
        cost_usd: 0.01,
        spent_usd: 0.01,
        max_usd: 2,
        suggested_ticket_id: "ticket-042",
      }),
    );

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Lancer le pipeline" }),
      ).toBeInTheDocument(),
    );
    expect(screen.getByText("ticket-042")).toBeInTheDocument();
  });

  it("n'affiche aucun bouton sans suggestion", async () => {
    render(<ChatPanel project={project} />);
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    act(() =>
      MockWebSocket.instance!.triggerMessage({
        type: "done",
        content: "Voici l'explication.",
        cost_usd: 0.01,
        spent_usd: 0.01,
        max_usd: 2,
        suggested_ticket_id: null,
      }),
    );

    expect(
      screen.queryByRole("button", { name: "Lancer le pipeline" }),
    ).not.toBeInTheDocument();
  });

  it("lance le pipeline au clic et retire la suggestion", async () => {
    const user = userEvent.setup();
    const runPipeline = vi
      .spyOn(api.chat, "runPipeline")
      .mockResolvedValue({
        ticket_id: "ticket-042",
        approved: true,
        rounds: 1,
        final_status: "done",
        branch: "ticket-042-slug",
        commit_sha: "abc1234",
      });

    render(<ChatPanel project={project} />);
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());
    act(() =>
      MockWebSocket.instance!.triggerMessage({
        type: "done",
        content: "Prêt.",
        cost_usd: 0.01,
        spent_usd: 0.01,
        max_usd: 2,
        suggested_ticket_id: "ticket-042",
      }),
    );

    await user.click(
      await screen.findByRole("button", { name: "Lancer le pipeline" }),
    );

    expect(runPipeline).toHaveBeenCalledWith("ide-core", "default", "ticket-042");
    // La suggestion disparaît : la laisser inviterait à relancer un pipeline
    // déjà en cours.
    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: "Lancer le pipeline" }),
      ).not.toBeInTheDocument(),
    );
    await waitFor(() =>
      expect(screen.getByText(/approuvé après 1 tour/)).toBeInTheDocument(),
    );
  });
});
