import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { MockWebSocket } from "../../test/mockWebSocket";
import { api } from "../../lib/api";
import ChatPanel from "./index";
import type { ChatHistory, Project } from "../../types/api";

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

function historique(sansOutils?: boolean): ChatHistory {
  return {
    project_id: "ide-core",
    conversation_id: "default",
    messages: [],
    spent_usd: 0.25,
    max_usd: 2,
    ...(sansOutils === undefined ? {} : { sans_outils: sansOutils }),
  };
}

beforeEach(() => {
  MockWebSocket.instance = null;
  vi.restoreAllMocks();
  vi.spyOn(api.chat, "list").mockResolvedValue([]);
});

describe("ChatPanel sans outils (ADR-094)", () => {
  it("affiche le bandeau quand l'API signale sans_outils", async () => {
    vi.spyOn(api.chat, "history").mockResolvedValue(historique(true));
    render(<ChatPanel project={project} conversationId="default" />);
    await waitFor(() =>
      expect(
        screen.getByText(/Sans accès aux fichiers sur ce projet/),
      ).toBeInTheDocument(),
    );
  });

  it("n'affiche pas le bandeau sinon", async () => {
    vi.spyOn(api.chat, "history").mockResolvedValue(historique(false));
    render(<ChatPanel project={project} conversationId="default" />);
    await waitFor(() =>
      expect(screen.getByText(/0\.250 \/ 2\.00/)).toBeInTheDocument(),
    );
    expect(
      screen.queryByText(/Sans accès aux fichiers sur ce projet/),
    ).not.toBeInTheDocument();
  });

  it("n'affiche pas le bandeau quand le champ est absent", async () => {
    vi.spyOn(api.chat, "history").mockResolvedValue(historique());
    render(<ChatPanel project={project} conversationId="default" />);
    await waitFor(() =>
      expect(screen.getByText(/0\.250 \/ 2\.00/)).toBeInTheDocument(),
    );
    expect(
      screen.queryByText(/Sans accès aux fichiers sur ce projet/),
    ).not.toBeInTheDocument();
  });
});
