import { useRef, useState } from "react";
import { api } from "../../lib/api";
import type { ConversationMessage } from "../../types/api";

interface AgentCreatorModalProps {
  onClose: () => void;
  onCreated: (role: string) => void;
  initialInput?: string;
}

export default function AgentCreatorModal({
  onClose,
  onCreated,
  initialInput = "",
}: AgentCreatorModalProps) {
  const [conversation, setConversation] = useState<ConversationMessage[]>([]);
  const [input, setInput] = useState(initialInput);
  const [loading, setLoading] = useState(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = input.trim();
    if (!trimmed) return;

    const userMsg: ConversationMessage = { role: "user", content: trimmed };
    const newConversation = [...conversation, userMsg];
    setConversation(newConversation);
    setInput("");
    setLoading(true);
    setApiError(null);

    try {
      const result = await api.agents.createConversational(newConversation);
      if (result.created && result.agent) {
        onCreated(result.agent.role);
      } else {
        setConversation([
          ...newConversation,
          { role: "assistant", content: result.message },
        ]);
        setTimeout(() => textareaRef.current?.focus(), 0);
      }
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Erreur inconnue");
      setConversation(conversation);
    } finally {
      setLoading(false);
    }
  }

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }

  const hasMessages = conversation.length > 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleOverlayClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-label="Créer un agent"
    >
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 w-full max-w-lg shadow-xl flex flex-col gap-4">
        <h2 className="text-zinc-100 text-base font-semibold">Nouvel agent</h2>

        {hasMessages && (
          <div className="flex flex-col gap-3 max-h-64 overflow-y-auto">
            {conversation.map((msg, i) => (
              <div
                key={i}
                className={`text-xs rounded px-3 py-2 ${
                  msg.role === "user"
                    ? "bg-zinc-800 text-zinc-200 self-end ml-8"
                    : "bg-zinc-700 text-zinc-100 self-start mr-8"
                }`}
              >
                {msg.content}
              </div>
            ))}
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <label
            htmlFor="agent-description"
            className="block text-xs text-zinc-400 mb-1"
          >
            {hasMessages
              ? "Votre réponse"
              : "Décrivez l'agent que vous souhaitez créer"}
          </label>
          <textarea
            id="agent-description"
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              hasMessages
                ? "Répondez à la question…"
                : "Ex : Un agent qui relit le code et vérifie la sécurité…"
            }
            rows={3}
            className="w-full bg-zinc-800 border border-zinc-600 rounded px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none focus:border-zinc-400 resize-none"
            disabled={loading}
            autoFocus={!hasMessages}
          />

          {apiError && (
            <p className="mt-2 text-xs text-red-400" role="alert">
              {apiError}
            </p>
          )}

          <div className="flex gap-3 justify-end mt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {loading && (
                <span className="inline-block w-3 h-3 border-2 border-zinc-400 border-t-white rounded-full animate-spin" />
              )}
              {hasMessages ? "Envoyer" : "Créer"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
