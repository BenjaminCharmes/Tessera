import type {
  AgentDetail,
  AgentInfo,
  ChatHistory,
  ConversationMessage,
  ConversationSummary,
  CreateAgentResponse,
  RunFromChatResponse,
} from "../types/api";
import { del, post, put } from "./apiVerbes";
import { request } from "./http";

export const chat = {
  list: (projectId: string): Promise<ConversationSummary[]> =>
    request(`/projects/${projectId}/chat`),
  history: (
    projectId: string,
    conversationId: string,
  ): Promise<ChatHistory> =>
    request(`/projects/${projectId}/chat/${conversationId}`),
  runPipeline: (
    projectId: string,
    conversationId: string,
    ticketId: string,
  ): Promise<RunFromChatResponse> =>
    post(`/projects/${projectId}/chat/run`, {
      conversation_id: conversationId,
      ticket_id: ticketId,
    }),
};

export const agents = {
  list: (): Promise<AgentInfo[]> =>
    request<{ agents: AgentInfo[] }>("/agents/registry").then(
      (r) => r.agents,
    ),
  detail: (role: string): Promise<AgentDetail> =>
    request(`/agents/registry/${role}`),
  updatePrompt: (role: string, systemPrompt: string): Promise<AgentDetail> =>
    put(`/agents/registry/${role}`, { system_prompt: systemPrompt }),
  remove: (role: string): Promise<void> => del(`/agents/registry/${role}`),
  createConversational: (
    conversation: ConversationMessage[],
  ): Promise<CreateAgentResponse> =>
    post("/agents/create-agent", { conversation }),
};
