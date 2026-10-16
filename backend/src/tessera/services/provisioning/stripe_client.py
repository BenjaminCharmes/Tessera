"""Stripe REST client — ADR-053, ticket-470.

Written against the Stripe API reference (https://docs.stripe.com/api), pages:

- Authentication (https://docs.stripe.com/api/authentication): bearer key, and
  the ``sk_``/``rk_`` + ``test_``/``live_`` prefix that tells the mode;
- Restricted keys (https://docs.stripe.com/keys#limit-access): the key of
  Tessera only needs write access to products, prices and webhook endpoints;
- Products (https://docs.stripe.com/api/products/list and ``/create``): the list
  is paged with ``starting_after`` and each product carries its ``metadata``;
- Prices (https://docs.stripe.com/api/prices/list and ``/create``): ``lookup_keys[]``
  filters the list, ``unit_amount`` and ``currency`` are immutable once created;
- Webhook endpoints (https://docs.stripe.com/api/webhook_endpoints/create and
  ``/list``): ``enabled_events[]`` on creation, and the signing ``secret`` is
  returned by the creation response only.

Stripe takes form-encoded bodies. The key and the signing secret are never
logged: the request log carries the method, the path and the status, and a
failure only carries the HTTP status and the API's error code. Nothing here
updates or deletes.
"""
from dataclasses import dataclass, field
from typing import Literal, Optional

import httpx

from tessera.config import Settings
from tessera.services.provisioning.errors import ServiceError
from tessera.services.provisioning.jsonview import as_dict, as_list, as_str
from tessera.utils.logger import get_logger

SERVICE = "stripe"
PROJECT_METADATA = "tessera_project"
_BASE_URL = "https://api.stripe.com"
_TIMEOUT_S = 30.0
_PAGE_SIZE = 100
_MAX_PAGES = 10

KeyMode = Literal["test", "live", "unknown"]
Form = dict[str, str | list[str]]
#: Le même type que `httpx` : une liste est invariante, `list[tuple[str, str]]` serait refusée.
Query = list[tuple[str, str | int | float | bool | None]]

_logger = get_logger(__name__)


@dataclass(frozen=True)
class StripePrice:
    """An existing price; only read, a Stripe price is immutable."""

    id: str
    unit_amount: int


@dataclass(frozen=True)
class StripeWebhook:
    """A webhook just created; the signing secret comes with the creation only."""

    id: str
    # Hors du repr : un traceback ou un log de dataclass ne doit pas citer le secret.
    secret: str = field(default="", repr=False)


class StripeClient:
    """The few Stripe calls the step needs; nothing updates, nothing deletes."""

    def __init__(
        self, api_key: str, transport: Optional[httpx.AsyncBaseTransport] = None
    ) -> None:
        self._api_key = api_key
        self._transport = transport

    @classmethod
    def from_settings(
        cls, settings: Settings, transport: Optional[httpx.AsyncBaseTransport] = None
    ) -> "StripeClient":
        """Build the client from the key of ``Settings``."""
        return cls(settings.stripe_api_key.get_secret_value(), transport)

    @property
    def configured(self) -> bool:
        """Tell whether a key is set; without one no request is ever sent."""
        return bool(self._api_key.strip())

    @property
    def key_mode(self) -> KeyMode:
        """Read the mode off the key prefix, without any request."""
        cle = self._api_key.strip()
        if cle.startswith(("sk_live_", "rk_live_")):
            return "live"
        if cle.startswith(("sk_test_", "rk_test_")):
            return "test"
        return "unknown"

    async def _send(
        self, method: str, path: str, params: Optional[Query] = None, form: Optional[Form] = None
    ) -> object:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        try:
            async with httpx.AsyncClient(
                base_url=_BASE_URL, transport=self._transport, timeout=_TIMEOUT_S
            ) as http:
                reponse = await http.request(
                    method, path, params=params, data=form, headers=headers
                )
        except httpx.HTTPError:
            # Le message d'une erreur réseau peut citer la requête : on le coupe.
            raise ServiceError(SERVICE, 0, "unreachable") from None
        _logger.info(
            "stripe_request",
            extra={"method": method, "path": path, "status": reponse.status_code},
        )
        if reponse.status_code >= 400:
            raise ServiceError.from_response(SERVICE, reponse.status_code, reponse.content)
        try:
            return reponse.json()
        except ValueError:
            raise ServiceError(SERVICE, reponse.status_code, "unreadable") from None

    async def _list_all(self, path: str, params: Query) -> list[dict[str, object]]:
        elements: list[dict[str, object]] = []
        apres = ""
        for _ in range(_MAX_PAGES):
            requete = [*params, ("limit", str(_PAGE_SIZE))]
            if apres:
                requete.append(("starting_after", apres))
            corps = as_dict(await self._send("GET", path, params=requete))
            page = [as_dict(e) for e in as_list(corps.get("data"))]
            elements += page
            apres = as_str(page[-1].get("id")) if page else ""
            if corps.get("has_more") is not True or not apres:
                break
        return elements

    async def find_product(self, project_id: str) -> Optional[str]:
        """Return the id of the active product tagged with the project, if any."""
        produits = await self._list_all("/v1/products", [("active", "true")])
        for produit in produits:
            if as_dict(produit.get("metadata")).get(PROJECT_METADATA) == project_id:
                return as_str(produit.get("id")) or None
        return None

    async def create_product(self, name: str, project_id: str) -> str:
        """Create a product tagged with the project."""
        form: Form = {"name": name, f"metadata[{PROJECT_METADATA}]": project_id}
        identifiant = as_str(as_dict(await self._send("POST", "/v1/products", form=form)).get("id"))
        if not identifiant:
            raise ServiceError(SERVICE, 200, "unreadable")
        return identifiant

    async def find_price(self, lookup_key: str) -> Optional[StripePrice]:
        """Return the price carrying this ``lookup_key``, ``None`` when there is none."""
        params: Query = [("lookup_keys[]", lookup_key), ("limit", "1")]
        corps = as_dict(await self._send("GET", "/v1/prices", params=params))
        prix = as_dict(next(iter(as_list(corps.get("data"))), None))
        identifiant = as_str(prix.get("id"))
        montant = prix.get("unit_amount")
        if not identifiant:
            return None
        return StripePrice(identifiant, montant if isinstance(montant, int) else 0)

    async def create_price(
        self, product_id: str, unit_amount: int, currency: str, lookup_key: str
    ) -> None:
        """Create a one-time price under a product."""
        form: Form = {
            "product": product_id,
            "unit_amount": str(unit_amount),
            "currency": currency,
            "lookup_key": lookup_key,
        }
        await self._send("POST", "/v1/prices", form=form)

    async def find_webhooks(self, url: str) -> list[str]:
        """Return the ids of every webhook endpoint registered at exactly ``url``."""
        points = await self._list_all("/v1/webhook_endpoints", [])
        ids = [as_str(p.get("id")) for p in points if p.get("url") == url]
        return [identifiant for identifiant in ids if identifiant]

    async def create_webhook(self, url: str, events: list[str]) -> StripeWebhook:
        """Create a webhook endpoint; its signing secret is only returned here."""
        form: Form = {"url": url, "enabled_events[]": list(events)}
        corps = as_dict(await self._send("POST", "/v1/webhook_endpoints", form=form))
        identifiant, secret = as_str(corps.get("id")), as_str(corps.get("secret"))
        if not (identifiant and secret):
            raise ServiceError(SERVICE, 200, "unreadable")
        return StripeWebhook(identifiant, secret)
