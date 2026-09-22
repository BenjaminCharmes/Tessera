import { useState } from "react";
import { IconAlert, IconCheck, IconChevronDown, IconChevronRight } from "../../design/icons";

interface VerdictBannerProps {
  content: string;
}

/**
 * Le bandeau ne gardait que `lines[0]` : le reviewer annonçait « voici ma
 * review » et l'utilisateur ne voyait rien de plus. Or le détail est la seule
 * chose qui permette de juger — c'est pour ça qu'on paie un reviewer
 * (ticket-072).
 */
function parseVerdict(content: string): {
  approved: boolean;
  summary: string;
  detail: string;
} {
  const approved =
    content.includes("APPROVED") && !content.includes("CHANGES_REQUESTED");
  const lines = content
    .split("\n")
    .map((l) => l.trim())
    .filter(
      (l) => l && !l.includes("APPROVED") && !l.includes("CHANGES_REQUESTED"),
    );
  return {
    approved,
    summary: lines[0] ?? "",
    detail: lines.slice(1).join("\n").trim(),
  };
}

export default function VerdictBanner({ content }: VerdictBannerProps) {
  const { approved, summary, detail } = parseVerdict(content);
  const [ouvert, setOuvert] = useState(false);

  return (
    <div
      className={`rounded p-3 text-xs ${
        approved
          ? "bg-green-900/40 border border-green-700/50 text-green-300"
          : "bg-amber-900/40 border border-amber-700/50 text-amber-300"
      }`}
    >
      <div className="font-semibold mb-1">
        {approved ? (
          <>
            <IconCheck size={14} /> APPROVED
          </>
        ) : (
          <>
            <IconAlert size={14} /> CHANGES_REQUESTED
          </>
        )}
      </div>
      {summary && <div className="text-mini text-zinc-400">{summary}</div>}

      {detail && (
        <>
          <button
            type="button"
            onClick={() => setOuvert((v) => !v)}
            aria-expanded={ouvert}
            className="mt-1.5 flex items-center gap-1 text-mini text-zinc-400 transition-colors hover:text-zinc-200"
          >
            {ouvert ? (
              <IconChevronDown size={12} />
            ) : (
              <IconChevronRight size={12} />
            )}
            {ouvert ? "Masquer le détail" : "Voir le détail de la revue"}
          </button>
          {ouvert && (
            <pre className="mt-1.5 max-h-64 overflow-auto whitespace-pre-wrap wrap-break-word rounded-sm bg-zinc-950/60 p-2 font-mono text-mini text-zinc-300">
              {detail}
            </pre>
          )}
        </>
      )}
    </div>
  );
}
