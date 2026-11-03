import type {
  AgentSettingsPatch,
  ArtifactMode,
  ArtifactModeState,
  GitStatus,
  PlanDeNettoyage,
  ProjectAgents,
  RemovalPlan,
} from "../types/api";
import { del, post, put } from "./apiVerbes";
import { request } from "./http";

export const git = {
  status: (projectId: string): Promise<GitStatus> =>
    request(`/projects/${projectId}/git/status`),
  init: (projectId: string): Promise<GitStatus> =>
    post(`/projects/${projectId}/git/init`, {}),
  link: (
    projectId: string,
    repoUrl: string,
    confirmed = false,
  ): Promise<GitStatus> =>
    post(`/projects/${projectId}/git/link`, {
      repo_url: repoUrl,
      confirmed,
    }),
  removalPlan: (projectId: string): Promise<RemovalPlan> =>
    request(`/projects/${projectId}/removal-plan`),
  detach: (projectId: string): Promise<{ detached: boolean; moved_to: string }> =>
    post(`/projects/${projectId}/detach`, {}),
  remove: (projectId: string): Promise<void> =>
    del(`/projects/${projectId}?confirmed=true`),
  agents: (projectId: string): Promise<ProjectAgents> =>
    request(`/projects/${projectId}/agents`),
  setAgentModel: (
    projectId: string,
    role: string,
    patch: AgentSettingsPatch,
  ): Promise<ProjectAgents> =>
    put(`/projects/${projectId}/agents/${role}`, patch),
  cleanupPlan: (projectId: string): Promise<PlanDeNettoyage> =>
    request(`/projects/${projectId}/branches/cleanup`),
  cleanup: (projectId: string, branches: string[]): Promise<string[]> =>
    post(`/projects/${projectId}/branches/cleanup`, { branches }),
  artifacts: (projectId: string): Promise<ArtifactModeState> =>
    request(`/projects/${projectId}/artifacts`),
  setArtifacts: (
    projectId: string,
    mode: ArtifactMode,
  ): Promise<ArtifactModeState> =>
    put(`/projects/${projectId}/artifacts`, { mode }),
};
