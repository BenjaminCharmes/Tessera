"""The Vercel deployment step: first deployment, or redeploy after a variable — ticket-489.

Creating a Vercel project through the API does not deploy it, so a project put
online with no variable to write would stay without any production deployment.
The step reads the newest production deployment first and decides from it.
"""
from typing import Optional

from tessera.config import settings
from tessera.services.provisioning.errors import ServiceError
from tessera.services.provisioning.github_repo import GitHubRepoLookup, RepoIdSource
from tessera.services.provisioning.steps import ProvisioningContext, StepResult, StepState
from tessera.services.provisioning.vercel import SERVICE, VercelClient, vercel_name
from tessera.services.provisioning.vercel_deployments import VercelDeployment

_NO_TOKEN = StepResult(
    StepState.NEEDS_HUMAN, "VERCEL_TOKEN is not set in the Tessera .env; nothing was sent"
)


def _failed(deploiement: VercelDeployment) -> StepResult:
    """Report a build in ``ERROR`` by Vercel's error code, never by its log."""
    code = ServiceError(SERVICE, 0, deploiement.error_code).code
    return StepResult(StepState.FAILED, f"production deployment failed ({code})")


def _judged(deploiement: VercelDeployment, fait: str) -> StepResult:
    """Turn the deployment Vercel just returned into the step result."""
    if deploiement.failed:
        return _failed(deploiement)
    if deploiement.ready:
        return StepResult(StepState.DONE, fait)
    return StepResult(StepState.PENDING, f"{fait}; the build is not finished")


class VercelRedeployStep:
    """Make sure production has a deployment, and redeploy it after a new variable."""

    name = "redeploy"

    def __init__(self, client: VercelClient, repos: Optional[RepoIdSource] = None) -> None:
        self._client = client
        self._repos = repos or GitHubRepoLookup.from_settings(settings)

    async def _latest(self, project_id: str) -> Optional[VercelDeployment]:
        """The newest production deployment that still counts (a canceled one does not)."""
        dernier = await self._client.latest_deployment(project_id)
        return None if dernier is None or dernier.canceled else dernier

    async def _project_id(self, ctx: ProvisioningContext) -> Optional[str]:
        projet = await self._client.get_project(vercel_name(ctx.project_id))
        identifiant = projet.get("id") if projet else None
        return identifiant if isinstance(identifiant, str) else None

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Read the newest production deployment; nothing is written."""
        if not self._client.configured:
            return _NO_TOKEN
        identifiant = await self._project_id(ctx)
        dernier = await self._latest(identifiant) if identifiant else None
        if dernier is None:
            return StepResult(StepState.TODO, "no production deployment: the first one is needed")
        if dernier.failed:
            return _failed(dernier)
        if dernier.in_progress:
            return StepResult(StepState.PENDING, "the production deployment is building")
        if ctx.changed_env:
            return StepResult(StepState.TODO, "variables written: a redeploy is needed")
        return StepResult(StepState.SKIPPED, "production is deployed and no variable was written")

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Create the first deployment, or redeploy when a variable was written."""
        if not self._client.configured:
            return _NO_TOKEN
        identifiant = await self._project_id(ctx)
        if identifiant is None:
            return StepResult(StepState.FAILED, "the Vercel project is missing: nothing to deploy")
        dernier = await self._latest(identifiant)
        if dernier is None:
            return await self._first_deployment(ctx)
        if dernier.failed:
            return _failed(dernier)
        if dernier.in_progress:
            return StepResult(StepState.PENDING, "the production deployment is building")
        if not ctx.changed_env:
            return StepResult(StepState.SKIPPED, "production is deployed and no variable was written")
        return await self._redeploy(ctx, identifiant)

    async def _first_deployment(self, ctx: ProvisioningContext) -> StepResult:
        remote = ctx.github_remote
        if not remote:
            return StepResult(
                StepState.NEEDS_HUMAN,
                "the project has no GitHub remote: Vercel has nothing to deploy from",
            )
        repo_id = await self._repos.repo_id(remote)
        if repo_id is None:
            return StepResult(
                StepState.NEEDS_HUMAN,
                f"the id of GitHub repository {remote} could not be read: "
                "check that it exists and that GITHUB_TOKEN can see it",
            )
        branche = ctx.base_branch or settings.github_base_branch
        cree = await self._client.create_deployment(vercel_name(ctx.project_id), repo_id, branche)
        return _judged(cree, f"first production deployment created from {branche}")

    async def _redeploy(self, ctx: ProvisioningContext, project_id: str) -> StepResult:
        pret = await self._client.latest_production_deployment(project_id)
        if pret is None:
            return StepResult(StepState.SKIPPED, "no ready production deployment to redeploy yet")
        await self._client.redeploy(vercel_name(ctx.project_id), pret)
        return StepResult(StepState.DONE, "production redeployed")
