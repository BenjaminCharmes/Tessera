import { IconChevronDown, IconChevronRight } from "../../design/icons";
import { useState } from "react";
import type { ChatToolUse } from "../../types/api";

interface ToolUseListProps {
  toolUses: ChatToolUse[];
}

/**
 * Les appels d'outil du tour en cours, repliés par défaut.
 *
 * Dépliés, ils noieraient la réponse ; masqués, on ne saurait pas que l'agent
 * a touché au projet.
 */
export default function ToolUseList({ toolUses }: ToolUseListProps) {
  const [open, setOpen] = useState(false);

  return (
    <div className="rounded border border-zinc-800 bg-zinc-950/50">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        className="flex w-full items-center gap-1.5 px-2 py-1 text-left text-mini text-zinc-500 hover:text-zinc-300"
      >
        {open ? <IconChevronDown size={12} /> : <IconChevronRight size={12} />}
        {toolUses.length} appel{toolUses.length > 1 ? "s" : ""} d'outil
      </button>

      {open && (
        <ul className="space-y-1 px-2 pb-1.5">
          {toolUses.map((use, i) => (
            <li key={i} className="font-mono text-mini text-zinc-400">
              <span className="text-zinc-300">{use.tool}</span>
              <span className="text-zinc-600">
                {" "}
                {JSON.stringify(use.input).slice(0, 120)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
