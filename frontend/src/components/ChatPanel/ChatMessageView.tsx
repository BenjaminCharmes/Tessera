import type { ChatMessage } from "../../types/api";

interface ChatMessageViewProps {
  message: ChatMessage;
}

/** Un tour de conversation. L'utilisateur à droite, l'agent à gauche. */
export default function ChatMessageView({ message }: ChatMessageViewProps) {
  const isUser = message.role === "user";

  return (
    <div className={isUser ? "flex justify-end" : ""}>
      <div
        className={
          isUser
            ? "max-w-[85%] rounded bg-zinc-700 px-2.5 py-1.5 text-sm text-zinc-100 whitespace-pre-wrap"
            : "text-sm text-zinc-300 whitespace-pre-wrap"
        }
      >
        {!isUser && (
          <span className="mb-0.5 block text-mini font-medium uppercase tracking-wide text-zinc-500">
            Agent
          </span>
        )}
        {message.content}
      </div>
    </div>
  );
}
