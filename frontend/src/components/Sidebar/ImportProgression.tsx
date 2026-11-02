import type { SourceType } from "./importValidation";

export type EtapeEnCours = "importing" | "analyzing";

interface ImportProgressionProps {
  step: EtapeEnCours;
  sourceType: SourceType;
}

function ProgressBar({ step }: { step: EtapeEnCours }) {
  const pct = step === "importing" ? 35 : 70;
  const label =
    step === "importing" ? "Import du projet…" : "Analyse de la stack…";
  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs text-zinc-400">{label}</p>
      <div className="w-full bg-zinc-700 rounded-full h-1.5">
        <div
          className="bg-zinc-300 h-1.5 rounded-full transition-all duration-700"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

/** Loading step: title and progress bar while the project is imported. */
export default function ImportProgression({
  step,
  sourceType,
}: ImportProgressionProps) {
  return (
    <>
      <h2 className="text-zinc-100 text-base font-semibold">
        {sourceType === "github"
          ? "Clone et analyse du repo…"
          : "Import et analyse du projet…"}
      </h2>
      <ProgressBar step={step} />
    </>
  );
}
