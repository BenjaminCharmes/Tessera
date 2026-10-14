import type { LigneDiff } from "./diff";

/** Le diff de confirmation d'un prompt : lignes retirées, ajoutées, inchangées (ticket-226). */
export default function PromptDiff({ lignes }: { lignes: LigneDiff[] }) {
  return (
    <div className="min-h-0 flex-1 overflow-auto rounded-sm border border-zinc-700 bg-zinc-950 font-mono text-micro leading-relaxed">
      {lignes.map((l, i) => (
        <div
          key={i}
          className={`whitespace-pre-wrap break-all px-4 ${
            l.type === "ajout"
              ? "bg-green-950/40 text-green-300"
              : l.type === "retrait"
                ? "bg-red-950/40 text-red-300"
                : "text-zinc-400"
          }`}
        >
          {l.type === "ajout"
            ? `+${l.texte}`
            : l.type === "retrait"
              ? `-${l.texte}`
              : ` ${l.texte}`}
        </div>
      ))}
    </div>
  );
}
