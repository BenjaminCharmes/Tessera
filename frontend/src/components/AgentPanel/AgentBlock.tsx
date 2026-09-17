import TokenStream from "./TokenStream";
import VerdictBanner from "./VerdictBanner";
import type { AgentRole } from "../../types/api";

// Le nom du rôle suffit. La carte précédente n'associait une émoji qu'à trois
// rôles sur treize : les dix autres s'affichaient sans, et l'en-tête du panneau
// changeait de forme selon l'agent qui parlait (ticket-067).

interface AgentBlockProps {
  agent: AgentRole;
  tokens: string;
  isActive: boolean;
  isDone: boolean;
  reviewContent?: string;
}

export default function AgentBlock({
  agent,
  tokens,
  isActive,
  isDone,
  reviewContent,
}: AgentBlockProps) {
  return (
    <div className="mx-3 mb-3 rounded border border-zinc-700 overflow-hidden">
      <div className="flex items-center gap-2 px-3 py-2 bg-zinc-800 text-xs font-semibold text-zinc-300">
        <span>{agent.toUpperCase()}</span>
        {isActive && (
          <span className="ml-auto flex gap-0.5">
            {[0, 150, 300].map((delay) => (
              <span
                key={delay}
                className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce"
                style={{ animationDelay: `${delay}ms` }}
              />
            ))}
          </span>
        )}
        {isDone && !isActive && (
          <span className="ml-auto text-zinc-600 font-normal">done</span>
        )}
      </div>

      <div className="p-3">
        {agent === "codeur" && tokens && (
          <TokenStream tokens={tokens} isActive={isActive} />
        )}
        {agent === "reviewer" && reviewContent && (
          <VerdictBanner content={reviewContent} />
        )}
        {isActive && !tokens && !reviewContent && (
          <div className="text-zinc-600 text-xs italic">Generating…</div>
        )}
      </div>
    </div>
  );
}
