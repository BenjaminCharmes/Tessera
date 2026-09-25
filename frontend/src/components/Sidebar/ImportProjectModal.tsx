import { IconCheck, IconSettings } from "../../design/icons";
import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import type { AnalysisResult, Project } from "../../types/api";

type SourceType = "local" | "github";
type ImportStep = "idle" | "importing" | "analyzing" | "review" | "error";

interface ImportProjectModalProps {
  onClose: () => void;
  onProjectCreated: (project: Project) => void;
}

function validateLocalPath(value: string): string | null {
  if (!value.trim()) return "Le chemin est requis";
  return null;
}

function validateGithubUrl(value: string): string | null {
  if (!value.trim()) return "L'URL est requise";
  const pattern = /^https:\/\/github\.com\/[a-zA-Z0-9_.-]+\/[a-zA-Z0-9_.-]+$/;
  if (!pattern.test(value.trim())) {
    return "Format invalide — ex : https://github.com/owner/mon-repo";
  }
  return null;
}

function ProgressBar({ step }: { step: "importing" | "analyzing" }) {
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

export default function ImportProjectModal({
  onClose,
  onProjectCreated,
}: ImportProjectModalProps) {
  const [sourceType, setSourceType] = useState<SourceType>("local");
  const [step, setStep] = useState<ImportStep>("idle");
  const [sourcePath, setSourcePath] = useState("");
  const [mode, setMode] = useState<"symlink" | "copy">("symlink");
  const [repoUrl, setRepoUrl] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [project, setProject] = useState<Project | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [editingClaudeMd, setEditingClaudeMd] = useState(false);
  const [claudeMdDraft, setClaudeMdDraft] = useState("");
  const [registeredAgents, setRegisteredAgents] = useState<Set<string>>(
    new Set(),
  );
  useEffect(() => {
    api.agents
      .list()
      .then((agents) => setRegisteredAgents(new Set(agents.map((a) => a.role))))
      .catch(() => {});
  }, []);

  async function handleImport(e: React.FormEvent) {
    e.preventDefault();

    const err =
      sourceType === "local"
        ? validateLocalPath(sourcePath)
        : validateGithubUrl(repoUrl);
    if (err) {
      setInputError(err);
      return;
    }
    setInputError(null);
    setApiError(null);

    try {
      setStep("importing");

      let imported: Project;
      if (sourceType === "local") {
        const res = await api.projects.import({
          source_path: sourcePath.trim(),
          mode,
        });
        imported = res.project;
        setProject(imported);

        setStep("analyzing");
        const result = await api.projects.analyze(imported.id, false);
        setAnalysis(result);
        setClaudeMdDraft(result.claude_md);
      } else {
        const res = await api.projects.clone({ repo_url: repoUrl.trim() });
        imported = res.project;
        setProject(imported);
        setAnalysis({
          claude_md: "",
          detected_stack: res.detected_stack,
          suggested_agents: [],
          claude_md_written: res.claude_md_generated,
        });
        setClaudeMdDraft("");
        setStep("analyzing");
        // Fetch the full CLAUDE.md for review
        const result = await api.projects.analyze(imported.id, false);
        setAnalysis(result);
        setClaudeMdDraft(result.claude_md);
      }

      setStep("review");
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Erreur inconnue");
      setStep("error");
    }
  }

  function handleValidate() {
    if (!project) return;
    onProjectCreated(project);
    onClose();
  }

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === e.currentTarget) onClose();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") onClose();
  }

  const isLoading = step === "importing" || step === "analyzing";

  return (
    <>
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
        onClick={handleOverlayClick}
        onKeyDown={handleKeyDown}
        role="dialog"
        aria-modal="true"
        aria-label="Importer un projet"
      >
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 w-full max-w-lg shadow-xl flex flex-col gap-4">
          {/* Step 1 — Input */}
          {(step === "idle" || step === "error") && (
            <>
              <h2 className="text-zinc-100 text-base font-semibold">
                Importer un projet existant
              </h2>

              {/* Source type toggle */}
              <div className="flex rounded-sm overflow-hidden border border-zinc-700">
                <button
                  type="button"
                  onClick={() => {
                    setSourceType("local");
                    setInputError(null);
                  }}
                  className={`flex-1 py-1.5 text-xs transition-colors ${
                    sourceType === "local"
                      ? "bg-zinc-700 text-zinc-100"
                      : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
                  }`}
                  aria-pressed={sourceType === "local"}
                >
                  Dossier local
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setSourceType("github");
                    setInputError(null);
                  }}
                  className={`flex-1 py-1.5 text-xs transition-colors ${
                    sourceType === "github"
                      ? "bg-zinc-700 text-zinc-100"
                      : "bg-zinc-800 text-zinc-400 hover:text-zinc-200"
                  }`}
                  aria-pressed={sourceType === "github"}
                >
                  Cloner depuis GitHub
                </button>
              </div>

              <form
                onSubmit={handleImport}
                noValidate
                className="flex flex-col gap-4"
              >
                {sourceType === "local" ? (
                  <>
                    <div>
                      <label
                        htmlFor="import-path"
                        className="block text-xs text-zinc-400 mb-1"
                      >
                        Chemin du dossier{" "}
                        <span className="text-red-400">*</span>
                      </label>
                      <input
                        id="import-path"
                        type="text"
                        value={sourcePath}
                        onChange={(e) => {
                          setSourcePath(e.target.value);
                          setInputError(null);
                        }}
                        placeholder="/Users/vous/Desktop/mon-projet"
                        className="w-full bg-zinc-800 border border-zinc-600 rounded-sm px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-hidden focus:border-zinc-400"
                        autoFocus
                      />
                      {inputError && (
                        <p className="mt-1 text-xs text-red-400" role="alert">
                          {inputError}
                        </p>
                      )}
                    </div>

                    <fieldset>
                      <legend className="text-xs text-zinc-400 mb-2">
                        Mode
                      </legend>
                      <div className="flex gap-4">
                        <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                          <input
                            type="radio"
                            name="import-mode"
                            value="symlink"
                            checked={mode === "symlink"}
                            onChange={() => setMode("symlink")}
                            className="accent-zinc-400"
                          />
                          Symlink (recommandé)
                        </label>
                        <label className="flex items-center gap-2 text-sm text-zinc-300 cursor-pointer">
                          <input
                            type="radio"
                            name="import-mode"
                            value="copy"
                            checked={mode === "copy"}
                            onChange={() => setMode("copy")}
                            className="accent-zinc-400"
                          />
                          Copie
                        </label>
                      </div>
                    </fieldset>
                  </>
                ) : (
                  <div>
                    <label
                      htmlFor="github-url"
                      className="block text-xs text-zinc-400 mb-1"
                    >
                      URL du repo GitHub <span className="text-red-400">*</span>
                    </label>
                    <input
                      id="github-url"
                      type="url"
                      value={repoUrl}
                      onChange={(e) => {
                        setRepoUrl(e.target.value);
                        setInputError(null);
                      }}
                      placeholder="https://github.com/owner/mon-repo"
                      className="w-full bg-zinc-800 border border-zinc-600 rounded-sm px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-hidden focus:border-zinc-400"
                      autoFocus
                    />
                    {inputError && (
                      <p className="mt-1 text-xs text-red-400" role="alert">
                        {inputError}
                      </p>
                    )}
                    <p className="mt-1 text-xs text-zinc-500">
                      Les repos privés nécessitent un token configuré dans les
                      settings.
                    </p>
                  </div>
                )}

                {apiError && (
                  <p className="text-xs text-red-400" role="alert">
                    {apiError}
                  </p>
                )}

                <div className="flex gap-3 justify-end">
                  <button
                    type="button"
                    onClick={onClose}
                    className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors"
                  >
                    Annuler
                  </button>
                  <button
                    type="submit"
                    className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded-sm transition-colors flex items-center gap-2"
                  >
                    {sourceType === "local" ? "Importer" : "Cloner"}
                  </button>
                </div>
              </form>
            </>
          )}

          {/* Step 2 — Loading */}
          {isLoading && (
            <>
              <h2 className="text-zinc-100 text-base font-semibold">
                {sourceType === "github"
                  ? "Clone et analyse du repo…"
                  : "Import et analyse du projet…"}
              </h2>
              <ProgressBar step={step as "importing" | "analyzing"} />
            </>
          )}

          {/* Step 3 — Review */}
          {step === "review" && analysis && project && (
            <>
              <h2 className="text-zinc-100 text-base font-semibold">
                <IconCheck size={14} /> {project.name} importé
              </h2>

              <div>
                <div className="flex items-center justify-between mb-1">
                  <span className="text-xs text-zinc-400">
                    CLAUDE.md généré
                  </span>
                  <button
                    onClick={() => setEditingClaudeMd((v) => !v)}
                    className="text-xs text-zinc-500 hover:text-zinc-300 transition-colors"
                  >
                    {editingClaudeMd ? "Aperçu" : "Modifier"}
                  </button>
                </div>
                {editingClaudeMd ? (
                  <textarea
                    value={claudeMdDraft}
                    onChange={(e) => setClaudeMdDraft(e.target.value)}
                    rows={8}
                    className="w-full bg-zinc-800 border border-zinc-700 rounded-sm px-3 py-2 text-xs text-zinc-200 font-mono focus:outline-hidden focus:border-zinc-500 resize-none"
                  />
                ) : (
                  <pre className="bg-zinc-800 border border-zinc-700 rounded-sm px-3 py-2 text-xs text-zinc-300 font-mono whitespace-pre-wrap max-h-40 overflow-y-auto">
                    {claudeMdDraft}
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
                  {analysis.suggested_agents.map((agent) => {
                    const present = registeredAgents.has(agent);
                    return (
                      <div
                        key={agent}
                        className="flex items-center justify-between"
                      >
                        <span className="text-sm text-zinc-300">
                          <span
                            role="img"
                            aria-label={
                              present ? "agent enregistré" : "agent à créer"
                            }
                            className="inline-flex align-middle"
                          >
                            {present ? (
                              <IconCheck size={12} />
                            ) : (
                              <IconSettings size={12} />
                            )}
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
                  })}
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
                  onClick={handleValidate}
                  className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded-sm transition-colors"
                >
                  Valider et ouvrir
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}
