import { useState } from "react";
import { IconCheck, IconSettings } from "../../design/icons";
import type { AnalysisResult, Project } from "../../types/api";

interface ImportRevueProps {
  project: Project;
  analysis: AnalysisResult;
  registeredAgents: Set<string>;
  onClose: () => void;
  onValidate: () => void;
}

function AgentLigne({ agent, present }: { agent: string; present: boolean }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-zinc-300">
        <span
          role="img"
          aria-label={present ? "agent enregistré" : "agent à créer"}
          className="inline-flex align-middle"
        >
          {present ? <IconCheck size={12} /> : <IconSettings size={12} />}
        </span>{" "}
        <span className="font-mono">{agent}</span>
      </span>
      {!present && (
        <span className="text-xs text-zinc-500 italic">
          sera créé automatiquement
        </span>
      )}
    </div>
  );
}

/** Review step: generated CLAUDE.md, detected stack and suggested agents. */
export default function ImportRevue({
  project,
  analysis,
  registeredAgents,
  onClose,
  onValidate,
}: ImportRevueProps) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(analysis.claude_md);

  return (
    <>
      <h2 className="flex items-center gap-1 text-zinc-100 text-base font-semibold">
        <IconCheck size={14} /> {project.name} importé
      </h2>

      <div>
        <div className="flex items-center justify-between mb-1">
          <span className="text-xs text-zinc-400">CLAUDE.md généré</span>
          <button
            onClick={() => setEditing((v) => !v)}
            className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
          >
            {editing ? "Aperçu" : "Modifier"}
          </button>
        </div>
        {editing ? (
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            rows={8}
            className="w-full bg-zinc-800 border border-zinc-700 rounded-sm px-3 py-2 text-xs text-zinc-200 font-mono focus:outline-hidden focus:border-zinc-500 resize-none"
          />
        ) : (
          <pre className="bg-zinc-800 border border-zinc-700 rounded-sm px-3 py-2 text-xs text-zinc-300 font-mono whitespace-pre-wrap max-h-40 overflow-y-auto">
            {draft}
          </pre>
        )}
      </div>

      <div>
        <p className="text-xs text-zinc-400 mb-2">
          Stack détectée :{" "}
          <span className="text-zinc-200">
            {analysis.detected_stack.join(", ")}
          </span>
        </p>
        <p className="text-xs text-zinc-400 mb-1">Agents suggérés</p>
        <div className="flex flex-col gap-1.5">
          {analysis.suggested_agents.map((agent) => (
            <AgentLigne
              key={agent}
              agent={agent}
              present={registeredAgents.has(agent)}
            />
          ))}
        </div>
      </div>

      <div className="flex gap-3 justify-end pt-1">
        <button
          onClick={onClose}
          className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
        >
          Annuler
        </button>
        <button
          onClick={onValidate}
          className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded-sm transition-colors"
        >
          Valider et ouvrir
        </button>
      </div>
    </>
  );
}
