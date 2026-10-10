import { IconCheck } from "../../design/icons";
import { useState } from "react";
import type { Project } from "../../types/api";
import { api } from "../../lib/api";

interface CreateProjectModalProps {
  onClose: () => void;
  onCreated: (project: Project) => void;
}

function validateName(value: string): string | null {
  if (!value) return "Le nom est requis";
  if (/\s/.test(value)) return "Le nom ne doit pas contenir d'espaces";
  if (value.length > 50) return "Le nom ne doit pas dépasser 50 caractères";
  return null;
}

interface TemplatePorts {
  backend: number;
  frontend: number;
}

export default function CreateProjectModal({
  onClose,
  onCreated,
}: CreateProjectModalProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [templateMode, setTemplateMode] = useState(false);
  const [nameError, setNameError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [createdProject, setCreatedProject] = useState<Project | null>(null);
  const [agentsCreated, setAgentsCreated] = useState<string[]>([]);
  const [depotPret, setDepotPret] = useState(true);
  const [templatePorts, setTemplatePorts] = useState<TemplatePorts | null>(
    null,
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const error = validateName(name);
    if (error) {
      setNameError(error);
      return;
    }
    setNameError(null);
    setApiError(null);
    setLoading(true);
    try {
      if (templateMode) {
        // Même identifiant que pour un projet vide (`api.projects.create`).
        const result = await api.projects.createFromTemplate(
          name.toLowerCase().replace(/\s+/g, "-"),
          name,
        );
        setCreatedProject(result.project);
        setAgentsCreated([]);
        setDepotPret(result.git_ready);
        setTemplatePorts({
          backend: result.backend_port,
          frontend: result.frontend_port,
        });
      } else {
        const result = await api.projects.create(name, description);
        setCreatedProject(result.project);
        setAgentsCreated(result.agents_created);
        setDepotPret(result.repository_ready);
      }
    } catch (err: unknown) {
      setApiError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }

  function handleOverlayClick(e: React.MouseEvent) {
    if (e.target === e.currentTarget) {
      if (createdProject) {
        onCreated(createdProject);
      } else {
        onClose();
      }
    }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === "Escape") {
      if (createdProject) {
        onCreated(createdProject);
      } else {
        onClose();
      }
    }
  }

  if (createdProject) {
    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
        onClick={handleOverlayClick}
        onKeyDown={handleKeyDown}
        role="dialog"
        aria-modal="true"
        aria-label="Projet créé"
      >
        <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 w-full max-w-md shadow-xl">
          <p className="inline-flex items-center gap-1 text-green-400 text-sm font-medium mb-1">
            <IconCheck size={14} /> Projet &ldquo;{createdProject.name}&rdquo;
            créé
          </p>
          {agentsCreated.length > 0 && (
            <p className="text-zinc-400 text-xs mt-1">
              {agentsCreated.length} agent
              {agentsCreated.length > 1 ? "s" : ""} créé
              {agentsCreated.length > 1 ? "s" : ""} automatiquement :{" "}
              <span className="font-mono text-zinc-300">
                {agentsCreated.join(", ")}
              </span>
            </p>
          )}
          {templatePorts !== null ? (
            <>
              <p className="text-zinc-400 text-xs mt-2">
                Ports attribués : backend{" "}
                <span className="font-mono text-zinc-300">
                  {templatePorts.backend}
                </span>
                , frontend{" "}
                <span className="font-mono text-zinc-300">
                  {templatePorts.frontend}
                </span>
              </p>
              <p className="text-zinc-400 text-xs mt-3 font-medium">
                Étapes restantes :
              </p>
              {!depotPret && (
                <p className="text-amber-400 text-xs mt-2">
                  Le dépôt git n&rsquo;a pas pu être initialisé&nbsp;:
                  rattrapez-le depuis la section Git de la barre latérale avant
                  le premier run.
                </p>
              )}
              <ul className="mt-1 text-zinc-400 text-xs list-disc list-inside space-y-1">
                <li>
                  Écrire le{" "}
                  <span className="font-mono text-zinc-300">CLAUDE.md</span> du
                  projet
                </li>
                <li>Créer le dépôt GitHub</li>
              </ul>
            </>
          ) : (
            <>
              {/*
                Sans dépôt à sa racine, un projet est inerte pour le pipeline :
                GitWorkspaceService lève NotAGitRepository et le run s'arrête
                avant la première branche (ADR-024). Le dire ici plutôt qu'au
                premier run, où le message ne dirait pas quoi faire.
              */}
              {depotPret ? (
                <p className="text-zinc-400 text-xs mt-1">
                  Dépôt git initialisé
                </p>
              ) : (
                <p className="text-amber-400 text-xs mt-1">
                  Le dépôt git n&rsquo;a pas pu être initialisé. Le projet est
                  créé, mais aucun run ne démarrera tant qu&rsquo;il
                  n&rsquo;aura pas de dépôt à sa racine&nbsp;: rattrapez-le
                  depuis la section Git de la barre latérale.
                </p>
              )}
            </>
          )}
          <div className="flex justify-end mt-4">
            <button
              type="button"
              onClick={() => onCreated(createdProject)}
              className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded-sm transition-colors"
              autoFocus
            >
              Continuer
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      onClick={handleOverlayClick}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-label="Créer un projet"
    >
      <div className="bg-zinc-900 border border-zinc-700 rounded-lg p-6 w-full max-w-md shadow-xl">
        <h2 className="text-zinc-100 text-base font-semibold mb-4">
          Nouveau projet
        </h2>
        <form onSubmit={handleSubmit} noValidate>
          <div className="mb-4">
            <p className="text-xs text-zinc-400 mb-2">Type de projet</p>
            <div className="flex flex-col gap-2">
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="project-type"
                  value="empty"
                  checked={!templateMode}
                  onChange={() => setTemplateMode(false)}
                  disabled={loading}
                />
                <span className="text-sm text-zinc-200">Projet vide</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="project-type"
                  value="template"
                  checked={templateMode}
                  onChange={() => setTemplateMode(true)}
                  disabled={loading}
                />
                <span className="text-sm text-zinc-200">
                  Gabarit FastAPI + React
                </span>
              </label>
            </div>
          </div>
          <div className="mb-4">
            <label
              htmlFor="project-name"
              className="block text-xs text-zinc-400 mb-1"
            >
              Nom <span className="text-red-400">*</span>
            </label>
            <input
              id="project-name"
              type="text"
              value={name}
              onChange={(e) => {
                setName(e.target.value);
                setNameError(null);
              }}
              placeholder="mon-projet"
              maxLength={50}
              className="w-full bg-zinc-800 border border-zinc-600 rounded-sm px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-hidden focus:border-zinc-400"
              disabled={loading}
              autoFocus
            />
            {nameError && (
              <p className="mt-1 text-xs text-red-400" role="alert">
                {nameError}
              </p>
            )}
          </div>
          {!templateMode && (
            <div className="mb-5">
              <label
                htmlFor="project-description"
                className="block text-xs text-zinc-400 mb-1"
              >
                Description
              </label>
              <textarea
                id="project-description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Description optionnelle…"
                maxLength={200}
                rows={3}
                className="w-full bg-zinc-800 border border-zinc-600 rounded-sm px-3 py-2 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-hidden focus:border-zinc-400 resize-none"
                disabled={loading}
              />
            </div>
          )}
          {apiError && (
            <p className="mb-4 text-xs text-red-400" role="alert">
              {apiError}
            </p>
          )}
          <div className="flex gap-3 justify-end">
            <button
              type="button"
              onClick={onClose}
              disabled={loading}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-zinc-200 transition-colors disabled:opacity-50"
            >
              Annuler
            </button>
            <button
              type="submit"
              disabled={loading}
              className="px-4 py-2 text-sm bg-zinc-700 hover:bg-zinc-600 text-white rounded-sm transition-colors disabled:opacity-50 flex items-center gap-2"
            >
              {loading && (
                <span className="inline-block w-3 h-3 border-2 border-zinc-400 border-t-white rounded-full animate-spin" />
              )}
              Créer
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
