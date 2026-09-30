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
  vi.spyOn(api.chat, "list").mockResolvedValue([]);
});

describe("ChatPanel", () => {
  it("invite à choisir un projet quand aucun n'est sélectionné", () => {
    render(<ChatPanel project={null} conversationId="default" />);
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

    render(<ChatPanel project={project} conversationId="default" />);

    await waitFor(() =>
      expect(screen.getByText(/0\.250 \/ 2\.00/)).toBeInTheDocument(),
    );
  });

  it("envoie le message saisi et l'affiche dans le fil", async () => {
    const user = userEvent.setup();
    render(<ChatPanel project={project} conversationId="default" />);

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

  it("dit que la connexion est fermée et laisse envoyer pour la rouvrir (ticket-123)", async () => {
    // Après une fermeture propre, le panneau exigeait `ready` : textarea
    // active, bouton grisé, et rien pour expliquer ni pour repartir.
    const user = userEvent.setup();
    render(<ChatPanel project={project} conversationId="default" />);

    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    const premiere = MockWebSocket.instance!;
    act(() => premiere.triggerOpen());
    act(() => premiere.triggerClose());

    expect(screen.getByText(/Connexion au chat fermée/)).toBeInTheDocument();

    await user.type(screen.getByLabelText("Message"), "Toujours là ?");
    const bouton = screen.getByRole("button", { name: "Envoyer" });
    expect(bouton).toBeEnabled();
    await user.click(bouton);

    expect(MockWebSocket.instance).not.toBe(premiere);
    expect(screen.getByText("Toujours là ?")).toBeInTheDocument();
  });

  it("le bouton 'Envoyer' est trouvable par son nom et soumet le message au clic", async () => {
    const user = userEvent.setup();
    render(<ChatPanel project={project} conversationId="default" />);

    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    await user.type(screen.getByLabelText("Message"), "Clic pour envoyer");
    const sendButton = screen.getByRole("button", { name: "Envoyer" });
    await waitFor(() => expect(sendButton).toBeEnabled());
    await user.click(sendButton);

    expect(screen.getByText("Clic pour envoyer")).toBeInTheDocument();
    expect(MockWebSocket.instance!.sent).toHaveLength(1);
  });

  it("soumet le message avec la touche Entrée", async () => {
    const user = userEvent.setup();
    render(<ChatPanel project={project} conversationId="default" />);

    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    const input = screen.getByLabelText("Message");
    await user.type(input, "Test Entrée");
    await user.keyboard("{Enter}");

    expect(screen.getByText("Test Entrée")).toBeInTheDocument();
    expect(MockWebSocket.instance!.sent).toHaveLength(1);
  });

  it("indique 'Envoi en cours' et désactive le bouton pendant la réflexion de l'agent", async () => {
    render(<ChatPanel project={project} conversationId="default" />);
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    act(() => MockWebSocket.instance!.triggerMessage({ type: "start" }));

    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Envoi en cours" }),
      ).toBeDisabled(),
    );
  });

  it("signale la branche sur laquelle le travail a été commité", async () => {
    render(<ChatPanel project={project} conversationId="default" />);
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
    render(<ChatPanel project={project} conversationId="default" />);
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
    render(<ChatPanel project={project} conversationId="default" />);
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

    render(<ChatPanel project={project} conversationId="default" />);
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

describe("ChatPanel — conversations (ticket-225, déplacées en colonne 2 par ticket-250)", () => {
  // La liste des conversations vit désormais dans la Sidebar
  // (SidebarChat.test.tsx) : le panneau ne fait que suivre la prop.
  it("charge l'historique de la conversation reçue en prop", async () => {
    const historySpy = vi.spyOn(api.chat, "history").mockResolvedValue({
      project_id: "ide-core",
      conversation_id: "conv-xyz",
      messages: [],
      spent_usd: 0,
      max_usd: 2,
    });

    render(<ChatPanel project={project} conversationId="conv-xyz" />);

    await waitFor(() =>
      expect(historySpy).toHaveBeenCalledWith("ide-core", "conv-xyz"),
    );
  });

  it("ne rend plus sa propre liste de conversations", async () => {
    vi.spyOn(api.chat, "list").mockResolvedValue([
      {
        conversation_id: "conv-abc",
        title: "Explique le pipeline",
        last_activity: "2026-09-29T10:00:00Z",
      },
    ]);

    render(<ChatPanel project={project} conversationId="default" />);

    expect(
      screen.queryByRole("button", { name: "Nouvelle conversation" }),
    ).not.toBeInTheDocument();
  });
});
