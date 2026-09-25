import type { Project, RunActif } from "../../types/api";

/**
 * Le projet d'un run sélectionné — ticket-164.
 *
 * `projects.find(...)` rendait `null` quand la liste ne portait pas le projet,
 * et le panneau affichait alors « sélectionne un projet » sur un run que
 * l'utilisateur venait précisément de sélectionner. La carte connaît son
 * `project_id` : faire dépendre l'affichage d'une correspondance qui peut
 * manquer perd deux fois.
 *
 * Le repli est volontairement minimal — il sert à identifier, pas à décrire.
 */
export function projetDuRun(
  projects: Project[],
  run: RunActif | null,
): Project | null {
  if (run === null) return null;
  const connu = projects.find((p) => p.id === run.project_id);
  if (connu) return connu;
  return {
    id: run.project_id,
    name: run.project_id,
    path: null,
    description: "",
    active_agents: [],
    stack: null,
    raw_claude_md: "",
    github_remote: null,
  };
}
