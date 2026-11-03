// ---------------------------------------------------------------- chat ----
// ticket-048 — chat conversationnel avec outils.

export interface ConversationMessage {
  role: "user" | "assistant";
  content: string;
}

/** A conversation entry as returned by GET /{project_id}/chat — ticket-224. */
export interface ConversationSummary {
  conversation_id: string;
  title: string;
  last_activity: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  cost_usd: number;
  ts: string;
}

export interface ChatHistory {
  project_id: string;
  conversation_id: string;
  messages: ChatMessage[];
  spent_usd: number;
  max_usd: number;
}

/** Résultat d'un pipeline lancé depuis la conversation (ticket-055). */
export interface RunFromChatResponse {
  ticket_id: string;
  approved: boolean;
  rounds: number;
  final_status: string;
  branch: string | null;
  commit_sha: string | null;
}

/** Appel d'outil rendu dans le fil, replié par défaut. */
export interface ChatToolUse {
  tool: string;
  input: Record<string, unknown>;
}
