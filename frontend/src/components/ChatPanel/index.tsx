import { BAND } from "../../design/layout";
import { useEffect, useRef, useState } from "react";
import type { Project } from "../../types/api";
import { useChat } from "../../hooks/useChat";
import ChatMessageView from "./ChatMessageView";
import ToolUseList from "./ToolUseList";
import { IconCross, IconSend } from "../../design/icons";

interface ChatPanelProps {
  project: Project | null;
  /** La liste des conversations vit dans la colonne 2 (ticket-250). */
  conversationId: string;
}

/**
 * Conversation libre avec l'agent du projet (ticket-048).
 *
 * Coexiste avec l'Agent Stream sans le remplacer : l'un observe un run de
 * pipeline, l'autre discute. Les écritures de l'agent sont commitées sur une
 * branche `chat-…` (ADR-019), jamais sur la branche courante.
 */
export default function ChatPanel({ project, conversationId }: ChatPanelProps) {
  const chat = useChat(project?.id ?? null, conversationId);
  const [draft, setDraft] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ block: "end" });
  }, [chat.messages.length, chat.streaming]);

  if (!project) {
    return (
      <div className="h-full flex items-center justify-center p-6 text-center text-sm text-zinc-500">
        Sélectionne un projet pour discuter avec son agent.
      </div>
    );
  }

  const thinking = chat.status === "thinking";
  const disconnected = chat.status === "disconnected";
  // Une socket fermée proprement n'empêche pas d'écrire : c'est l'envoi qui
  // la rouvre (ticket-123).
  const canSend =
    (chat.status === "ready" || disconnected) && draft.trim().length > 0;

  function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSend) return;
    chat.send(draft);
    setDraft("");
  }

  const budgetRatio = chat.maxUsd > 0 ? chat.spentUsd / chat.maxUsd : 0;

  return (
    <div className="h-full flex flex-col overflow-hidden bg-zinc-900">
      <header className={`${BAND} justify-between gap-2 border-b border-zinc-800 px-3`}>
        <span className="text-xs font-medium text-zinc-300">
          Chat — {project.id}
        </span>
        {chat.maxUsd > 0 && (
          <span
            className={`text-mini tabular-nums ${
              budgetRatio >= 0.9 ? "text-amber-400" : "text-zinc-500"
            }`}
            title="Coût cumulé de cette conversation"
          >
            {chat.spentUsd.toFixed(3)} / {chat.maxUsd.toFixed(2)} $
          </span>
        )}
      </header>

      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        {chat.messages.length === 0 && !thinking && (
          <p className="text-sm text-zinc-500">
            Pose une question sur le projet, ou demande une modification.
            L'agent lit et écrit les fichiers ; son travail est commité sur une
            branche <code className="text-zinc-400">chat-…</code>.
          </p>
        )}

        {chat.messages.map((message, i) => (
          <ChatMessageView key={`${message.ts}-${i}`} message={message} />
        ))}

        {chat.toolUses.length > 0 && <ToolUseList toolUses={chat.toolUses} />}

        {thinking && (
          <div className="text-sm text-zinc-300 whitespace-pre-wrap">
            {chat.streaming || (
              <span className="text-zinc-500">L'agent réfléchit…</span>
            )}
          </div>
        )}

        {chat.lastBranch && (
          <p className="text-mini text-green-400">
            Travail commité sur <code>{chat.lastBranch}</code>
          </p>
        )}

        {chat.suggestedTicketId && !chat.runningTicketId && (
          <div className="rounded-sm border border-zinc-700 bg-zinc-800/60 p-2">
            <p className="mb-1.5 text-mini text-zinc-400">
              L'agent propose de lancer le pipeline sur{" "}
              <code className="text-zinc-200">{chat.suggestedTicketId}</code>.
            </p>
            <button
              type="button"
              onClick={chat.runSuggested}
              className="rounded-sm bg-green-800 px-2.5 py-1 text-xs text-green-50 hover:bg-green-700"
            >
              Lancer le pipeline
            </button>
          </div>
        )}

        {chat.runningTicketId && (
          <p className="text-mini text-zinc-400">
            Pipeline en cours sur <code>{chat.runningTicketId}</code>…
          </p>
        )}

        {chat.lastRun && (
          <p
            className={`text-mini ${
              chat.lastRun.approved ? "text-green-400" : "text-amber-400"
            }`}
          >
            {chat.lastRun.ticket_id} —{" "}
            {chat.lastRun.approved ? "approuvé" : "non approuvé"} après{" "}
            {chat.lastRun.rounds} tour(s)
            {chat.lastRun.branch ? ` sur ${chat.lastRun.branch}` : ""}
          </p>
        )}

        <div ref={endRef} />
      </div>

      {chat.errorMessage && (
        <div className="px-3 py-2 border-t border-amber-900/50 bg-amber-950/40 text-xs text-amber-300 flex items-start justify-between gap-2">
          <span>{chat.errorMessage}</span>
          <button
            type="button"
            onClick={chat.clearError}
            className="text-amber-500 hover:text-amber-300"
            aria-label="Masquer l'erreur"
          >
            <IconCross size={12} />
          </button>
        </div>
      )}

      {disconnected && (
        <p className="border-t border-amber-900/50 bg-amber-950/40 px-3 py-2 text-xs text-amber-300">
          Connexion au chat fermée. Le prochain envoi la rouvre.
        </p>
      )}

      <form onSubmit={submit} className="border-t border-zinc-800 p-2">
        <label htmlFor="chat-input" className="sr-only">
          Message
        </label>
        <div className="flex items-end gap-2">
          <textarea
            id="chat-input"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) submit(e);
            }}
            rows={2}
            placeholder={
              chat.status === "connecting"
                ? "Connexion…"
                : "Écris ton message (Entrée pour envoyer)"
            }
            disabled={chat.status === "connecting"}
            className="flex-1 resize-none rounded-sm bg-zinc-800 px-2 py-1.5 text-sm text-zinc-200 placeholder-zinc-600 outline-hidden focus:ring-1 focus:ring-zinc-600 disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={!canSend}
            title="Envoyer (Entrée)"
            className="flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-sm bg-violet-700 text-white hover:bg-violet-600 disabled:opacity-40 disabled:hover:bg-violet-700"
          >
            <IconSend size={16} />
            <span className="sr-only">
              {thinking ? "Envoi en cours" : "Envoyer"}
            </span>
          </button>
        </div>
      </form>
    </div>
  );
}
