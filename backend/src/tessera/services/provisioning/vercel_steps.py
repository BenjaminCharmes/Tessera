"""The three Vercel steps: project and domain, variables, redeploy — ticket-466.

Each step reads before it writes and only creates what is missing. Nothing is
ever deleted, and a variable that exists is never rewritten (a ``sensitive``
one cannot be read back, so its value is unknown).
"""
import secrets
from typing import Optional

from tessera.services.provisioning.errors import ServiceError
from tessera.services.provisioning.steps import (
    ProvisioningContext,
    StepResult,
    StepState,
)
from tessera.services.provisioning.vercel import (
    PUBLIC_PREFIX,
    VercelClient,
    vercel_name,
)
from tessera.services.provisioning.vercel_dns import VercelDomain
from tessera.utils.logger import get_logger
from tessera.utils.secrets import SECRETS, SecretRegistry

_logger = get_logger(__name__)

APP_URL_VARIABLE = f"{PUBLIC_PREFIX}APP_URL"
GENERATED_VARIABLES: tuple[str, ...] = ("SESSION_SECRET", "CRON_SECRET")
#: Code d'erreur de Vercel quand son application GitHub ne voit pas le dépôt.
REPO_NOT_FOUND = "repo_not_found"

_NO_TOKEN = StepResult(
    StepState.NEEDS_HUMAN, "VERCEL_TOKEN is not set in the Tessera .env; nothing was sent"
)


def _repo_access_missing(repo: Optional[str]) -> StepResult:
    """Tell the user how to give Vercel's GitHub application access to the repository."""
    cible = repo or "du projet"
    return StepResult(
        StepState.NEEDS_HUMAN,
        f"Vercel n'a pas accès au dépôt {cible} : installe l'application GitHub "
        "de Vercel (github.com/apps/vercel) sur ce dépôt, puis relance",
    )


class VercelProjectStep:
    """Find or create the project, attach the domain, ask for its DNS records."""

    name = "vercel_project"

    def __init__(self, client: VercelClient) -> None:
        self._client = client

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Read the project and its domain; ask for DNS when the domain is attached."""
        if not self._client.configured:
            return _NO_TOKEN
        nom = vercel_name(ctx.project_id)
        if await self._client.get_project(nom) is None:
            return StepResult(StepState.TODO, "Vercel project is missing")
        domaine = await self._client.get_domain(nom, ctx.online.domain)
        if domaine is None:
            return StepResult(StepState.TODO, f"domain {ctx.online.domain} is not attached")
        await self._ask_dns(ctx, domaine)
        return StepResult(StepState.SKIPPED, "project and domain are in place")

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Create the project and attach the domain, each only if absent."""
        if not self._client.configured:
            return _NO_TOKEN
        nom = vercel_name(ctx.project_id)
        faits: list[str] = []
        if await self._client.get_project(nom) is None:
            try:
                await self._client.create_project(nom, ctx.github_remote)
            except ServiceError as erreur:
                if erreur.code != REPO_NOT_FOUND:
                    raise
                return _repo_access_missing(ctx.github_remote)
            faits.append("project created")
        domaine = await self._client.get_domain(nom, ctx.online.domain)
        if domaine is None:
            domaine = await self._client.add_domain(nom, ctx.online.domain)
            faits.append(f"domain {ctx.online.domain} attached")
        await self._ask_dns(ctx, domaine)
        return StepResult(StepState.DONE, ", ".join(faits) or "nothing to create")

    async def _ask_dns(self, ctx: ProvisioningContext, domaine: VercelDomain) -> None:
        demandes = [] if domaine.verified else list(domaine.verification)
        demandes += await self._client.domain_config(ctx.online.domain)
        for enregistrement in demandes:
            if enregistrement not in ctx.wanted_dns:
                ctx.wanted_dns.append(enregistrement)


class VercelVariablesStep:
    """Write the app variables that are absent, as ``sensitive`` unless public."""

    name = "variables"

    def __init__(self, client: VercelClient, registry: SecretRegistry = SECRETS) -> None:
        self._client = client
        self._registry = registry

    async def _missing(self, ctx: ProvisioningContext) -> list[str]:
        voulues = [APP_URL_VARIABLE, *GENERATED_VARIABLES]
        return [nom for nom in voulues if not await ctx.env_writer.has_env(nom)]

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """List the missing variables by name; values are never read."""
        if not self._client.configured:
            return _NO_TOKEN
        absentes = await self._missing(ctx)
        if not absentes:
            return StepResult(StepState.SKIPPED, "variables are already set")
        return StepResult(StepState.TODO, "missing: " + ", ".join(absentes))

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Write each missing variable once and record it in ``ctx.changed_env``."""
        if not self._client.configured:
            return _NO_TOKEN
        ecrites: list[str] = []
        for nom in await self._missing(ctx):
            valeur = self._value_for(nom, ctx)
            # Inscrit avant l'envoi : une erreur ou un log ne doit pas pouvoir le citer.
            self._registry.register(valeur)
            await ctx.env_writer.set_env(nom, valeur)
            ctx.changed_env.add(nom)
            ecrites.append(nom)
        _logger.info("vercel_variables_written", extra={"names": ecrites})
        return StepResult(StepState.DONE, "wrote: " + (", ".join(ecrites) or "nothing"))

    @staticmethod
    def _value_for(nom: str, ctx: ProvisioningContext) -> str:
        if nom == APP_URL_VARIABLE:
            return f"https://{ctx.online.domain}"
        return secrets.token_urlsafe(32)


class VercelRedeployStep:
    """Redeploy production once, only if a variable was written during this run."""

    name = "redeploy"

    def __init__(self, client: VercelClient) -> None:
        self._client = client

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Nothing written during the run: nothing to redeploy."""
        if not self._client.configured:
            return _NO_TOKEN
        if not ctx.changed_env:
            return StepResult(StepState.SKIPPED, "no variable was written")
        return StepResult(StepState.TODO, "variables written: a redeploy is needed")

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Redeploy the latest production deployment, if there is one."""
        if not self._client.configured:
            return _NO_TOKEN
        nom = vercel_name(ctx.project_id)
        projet = await self._client.get_project(nom)
        identifiant = projet.get("id") if projet else None
        deploiement = None
        if isinstance(identifiant, str):
            deploiement = await self._client.latest_production_deployment(identifiant)
        if deploiement is None:
            # Pas encore de production : le premier déploiement lira les variables.
            return StepResult(StepState.SKIPPED, "no production deployment to redeploy yet")
        await self._client.redeploy(nom, deploiement)
        return StepResult(StepState.DONE, "production redeployed")
