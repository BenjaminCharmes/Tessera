"""The (method, path) pairs of the API are frozen — ticket-687.

Déplacer l'assemblage d'un run hors du routeur ne change aucun endpoint
(ADR-041) : si un couple apparaît ou disparaît, ce test le dit avant la revue.
"""

from tessera.main import app

#: Les couples (méthode, chemin) de `app.openapi()["paths"]`, triés.
COUPLES: list[tuple[str, str]] = [
    ("DELETE", "/api/v1/agents/registry/{role}"),
    ("DELETE", "/api/v1/projects/{project_id}"),
    ("GET", "/api/v1/agents/registry"),
    ("GET", "/api/v1/agents/registry/{role}"),
    ("GET", "/api/v1/fs/list"),
    ("GET", "/api/v1/fs/read"),
    ("GET", "/api/v1/orchestrator/limits"),
    ("GET", "/api/v1/projects"),
    ("GET", "/api/v1/projects/overview"),
    ("GET", "/api/v1/projects/usage/breakdown"),
    ("GET", "/api/v1/projects/{project_id}"),
    ("GET", "/api/v1/projects/{project_id}/agents"),
    ("GET", "/api/v1/projects/{project_id}/artifacts"),
    ("GET", "/api/v1/projects/{project_id}/branches/cleanup"),
    ("GET", "/api/v1/projects/{project_id}/captures"),
    ("GET", "/api/v1/projects/{project_id}/captures/{fichier}"),
    ("GET", "/api/v1/projects/{project_id}/chat"),
    ("GET", "/api/v1/projects/{project_id}/chat/{conversation_id}"),
    ("GET", "/api/v1/projects/{project_id}/context"),
    ("GET", "/api/v1/projects/{project_id}/git/status"),
    ("GET", "/api/v1/projects/{project_id}/icon"),
    ("GET", "/api/v1/projects/{project_id}/pipeline"),
    ("GET", "/api/v1/projects/{project_id}/pr-statuses"),
    ("GET", "/api/v1/projects/{project_id}/provision"),
    ("GET", "/api/v1/projects/{project_id}/removal-plan"),
    ("GET", "/api/v1/projects/{project_id}/runs"),
    ("GET", "/api/v1/projects/{project_id}/services"),
    ("GET", "/api/v1/projects/{project_id}/tickets"),
    ("GET", "/api/v1/projects/{project_id}/tickets/archive"),
    ("GET", "/api/v1/projects/{project_id}/tickets/check"),
    ("GET", "/api/v1/projects/{project_id}/tickets/{ticket_id}"),
    ("GET", "/api/v1/projects/{project_id}/tickets/{ticket_id}/activity"),
    ("GET", "/api/v1/projects/{project_id}/tickets/{ticket_id}/diff"),
    ("GET", "/api/v1/projects/{project_id}/tickets/{ticket_id}/pr-status"),
    ("GET", "/api/v1/projects/{project_id}/tickets/{ticket_id}/runs"),
    ("GET", "/api/v1/projects/{project_id}/usage"),
    ("GET", "/api/v1/projects/{project_id}/usage/breakdown"),
    ("GET", "/api/v1/runs/{run_id}"),
    ("GET", "/api/v1/runs/{run_id}/events"),
    ("GET", "/api/v1/services/running"),
    ("GET", "/api/v1/services/running/activite"),
    ("GET", "/api/v1/services/running/avertissements"),
    ("GET", "/api/v1/tessera/salle"),
    ("GET", "/api/v1/usage/quota"),
    ("GET", "/api/v1/usage/recent-runs"),
    ("GET", "/api/v1/usage/stats"),
    ("GET", "/health"),
    ("PATCH", "/api/v1/projects/{project_id}/pipeline"),
    ("PATCH", "/api/v1/projects/{project_id}/tickets/{ticket_id}"),
    ("POST", "/api/v1/agents/create-agent"),
    ("POST", "/api/v1/agents/create-project"),
    ("POST", "/api/v1/agents/registry"),
    ("POST", "/api/v1/agents/run"),
    ("POST", "/api/v1/orchestrator/run"),
    ("POST", "/api/v1/orchestrator/runs/{run_id}/append"),
    ("POST", "/api/v1/orchestrator/runs/{run_id}/remove"),
    ("POST", "/api/v1/projects"),
    ("POST", "/api/v1/projects/clone"),
    ("POST", "/api/v1/projects/from-template"),
    ("POST", "/api/v1/projects/import"),
    ("POST", "/api/v1/projects/{project_id}/analyze"),
    ("POST", "/api/v1/projects/{project_id}/branches/cleanup"),
    ("POST", "/api/v1/projects/{project_id}/captures"),
    ("POST", "/api/v1/projects/{project_id}/chat/run"),
    ("POST", "/api/v1/projects/{project_id}/detach"),
    ("POST", "/api/v1/projects/{project_id}/git/init"),
    ("POST", "/api/v1/projects/{project_id}/git/link"),
    ("POST", "/api/v1/projects/{project_id}/github/sync"),
    ("POST", "/api/v1/projects/{project_id}/plan"),
    ("POST", "/api/v1/projects/{project_id}/provision"),
    ("POST", "/api/v1/projects/{project_id}/services/start"),
    ("POST", "/api/v1/projects/{project_id}/services/stop"),
    ("POST", "/api/v1/projects/{project_id}/tickets"),
    ("POST", "/api/v1/projects/{project_id}/tickets/archive"),
    ("POST", "/api/v1/projects/{project_id}/tickets/batch"),
    ("POST", "/api/v1/projects/{project_id}/tickets/propose"),
    ("POST", "/api/v1/projects/{project_id}/tickets/{ticket_id}/create-pr"),
    ("POST", "/api/v1/projects/{project_id}/tickets/{ticket_id}/merge-pr"),
    ("POST", "/api/v1/projects/{project_id}/tickets/{ticket_id}/open-pr"),
    ("POST", "/api/v1/services/running/{pid}/stop"),
    ("POST", "/api/v1/signalements"),
    ("PUT", "/api/v1/agents/registry/{role}"),
    ("PUT", "/api/v1/fs/write"),
    ("PUT", "/api/v1/projects/{project_id}/agents/{role}"),
    ("PUT", "/api/v1/projects/{project_id}/artifacts"),
]


def _couples_courants() -> list[tuple[str, str]]:
    chemins = app.openapi()["paths"]
    return sorted((methode.upper(), chemin) for chemin, ops in chemins.items() for methode in ops)


def test_the_method_and_path_pairs_of_the_api_are_unchanged() -> None:
    assert _couples_courants() == COUPLES


def test_the_orchestrator_endpoints_stay_on_the_router() -> None:
    orchestrateur = [c for c in COUPLES if c[1].startswith("/api/v1/orchestrator/")]

    assert orchestrateur == [
        ("GET", "/api/v1/orchestrator/limits"),
        ("POST", "/api/v1/orchestrator/run"),
        ("POST", "/api/v1/orchestrator/runs/{run_id}/append"),
        ("POST", "/api/v1/orchestrator/runs/{run_id}/remove"),
    ]

