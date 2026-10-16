"""The Stripe step: webhook, secret in Vercel, optional product and price — ticket-470.

Test mode is the default. A live key is only accepted when ``online.stripe.mode``
is ``"live"`` in ``agents.json`` (which agents cannot write, ADR-027), and the
refusal comes before any request. The Stripe API cannot create an API key:
``STRIPE_SECRET_KEY`` of the *site* is set by hand in Vercel, the step only
checks its name. The webhook signing secret goes from Stripe to Vercel and
nowhere else: it is registered as a secret before it is sent, it is not in a
result detail, a log or an event. An existing price, product or webhook is
never modified, and nothing is deleted.
"""
from dataclasses import dataclass, field
from typing import Optional

from tessera.services.provisioning.online_config import StripeConfig
from tessera.services.provisioning.steps import (
    ProvisioningContext,
    StepResult,
    StepState,
)
from tessera.services.provisioning.stripe_client import StripeClient
from tessera.utils.logger import get_logger
from tessera.utils.secrets import SECRETS, SecretRegistry

__all__ = ["SECRET_KEY_VARIABLE", "StripeClient", "StripeStep", "WEBHOOK_VARIABLE"]

_logger = get_logger(__name__)

SECRET_KEY_VARIABLE = "STRIPE_SECRET_KEY"
WEBHOOK_VARIABLE = "STRIPE_WEBHOOK_SECRET"
#: The declaration carries no currency: the price is in euros.
CURRENCY = "eur"


def lookup_key(project_id: str) -> str:
    """Return the ``lookup_key`` of the price of a project."""
    return f"tessera_{project_id}"


@dataclass
class _Report:
    """What one pass created (``done``) or found missing (``missing``)."""

    done: list[str] = field(default_factory=list)
    missing: list[str] = field(default_factory=list)

    def outcome(self) -> StepResult:
        """Turn the pass into a result: ``todo`` if anything is missing, else ``done``.

        Nothing created and nothing missing means the world was already complete.
        """
        if self.missing:
            return StepResult(StepState.TODO, "; ".join(self.missing))
        if self.done:
            return StepResult(StepState.DONE, "; ".join(self.done))
        return StepResult(StepState.SKIPPED, "the webhook and what was declared already exist")


