import { IconAlert, IconCheck } from "../../design/icons";

interface VerdictBannerProps {
  content: string;
}

function parseVerdict(content: string): { approved: boolean; summary: string } {
  const approved =
    content.includes("APPROVED") && !content.includes("CHANGES_REQUESTED");
  const lines = content
    .split("\n")
    .map((l) => l.trim())
    .filter(
      (l) => l && !l.includes("APPROVED") && !l.includes("CHANGES_REQUESTED"),
    );
  return { approved, summary: lines[0] ?? "" };
}

export default function VerdictBanner({ content }: VerdictBannerProps) {
  const { approved, summary } = parseVerdict(content);

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
      {summary && <div className="text-zinc-400 text-mini">{summary}</div>}
    </div>
  );
}
