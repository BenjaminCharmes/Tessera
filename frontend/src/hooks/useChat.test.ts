import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { MockWebSocket } from "../test/mockWebSocket";
import { useChat } from "./useChat";
import { api } from "../lib/api";

vi.stubGlobal("WebSocket", MockWebSocket);

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

describe("useChat", () => {
  it("reste inerte sans projet sélectionné", () => {
    const { result } = renderHook(() => useChat(null));
    expect(result.current.status).toBe("idle");
    expect(result.current.messages).toHaveLength(0);
  });

  it("charge l'historique au montage — la conversation survit au rechargement", async () => {
    vi.spyOn(api.chat, "history").mockResolvedValue({
      project_id: "ide-core",
      conversation_id: "default",
      messages: [
        { role: "user", content: "Salut", cost_usd: 0, ts: "t1" },
        { role: "assistant", content: "Bonjour", cost_usd: 0.04, ts: "t2" },
      ],
      spent_usd: 0.04,
      max_usd: 2,
    });

    const { result } = renderHook(() => useChat("ide-core"));

    await waitFor(() => expect(result.current.messages).toHaveLength(2));
    expect(result.current.spentUsd).toBe(0.04);
    expect(result.current.maxUsd).toBe(2);
  });

  it("affiche le message de l'utilisateur immédiatement", async () => {
    const { result } = renderHook(() => useChat("ide-core"));
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    act(() => result.current.send("Explique le pipeline"));

    expect(result.current.messages.at(-1)).toMatchObject({
      role: "user",
      content: "Explique le pipeline",
    });
    expect(result.current.status).toBe("thinking");
    expect(MockWebSocket.instance!.sent).toHaveLength(1);
  });

  it("accumule les tokens streamés puis verse la réponse dans le fil", async () => {
    const { result } = renderHook(() => useChat("ide-core"));
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());
    act(() => result.current.send("Question"));

    act(() => {
      MockWebSocket.instance!.triggerMessage({ type: "token", token: "Une " });
      MockWebSocket.instance!.triggerMessage({ type: "token", token: "réponse" });
    });
    expect(result.current.streaming).toBe("Une réponse");

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "done",
        content: "Une réponse",
        cost_usd: 0.02,
        spent_usd: 0.02,
        max_usd: 2,
        branch: "chat-20260915-120000",
      });
    });

    expect(result.current.streaming).toBe("");
    expect(result.current.messages.at(-1)).toMatchObject({
      role: "assistant",
      content: "Une réponse",
    });
    expect(result.current.spentUsd).toBe(0.02);
    expect(result.current.lastBranch).toBe("chat-20260915-120000");
    expect(result.current.status).toBe("ready");
  });

  it("collecte les appels d'outil du tour", async () => {
    const { result } = renderHook(() => useChat("ide-core"));
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "tool_use",
        tool: "Read",
        input: { path: "src/main.py" },
      });
    });

    expect(result.current.toolUses).toEqual([
      { tool: "Read", input: { path: "src/main.py" } },
    ]);
  });

  it("remonte le dépassement de plafond sans casser la conversation", async () => {
    // LLM_MAX_BUDGET_USD borne un appel, pas une conversation : le plafond
    // doit être visible, pas silencieux.
    const { result } = renderHook(() => useChat("ide-core"));
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());
    act(() => MockWebSocket.instance!.triggerOpen());

    act(() => {
      MockWebSocket.instance!.triggerMessage({
        type: "budget_exceeded",
        detail: "Plafond atteint : 2.00 USD",
      });
    });

    expect(result.current.errorMessage).toContain("Plafond atteint");
    expect(result.current.status).toBe("ready");
  });

  it("n'envoie rien si la socket n'est pas ouverte", async () => {
    const { result } = renderHook(() => useChat("ide-core"));
    await waitFor(() => expect(MockWebSocket.instance).not.toBeNull());

    act(() => result.current.send("Perdu"));

    expect(MockWebSocket.instance!.sent).toHaveLength(0);
  });
});
