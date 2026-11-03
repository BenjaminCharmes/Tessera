import type {
  AnalysisResult,
  CloneProjectRequest,
  CloneProjectResponse,
  EtapeMiseEnLigne,
  ImportProjectRequest,
  ImportProjectResponse,
  PipelineReglages,
  PipelineReglagesPatch,
  PlanResult,
  Project,
  ProjectCreationResult,
  ProjectOverview,
  TemplateCreationResult,
} from "../types/api";
import { patch_, post } from "./apiVerbes";
import { request } from "./http";

export const projects = {
  list: (): Promise<Project[]> => request("/projects"),
  /** Tout ce que les cartes de la vue Projets affichent, en une requête (ticket-399). */
  overview: (): Promise<ProjectOverview[]> => request("/projects/overview"),
  /** Range un projet dans une catégorie ; une chaîne vide l'en retire (ticket-399). */
  setCategory: (projectId: string, category: string): Promise<PipelineReglages> =>
    patch_(`/projects/${projectId}/pipeline`, { category }),
  create: (
    name: string,
    description: string,
  ): Promise<ProjectCreationResult> =>
    post("/projects", {
      project_id: name.toLowerCase().replace(/\s+/g, "-"),
      name,
      description,
    }),
  createFromTemplate: (
    projectId: string,
    name: string,
  ): Promise<TemplateCreationResult> =>
    post("/projects/from-template", { project_id: projectId, name }),
  import: (req: ImportProjectRequest): Promise<ImportProjectResponse> =>
    post("/projects/import", req),
  clone: (req: CloneProjectRequest): Promise<CloneProjectResponse> =>
    post("/projects/clone", req),
  analyze: (projectId: string, overwrite = false): Promise<AnalysisResult> =>
    post(`/projects/${projectId}/analyze`, { overwrite }),
  plan: (projectId: string, description: string): Promise<PlanResult> =>
    post(`/projects/${projectId}/plan`, { description }),
};

export const pipeline = {
  /** Les réglages du pipeline d'un projet (ticket-196). */
  get: (projectId: string): Promise<PipelineReglages> =>
    request(`/projects/${projectId}/pipeline`),
  set: (projectId: string, patch: PipelineReglagesPatch): Promise<PipelineReglages> =>
    patch_(`/projects/${projectId}/pipeline`, patch),
};

export const provisioning = {
  /** L'état de chaque étape, lu sans rien écrire — ticket-472. */
  read: (projectId: string): Promise<EtapeMiseEnLigne[]> =>
    request(`/projects/${projectId}/provision`),
  /** Lance la mise en ligne ; 409 si une autre tourne déjà, 422 si le bloc est invalide. */
  start: (projectId: string): Promise<{ project_id: string; steps: string[] }> =>
    post(`/projects/${projectId}/provision`, {}),
};
