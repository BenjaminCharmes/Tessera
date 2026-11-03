/**
 * Les routes que le contrat ne couvre pas — écrites, pas tues (ticket-684).
 * `contrat.test.ts` échoue quand une route du schéma n'est ni couverte ni ici :
 * une route nouvelle force le choix. Ranger une route ici ne dit pas que son
 * type est juste, seulement qu'elle n'a pas été confrontée.
 */
/** Sans `response_model` ou sans corps JSON : rien à confronter. */
export const SANS_SCHEMA: string[] = [
  "POST /api/v1/services/running/{pid}/stop", // `dict[str, object]` : le front type `{ pid, arretes }` à la main
  "POST /api/v1/orchestrator/run",
  "POST /api/v1/projects",
  "POST /api/v1/projects/clone",
  "POST /api/v1/projects/from-template",
  "POST /api/v1/projects/import",
  "DELETE /api/v1/projects/{project_id}",
  "POST /api/v1/projects/{project_id}/tickets",
  "POST /api/v1/projects/{project_id}/tickets/batch",
  "POST /api/v1/signalements",
  "PUT /api/v1/fs/write",
  "POST /api/v1/agents/registry",
  "DELETE /api/v1/agents/registry/{role}",
];

/**
 * Avec un `response_model`, mais hors du périmètre du ticket : leur type n'est
 * pas confronté (liste « Non examiné » de `docs/audit/doublons.md` §4).
 * `pr-statuses` en fait partie : `getPrStatuses` déplie `statuses`, donc la
 * valeur qu'une fixture lui donne n'est pas la réponse de la route.
 */
export const HORS_PERIMETRE: string[] = [
  "GET /api/v1/projects/usage/breakdown", // même schéma que la route d'un projet, aucun appel du front
  "GET /api/v1/services/running/avertissements",
  "GET /api/v1/usage/recent-runs",
  "GET /health",
  "GET /api/v1/projects/{project_id}/context",
  "GET /api/v1/projects/{project_id}/removal-plan",
  "GET /api/v1/projects/{project_id}/icon",
  "POST /api/v1/projects/{project_id}/detach",
  "POST /api/v1/projects/{project_id}/analyze",
  "POST /api/v1/projects/{project_id}/plan",
  "GET /api/v1/projects/{project_id}/provision",
  "POST /api/v1/projects/{project_id}/provision",
  "POST /api/v1/projects/{project_id}/tickets/propose",
  "POST /api/v1/projects/{project_id}/tickets/{ticket_id}/create-pr",
  "POST /api/v1/orchestrator/runs/{run_id}/append",
  "POST /api/v1/orchestrator/runs/{run_id}/remove",
  "POST /api/v1/agents/run",
  "GET /api/v1/projects",
  "GET /api/v1/projects/overview",
  "GET /api/v1/projects/{project_id}",
  "GET /api/v1/projects/{project_id}/agents",
  "PUT /api/v1/projects/{project_id}/agents/{role}",
  "GET /api/v1/projects/{project_id}/artifacts",
  "PUT /api/v1/projects/{project_id}/artifacts",
  "GET /api/v1/projects/{project_id}/captures",
  "POST /api/v1/projects/{project_id}/captures",
  "GET /api/v1/projects/{project_id}/captures/{fichier}",
  "GET /api/v1/projects/{project_id}/chat",
  "POST /api/v1/projects/{project_id}/chat/run",
  "GET /api/v1/projects/{project_id}/chat/{conversation_id}",
  "POST /api/v1/projects/{project_id}/git/init",
  "POST /api/v1/projects/{project_id}/git/link",
  "GET /api/v1/projects/{project_id}/git/status",
  "POST /api/v1/projects/{project_id}/github/sync",
  "GET /api/v1/projects/{project_id}/pipeline",
  "PATCH /api/v1/projects/{project_id}/pipeline",
  "GET /api/v1/projects/{project_id}/pr-statuses",
  "GET /api/v1/projects/{project_id}/runs",
  "GET /api/v1/projects/{project_id}/tickets",
  "GET /api/v1/projects/{project_id}/tickets/archive",
  "POST /api/v1/projects/{project_id}/tickets/archive",
  "GET /api/v1/projects/{project_id}/tickets/check",
  "GET /api/v1/projects/{project_id}/tickets/{ticket_id}",
  "PATCH /api/v1/projects/{project_id}/tickets/{ticket_id}",
  "GET /api/v1/projects/{project_id}/tickets/{ticket_id}/activity",
  "GET /api/v1/projects/{project_id}/tickets/{ticket_id}/diff",
  "POST /api/v1/projects/{project_id}/tickets/{ticket_id}/merge-pr",
  "POST /api/v1/projects/{project_id}/tickets/{ticket_id}/open-pr",
  "GET /api/v1/projects/{project_id}/tickets/{ticket_id}/pr-status",
  "GET /api/v1/projects/{project_id}/tickets/{ticket_id}/runs",
  "GET /api/v1/projects/{project_id}/usage",
  "GET /api/v1/runs/{run_id}/events",
  "GET /api/v1/services/running/activite",
  "GET /api/v1/tessera/salle",
  "GET /api/v1/usage/stats",
  "GET /api/v1/orchestrator/limits",
  "GET /api/v1/agents/registry",
  "GET /api/v1/agents/registry/{role}",
  "PUT /api/v1/agents/registry/{role}",
  "POST /api/v1/agents/create-agent",
  "POST /api/v1/agents/create-project",
  "GET /api/v1/fs/list",
  "GET /api/v1/fs/read",
];
