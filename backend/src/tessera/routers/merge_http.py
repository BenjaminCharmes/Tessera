"""The manual merge call, with a doubtful GitHub answer turned into a 502."""
import httpx
from fastapi import HTTPException

from tessera.services.github.github_workflow import GitHubWorkflowService


async def merge_ou_502(service: GitHubWorkflowService, pr_number: int) -> bool:
    """Merges the PR; a 5xx or "merge in progress" from GitHub answers 502."""
    try:
        return await service.merge_si_la_ci_est_verte(pr_number)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub n'a pas confirmé le merge (HTTP {exc.response.status_code}).",
        ) from exc
