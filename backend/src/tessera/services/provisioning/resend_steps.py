"""The two Resend steps: domain and sending key, then verification — ticket-468.

Each step reads before it writes. Nothing is ever deleted: a key that exists
without its Vercel variable cannot be recovered (Resend shows a token once), so
the step names it and waits for a human instead of creating a second one.
"""
from typing import Literal

from tessera.services.provisioning.resend import ResendClient
from tessera.services.provisioning.resend_records import (
    STATUS_FAILED,
    STATUS_VERIFIED,
    ResendDomain,
)
from tessera.services.provisioning.steps import (
    ProvisioningContext,
    StepResult,
    StepState,
)
from tessera.utils.logger import get_logger
from tessera.utils.secrets import SECRETS, SecretRegistry

_logger = get_logger(__name__)

KEY_VARIABLE = "RESEND_API_KEY"
_WAITING_DNS = "DNS records are not published yet; verification was not launched"

_NOT_LAUNCHED = ("", "not_started")

KeyState =Literal["env_set", "orphan", "to_create"]

_NO_TOKEN = StepResult(
    StepState.NEEDS_HUMAN, "RESEND_API_KEY is not set in the Tessera .env; nothing was sent"
)


def key_name(ctx: ProvisioningContext) -> str:
    """Return the name of the project's sending key."""
    return f"{ctx.project_id}-sending"


class ResendDomainStep:
    """Find or create the sending domain, and a sending key written to Vercel."""

    name = "resend_domain"

    def __init__(self, client: ResendClient, registry: SecretRegistry = SECRETS) -> None:
        self._client = client
        self._registry = registry

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Read the domain and the key; ask for the DNS records of a pending domain."""
        if not self._client.configured:
            return _NO_TOKEN
        domaine = await self._client.find_domain(ctx.online.domain)
        if domaine is not None:
            await self._ask_dns(ctx, domaine)
        etat = await self._key_state(ctx)
        if etat == "orphan":
            return self._orphan(ctx)
        manques = ["domain"] if domaine is None else []
        manques += ["sending key"] if etat == "to_create" else []
        if not manques:
            return StepResult(StepState.SKIPPED, "domain and sending key are in place")
        return StepResult(StepState.TODO, "missing: " + ", ".join(manques))

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Create the domain and the key, each only if absent."""
        if not self._client.configured:
            return _NO_TOKEN
        faits: list[str] = []
        domaine = await self._client.find_domain(ctx.online.domain)
        if domaine is None:
            domaine = await self._client.create_domain(ctx.online.domain)
            faits.append(f"domain {ctx.online.domain} created")
        await self._ask_dns(ctx, domaine)
        etat = await self._key_state(ctx)
        if etat == "orphan":
            return self._orphan(ctx, faits)
        if etat == "to_create":
            await self._create_key(ctx, domaine)
            faits.append(f"sending key written to {KEY_VARIABLE}")
        state = StepState.DONE if faits else StepState.SKIPPED
        return StepResult(state, ", ".join(faits) or "nothing to create")

    async def _key_state(self, ctx: ProvisioningContext) -> KeyState:
        if await ctx.env_writer.has_env(KEY_VARIABLE):
            return "env_set"
        if await self._client.has_api_key(key_name(ctx)):
            return "orphan"
        return "to_create"

    async def _create_key(self, ctx: ProvisioningContext, domaine: ResendDomain) -> None:
        token = await self._client.create_sending_key(key_name(ctx), domaine.id)
        # Inscrit avant l'écriture : une erreur ou un log ne doit pas pouvoir le citer.
        self._registry.register(token)
        await ctx.env_writer.set_env(KEY_VARIABLE, token)
        ctx.changed_env.add(KEY_VARIABLE)
        _logger.info("resend_key_written", extra={"variable": KEY_VARIABLE})

    @staticmethod
    def _orphan(ctx: ProvisioningContext, faits: list[str] | None = None) -> StepResult:
        detail = (
            f"key '{key_name(ctx)}' exists in Resend but {KEY_VARIABLE} is missing in "
            f"Vercel and a key cannot be read back: delete '{key_name(ctx)}' in Resend, "
            "then relaunch"
        )
        if faits:
            detail = ", ".join(faits) + "; " + detail
        return StepResult(StepState.NEEDS_HUMAN, detail)

    async def _ask_dns(self, ctx: ProvisioningContext, domaine: ResendDomain) -> None:
        if domaine.verified:
            return
        # La liste ne porte pas les enregistrements : on relit le domaine.
        complet = domaine if domaine.records else await self._client.get_domain(domaine.id)
        for enregistrement in complet.records:
            if enregistrement not in ctx.wanted_dns:
                ctx.wanted_dns.append(enregistrement)


class ResendVerifyStep:
    """Launch the verification once the DNS records are published."""

    name = "resend_verify"

    def __init__(self, client: ResendClient) -> None:
        self._client = client

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Read the domain status; nothing is launched."""
        if not self._client.configured:
            return _NO_TOKEN
        domaine = await self._client.find_domain(ctx.online.domain)
        if domaine is None:
            return StepResult(StepState.TODO, "Resend domain is missing")
        if domaine.verified:
            return StepResult(StepState.SKIPPED, "domain is already verified")
        if not ctx.dns_published:
            return StepResult(StepState.PENDING, _WAITING_DNS)
        if domaine.status in _NOT_LAUNCHED:
            return StepResult(StepState.TODO, "verification is to be launched")
        # Déjà lancée : le statut réel du domaine, comme apply le rapporte.
        return _from_status(domaine.status)

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Launch the verification, only when the DNS records are published."""
        if not self._client.configured:
            return _NO_TOKEN
        if not ctx.dns_published:
            return StepResult(StepState.PENDING, _WAITING_DNS)
        domaine = await self._client.find_domain(ctx.online.domain)
        if domaine is None:
            return StepResult(
                StepState.NEEDS_HUMAN, f"Resend domain {ctx.online.domain} does not exist"
            )
        if domaine.verified:
            return StepResult(StepState.SKIPPED, "domain is already verified")
        await self._client.verify_domain(domaine.id)
        return _from_status((await self._client.get_domain(domaine.id)).status)


def _from_status(status: str) -> StepResult:
    """Map a Resend domain status to a step result."""
    if status == STATUS_VERIFIED:
        return StepResult(StepState.DONE, "domain verified")
    if status == STATUS_FAILED:
        return StepResult(StepState.FAILED, "Resend could not verify the DNS records")
    # not_started, pending, temporary_failure : la propagation n'est pas finie.
    return StepResult(StepState.PENDING, f"verification is {status or 'pending'}; relaunch later")
