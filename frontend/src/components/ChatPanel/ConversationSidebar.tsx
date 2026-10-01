import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { ConversationSummary } from "../../types/api";

interface Props {
  projectId: string;
  activeId: string;
  onSelect: (id: string) => void;
  onNew: () => void;
}

/**
 * Conversation list for a project — ticket-225.
 *
 * Reloads the list whenever the project or the active conversation changes,
 * so a freshly created conversation appears after the first message is sent.
 * Lives in the sidebar column (ticket-250): the chat panel used to open its
 * own mini-column in the center while column 2 sat empty.
 */
export default function ConversationSidebar({
  projectId,
  activeId,
  onSelect,
  onNew,
}: Props) {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);

  useEffect(() => {
    let cancelled = false;
    api.chat
      .list(projectId)
      .then((list) => {
        if (!cancelled) setConversations(list);
      })
      .catch(() => {
        // Non-critical: the sidebar stays empty if the request fails.
      });
    return () => {
      cancelled = true;
    };
  }, [projectId, activeId]);

  return (
    <div className="flex h-full flex-col overflow-y-auto">
      <button
        type="button"
        onClick={onNew}
        className="m-2 rounded-sm bg-zinc-700 px-2 py-1 text-xs text-zinc-100 hover:bg-zinc-600"
      >
        Nouvelle conversation
      </button>
      <ul className="flex-1">
        {conversations.map((conv) => (
          <li key={conv.conversation_id}>
            <button
              type="button"
              onClick={() => onSelect(conv.conversation_id)}
              className={`w-full text-left truncate rounded-sm px-2 py-1.5 text-xs ${
                conv.conversation_id === activeId
                  ? "bg-violet-900/50 text-zinc-100"
                  : "text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200"
              }`}
            >
              {conv.title || conv.conversation_id}
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
