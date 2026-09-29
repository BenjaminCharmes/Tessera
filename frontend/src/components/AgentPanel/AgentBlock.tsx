import { useState } from "react";
import { IconCheck, IconChevronDown, IconChevronRight } from "../../design/icons";
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
  /** Contenu complet de agent_done pour le codeur, rejoué après reconnexion. */
  doneContent?: string;
}

/**
 * Le compte rendu complet du codeur, replié par défaut (ticket-216).
 *
 * Les tokens live disparaissent à la reconnexion (ADR-041) ; agent_done porte
 * le même texte et survit. On l'affiche ici quand les tokens sont absents ou
 * tronqués.
 */
function CompteRenduCodeur({ content }: { content: string }) {
  const [ouvert, setOuvert] = useState(false);

  return (
    <div className="text-xs text-zinc-400">
      <button
        type="button"
        onClick={() => setOuvert((v) => !v)}
        aria-expanded={ouvert}
        className="flex items-center gap-1 text-mini transition-colors hover:text-zinc-200"
      >
        {ouvert ? <IconChevronDown size={12} /> : <IconChevronRight size={12} />}
        {ouvert ? "Masquer le compte rendu" : "Voir le compte rendu"}
      </button>
      {ouvert && (
        <pre className="mt-1.5 max-h-64 overflow-auto whitespace-pre-wrap wrap-break-word rounded-sm bg-zinc-950/60 p-2 font-mono text-mini text-zinc-300">
          {content}
        </pre>
      )}
    </div>
  );
}

export default function AgentBlock({
  agent,
  tokens,
  isActive,
  isDone,
  reviewContent,
  doneContent,
}: AgentBlockProps) {
  // Préférer doneContent quand le codeur a terminé et que les tokens live sont
  // absents ou plus courts — c'est le cas après une reconnexion (ADR-041).
  const useDoneContent =
    agent === "codeur" &&
    isDone &&
    !!doneContent &&
    tokens.length < doneContent.length;

  return (
    <div className="mx-3 mb-3 rounded-sm border border-zinc-700 overflow-hidden">
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
          <span className="ml-auto flex items-center gap-1 font-normal text-green-400">
            <IconCheck size={12} /> terminé
          </span>
        )}
      </div>

      <div className="p-3">
        {agent === "codeur" && !useDoneContent && tokens && (
          <TokenStream tokens={tokens} isActive={isActive} />
        )}
        {useDoneContent && <CompteRenduCodeur content={doneContent} />}
        {agent === "reviewer" && reviewContent && (
          <VerdictBanner content={reviewContent} />
        )}
        {isActive && !tokens && !reviewContent && !useDoneContent && (
          <div className="text-zinc-600 text-xs italic">Génération…</div>
        )}
      </div>
    </div>
  );
}