class StripeStep:
    """Find or create the product, the price and the webhook of the project."""

    name = "stripe"

    def __init__(self, client: StripeClient, registry: SecretRegistry = SECRETS) -> None:
        self._client = client
        self._registry = registry

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Read Stripe and Vercel; nothing is created or written."""
        return await self._run(ctx, write=False)

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Create the product, the price and the webhook that are missing."""
        return await self._run(ctx, write=True)

    async def _run(self, ctx: ProvisioningContext, write: bool) -> StepResult:
        config = ctx.online.stripe
        if config is None:
            return StepResult(StepState.SKIPPED, "no stripe block declared")
        refus = self._refusal(config)
        if refus is not None:
            return refus
        if not await ctx.env_writer.has_env(SECRET_KEY_VARIABLE):
            return self._missing_site_key()
        secret_present = await ctx.env_writer.has_env(WEBHOOK_VARIABLE)
        if not self._client.configured:
            return self._without_key(ctx, secret_present)
        report = _Report()
        await self._product_and_price(ctx, config, write, report)
        return await self._webhook(ctx, config, secret_present, write, report)

    def _refusal(self, config: StripeConfig) -> Optional[StepResult]:
        """Refuse before any request when the key and the declared mode disagree."""
        if config.price_cents is not None and not config.product:
            return StepResult(StepState.FAILED, "price_cents needs a product name; nothing was sent")
        if not self._client.configured:
            return None
        mode = self._client.key_mode
        if mode == config.mode:
            return None
        if mode == "unknown":
            return StepResult(
                StepState.FAILED,
                "STRIPE_API_KEY is neither a test nor a live key; nothing was sent",
            )
        return StepResult(
            StepState.FAILED,
            f"STRIPE_API_KEY is a {mode} key but online.stripe.mode is '{config.mode}'; "
            "nothing was sent. Live mode is declared in agents.json, never implied",
        )

    @staticmethod
    def _missing_site_key() -> StepResult:
        return StepResult(
            StepState.NEEDS_HUMAN,
            f"{SECRET_KEY_VARIABLE} is not set in the Vercel project. Stripe cannot create "
            "an API key: create a restricted key for the site in the Stripe dashboard "
            f"(Developers > API keys) and add it to Vercel as {SECRET_KEY_VARIABLE}",
        )

    @staticmethod
    def _without_key(ctx: ProvisioningContext, secret_present: bool) -> StepResult:
        if secret_present:
            return StepResult(
                StepState.MANUAL,
                f"STRIPE_API_KEY is not set; {WEBHOOK_VARIABLE} is present in Vercel, Stripe was not checked",
            )
        return StepResult(
            StepState.NEEDS_HUMAN,
            "STRIPE_API_KEY is not set in the Tessera .env. Create the webhook of "
            f"'{ctx.project_id}' yourself and add {WEBHOOK_VARIABLE} to the Vercel project, "
            "or set a restricted key and relaunch",
        )

    async def _product_and_price(
        self, ctx: ProvisioningContext, config: StripeConfig, write: bool, report: _Report
    ) -> None:
        if not config.product:
            return
        produit = await self._client.find_product(ctx.project_id)
        if produit is None and not write:
            report.missing.append("product is missing")
        elif produit is None:
            produit = await self._client.create_product(config.product, ctx.project_id)
            report.done.append("product created")
        if config.price_cents is None:
            return
        cle = lookup_key(ctx.project_id)
        if await self._client.find_price(cle) is not None:
            return
        if produit is None or not write:
            report.missing.append("price is missing")
            return
        await self._client.create_price(produit, config.price_cents, CURRENCY, cle)
        report.done.append("price created")

    async def _webhook(
        self,
        ctx: ProvisioningContext,
        config: StripeConfig,
        secret_present: bool,
        write: bool,
        report: _Report,
    ) -> StepResult:
        url = f"https://{ctx.online.domain}{config.webhook_path}"
        existants = await self._client.find_webhooks(url)
        if existants and not secret_present:
            return self._existing_without_secret(url, existants)
        if secret_present and not existants:
            return self._secret_without_webhook(url)
        if not existants and not write:
            report.missing.append("webhook is missing")
        elif not existants:
            await self._create_webhook(ctx, config, url)
            report.done.append(f"webhook created, {WEBHOOK_VARIABLE} written to Vercel")
        return report.outcome()

    @staticmethod
    def _existing_without_secret(url: str, ids: list[str]) -> StepResult:
        return StepResult(
            StepState.NEEDS_HUMAN,
            f"Stripe webhook {', '.join(ids)} already exists for {url} but {WEBHOOK_VARIABLE} is "
            "missing in Vercel, and Stripe only shows the signing secret at creation. Reveal it "
            "in the Stripe dashboard (Developers > Webhooks) and add it to Vercel, or delete that "
            "webhook yourself and relaunch. Nothing was deleted",
        )

    @staticmethod
    def _secret_without_webhook(url: str) -> StepResult:
        return StepResult(
            StepState.NEEDS_HUMAN,
            f"{WEBHOOK_VARIABLE} is already set in Vercel but no Stripe webhook exists for {url}; "
            "a new one would hand out a secret that cannot replace it. Remove the variable in "
            "Vercel and relaunch, or create the webhook yourself",
        )

    async def _create_webhook(self, ctx: ProvisioningContext, config: StripeConfig, url: str) -> None:
        cree = await self._client.create_webhook(url, config.events)
        # Inscrit avant l'envoi : une erreur ou un log ne doit pas pouvoir le citer.
        self._registry.register(cree.secret)
        await ctx.env_writer.set_env(WEBHOOK_VARIABLE, cree.secret)
        ctx.changed_env.add(WEBHOOK_VARIABLE)
        _logger.info("stripe_webhook_created", extra={"project": ctx.project_id})
