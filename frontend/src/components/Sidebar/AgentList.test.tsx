import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import AgentList from "./AgentList";
import * as apiModule from "../../lib/api";
import type { AgentInfo } from "../../types/api";

const AGENT_BUILTIN: AgentInfo = {
  role: "codeur",
  description: null,
  is_builtin: true,
  prompt_preview: "Tu es un codeur expert…",
};

const AGENT_CUSTOM: AgentInfo = {
  role: "securite",
  description: "Audit sécurité",
  is_builtin: false,
  prompt_preview: "Tu audites la sécurité…",
};

vi.mock("../../lib/api", () => ({
  api: {
    agents: {
      list: vi.fn(),
      remove: vi.fn(),
      createConversational: vi.fn(),
    },
  },
}));

vi.mock("../../hooks/useAgents", () => ({
  useAgents: vi.fn(),
}));

import { useAgents } from "../../hooks/useAgents";

const mockUseAgents = vi.mocked(useAgents);

describe("AgentList", () => {
  const onAgentCreated = vi.fn();
  const mockRefresh = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAgents.mockReturnValue({
      agents: [AGENT_BUILTIN, AGENT_CUSTOM],
      loading: false,
      error: null,
      refresh: mockRefresh,
    });
  });

  it("distingue d'un mot les agents livres et ceux qu'on a crees", () => {
    render(<AgentList onAgentCreated={onAgentCreated} />);
    expect(screen.getByText("codeur")).toBeInTheDocument();
    expect(screen.getByText("securite")).toBeInTheDocument();
    // Le badge dit la conséquence, pas l'origine : « qui a écrit le prompt »
    // n'apprend rien, puisque c'est toujours un agent (ticket-094).
    expect(screen.getByText("requis")).toBeInTheDocument();
    expect(screen.getByText("ajouté")).toBeInTheDocument();
  });

  it("shows delete button only for custom agents", () => {
    render(<AgentList onAgentCreated={onAgentCreated} />);
    const deleteBtn = screen.getByRole("button", {
      name: /supprimer securite/i,
    });
    expect(deleteBtn).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /supprimer codeur/i }),
    ).not.toBeInTheDocument();
  });

  it("supprime et rafraichit, une fois la confirmation donnee", async () => {
    vi.mocked(apiModule.api.agents.remove).mockResolvedValue(undefined);
    render(<AgentList onAgentCreated={onAgentCreated} />);

    await userEvent.click(
      screen.getByRole("button", { name: /supprimer securite/i }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Supprimer définitivement" }),
    );

    await waitFor(() => {
      expect(apiModule.api.agents.remove).toHaveBeenCalledWith("securite");
      expect(mockRefresh).toHaveBeenCalledTimes(1);
    });
  });

  it("shows error when delete fails", async () => {
    vi.mocked(apiModule.api.agents.remove).mockRejectedValue(
      new Error("Forbidden"),
    );
    render(<AgentList onAgentCreated={onAgentCreated} />);

    await userEvent.click(
      screen.getByRole("button", { name: /supprimer securite/i }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Supprimer définitivement" }),
    );

    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Forbidden");
    });
  });

  it("shows loading state", () => {
    mockUseAgents.mockReturnValue({
      agents: [],
      loading: true,
      error: null,
      refresh: mockRefresh,
    });
    render(<AgentList onAgentCreated={onAgentCreated} />);
    expect(screen.getByText(/chargement/i)).toBeInTheDocument();
  });

  it("shows empty state when no agents", () => {
    mockUseAgents.mockReturnValue({
      agents: [],
      loading: false,
      error: null,
      refresh: mockRefresh,
    });
    render(<AgentList onAgentCreated={onAgentCreated} />);
    expect(screen.getByText(/aucun agent/i)).toBeInTheDocument();
  });

  it("opens AgentCreatorModal when + Nouveau is clicked", async () => {
    render(<AgentList onAgentCreated={onAgentCreated} />);
    await userEvent.click(screen.getByRole("button", { name: /nouveau/i }));
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });
});

describe("AgentList — suppression", () => {
  const onAgentCreated = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAgents.mockReturnValue({
      agents: [AGENT_BUILTIN, AGENT_CUSTOM],
      loading: false,
      error: null,
      refresh: vi.fn(),
    });
  });

  it("demande confirmation avant de supprimer", async () => {
    // Panne vecue : un clic sur la croix supprimait le prompt sans rien
    // demander. L'agent disparaissait, et avec lui sa definition — la seule
    // chose qui determine son comportement (ticket-080).
    render(<AgentList onAgentCreated={onAgentCreated} />);

    await userEvent.click(
      screen.getByRole("button", { name: /supprimer securite/i }),
    );

    expect(apiModule.api.agents.remove).not.toHaveBeenCalled();
    expect(screen.getByRole("dialog")).toBeInTheDocument();
  });

  it("ne supprime qu'apres confirmation explicite", async () => {
    vi.mocked(apiModule.api.agents.remove).mockResolvedValue(undefined);
    render(<AgentList onAgentCreated={onAgentCreated} />);

    await userEvent.click(
      screen.getByRole("button", { name: /supprimer securite/i }),
    );
    await userEvent.click(
      screen.getByRole("button", { name: "Supprimer définitivement" }),
    );

    expect(apiModule.api.agents.remove).toHaveBeenCalledWith("securite");
  });

  it("renonce sans rien supprimer", async () => {
    render(<AgentList onAgentCreated={onAgentCreated} />);

    await userEvent.click(
      screen.getByRole("button", { name: /supprimer securite/i }),
    );
    await userEvent.click(screen.getByRole("button", { name: "Annuler" }));

    expect(apiModule.api.agents.remove).not.toHaveBeenCalled();
    expect(screen.queryByRole("dialog")).toBeNull();
  });
});
