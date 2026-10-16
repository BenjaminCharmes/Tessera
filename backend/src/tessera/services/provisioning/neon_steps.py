"""The database step: a Neon project and ``DATABASE_URL`` in Vercel — ticket-467.

The connection URI (password included) goes from the Neon API to the Vercel
API and nowhere else: it is registered as a secret before it is sent, it is not
in a result detail, a log or an event, and it is never returned to the caller.
"""
from typing import Optional
from urllib.parse import unquote, urlsplit

from tessera.services.provisioning.neon import NeonClient
from tessera.services.provisioning.steps import (
    ProvisioningContext,
    StepResult,
    StepState,
)
from tessera.utils.logger import get_logger
from tessera.utils.secrets import SECRETS, SecretRegistry

_logger = get_logger(__name__)

URL_VARIABLE = "DATABASE_URL"


def _secrets_of(uri: str) -> list[str]:
    """Return what must be masked: the whole URI and its password, both forms."""
    try:
        mot_de_passe = urlsplit(uri).password or ""
    except ValueError:
        mot_de_passe = ""
    return [uri, mot_de_passe, unquote(mot_de_passe)]


class DatabaseStep:
    """Find or create the Neon project, hand its URI to Vercel as ``DATABASE_URL``."""

    name = "database"

    def __init__(self, client: NeonClient, registry: SecretRegistry = SECRETS) -> None:
        self._client = client
        self._registry = registry

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Read Neon and Vercel; the URI is not even requested."""
        court = await self._shortcut(ctx)
        if court is not None:
            return court
        ids = await self._client.find_projects(ctx.project_id)
        if len(ids) > 1:
            return self._ambiguous(ctx)
        if ids:
            return StepResult(StepState.TODO, f"Neon project exists, {URL_VARIABLE} is missing")
        return StepResult(StepState.TODO, "Neon project is missing")

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Create the project if absent, then write the URI in Vercel if absent."""
        court = await self._shortcut(ctx)
        if court is not None:
            return court
        ids = await self._client.find_projects(ctx.project_id)
        if len(ids) > 1:
            return self._ambiguous(ctx)
        if ids:
            uri, fait = await self._client.connection_uri(ids[0]), "Neon project found"
        else:
            uri, fait = await self._create(ctx), "Neon project created"
        await self._hand_over(ctx, uri)
        return StepResult(StepState.DONE, f"{fait}; {URL_VARIABLE} written to Vercel")

    async def _shortcut(self, ctx: ProvisioningContext) -> Optional[StepResult]:
        """Answer without asking Neon when the variable decides, or no key is set."""
        presente = await ctx.env_writer.has_env(URL_VARIABLE)
        if not self._client.configured:
            return self._without_key(ctx, presente)
        if presente:
            return StepResult(StepState.SKIPPED, f"{URL_VARIABLE} is already set in Vercel")
        return None

    @staticmethod
    def _without_key(ctx: ProvisioningContext, presente: bool) -> StepResult:
        if presente:
            return StepResult(
                StepState.MANUAL,
                f"NEON_API_KEY is not set; {URL_VARIABLE} is present in Vercel, Neon was not checked",
            )
        return StepResult(
            StepState.NEEDS_HUMAN,
            "NEON_API_KEY is not set in the Tessera .env. Create the Neon project "
            f"'{ctx.project_id}' yourself and add {URL_VARIABLE} to the Vercel project, "
            "or set the key and relaunch",
        )

    @staticmethod
    def _ambiguous(ctx: ProvisioningContext) -> StepResult:
        return StepResult(
            StepState.FAILED,
            f"several Neon projects are named '{ctx.project_id}'; nothing was created",
        )

    async def _create(self, ctx: ProvisioningContext) -> str:
        cree = await self._client.create_project(ctx.project_id)
        # Le projet existe déjà : l'URI est lue par l'API si la création ne l'a pas rendue.
        return cree.uri or await self._client.connection_uri(cree.id)

    async def _hand_over(self, ctx: ProvisioningContext, uri: str) -> None:
        # Inscrit avant l'envoi : une erreur ou un log ne doit pas pouvoir la citer.
        self._registry.register_all(_secrets_of(uri))
        await ctx.env_writer.set_env(URL_VARIABLE, uri)
        ctx.changed_env.add(URL_VARIABLE)
        _logger.info("neon_url_written", extra={"project": ctx.project_id})
