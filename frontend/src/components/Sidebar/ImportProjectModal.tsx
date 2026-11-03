import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import Modale from "../../design/ui/Modale";
import type { AnalysisResult, Project } from "../../types/api";
import ImportProgression from "./ImportProgression";
import ImportRevue from "./ImportRevue";
import ImportSaisie from "./ImportSaisie";
import {
  validateGithubUrl,
  validateLocalPath,
  type ImportMode,
  type SourceType,
} from "./importValidation";

type ImportStep = "idle" | "importing" | "analyzing" | "review" | "error";

interface ImportProjectModalProps {
  onClose: () => void;
  onProjectCreated: (project: Project) => void;
}

interface Imported {
  project: Project;
  analysis: AnalysisResult;
}

async function importLocal(
  sourcePath: string,
  mode: ImportMode,
  onAnalyzing: () => void,
): Promise<Imported> {
  const res = await api.projects.import({
    source_path: sourcePath.trim(),
    mode,
  });
  onAnalyzing();
  const analysis = await api.projects.analyze(res.project.id, false);
  return { project: res.project, analysis };
}

async function cloneGithub(
  repoUrl: string,
  onAnalyzing: () => void,
): Promise<Imported> {
  const res = await api.projects.clone({ repo_url: repoUrl.trim() });
  onAnalyzing();
  // Le clone ne renvoie pas le CLAUDE.md : on l'analyse pour la revue.
  const analysis = await api.projects.analyze(res.project.id, false);
  return { project: res.project, analysis };
}

export default function ImportProjectModal({
  onClose,
  onProjectCreated,
}: ImportProjectModalProps) {
  const [sourceType, setSourceType] = useState<SourceType>("local");
  const [step, setStep] = useState<ImportStep>("idle");
  const [sourcePath, setSourcePath] = useState("");
  const [mode, setMode] = useState<ImportMode>("symlink");
  const [repoUrl, setRepoUrl] = useState("");
  const [inputError, setInputError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [imported, setImported] = useState<Imported | null>(null);
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
      const onAnalyzing = () => setStep("analyzing");
      setImported(
        sourceType === "local"
          ? await importLocal(sourcePath, mode, onAnalyzing)
          : await cloneGithub(repoUrl, onAnalyzing),
      );
      setStep("review");
    } catch (error: unknown) {
      setApiError(error instanceof Error ? error.message : "Erreur inconnue");
      setStep("error");
    }
  }

  function handleValidate() {
    if (!imported) return;
    onProjectCreated(imported.project);
    onClose();
  }

  return (
    <Modale onFermer={onClose} aria-label="Importer un projet">
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 w-full max-w-lg shadow-xl flex flex-col gap-4">
        {(step === "idle" || step === "error") && (
          <ImportSaisie
            sourceType={sourceType}
            sourcePath={sourcePath}
            mode={mode}
            repoUrl={repoUrl}
            inputError={inputError}
            apiError={apiError}
            onSourceType={(value) => {
              setSourceType(value);
              setInputError(null);
            }}
            onSourcePath={(value) => {
              setSourcePath(value);
              setInputError(null);
            }}
            onMode={setMode}
            onRepoUrl={(value) => {
              setRepoUrl(value);
              setInputError(null);
            }}
            onSubmit={handleImport}
            onClose={onClose}
          />
        )}
        {(step === "importing" || step === "analyzing") && (
          <ImportProgression step={step} sourceType={sourceType} />
        )}
        {step === "review" && imported && (
          <ImportRevue
            project={imported.project}
            analysis={imported.analysis}
            registeredAgents={registeredAgents}
            onClose={onClose}
            onValidate={handleValidate}
          />
        )}
      </div>
    </Modale>
  );
}
