"""Resend REST client — ADR-053, ticket-468.

Written against the Resend API reference (https://resend.com/docs/api-reference),
pages:

- Domains: list (``GET /domains``), create (``POST /domains``, the response holds
  the DNS ``records`` to publish), retrieve (``GET /domains/{id}``) and verify
  (``POST /domains/{id}/verify``). Verification is asynchronous: a domain stays
  ``pending`` while DNS propagates and ends ``verified`` or ``failed``;
- API keys: list (``GET /api-keys``, names only) and create (``POST /api-keys``
  with ``permission: sending_access`` and ``domain_id``). The token is returned
  once, by the creation call, and can never be read again.

Every call goes through `httpx`. The ``Authorization`` header is built per
request and appears in no log and no error: a failure only carries the HTTP
status and the API's error code (`ServiceError`). Nothing deletes.
"""
from typing import Optional
from urllib.parse import quote

import httpx

from tessera.config import Settings
from tessera.services.provisioning.errors import ServiceError
from tessera.services.provisioning.jsonview import as_dict, as_list, as_str
from tessera.services.provisioning.resend_records import ResendDomain, domain_from
from tessera.utils.logger import get_logger

SERVICE = "resend"
_BASE_URL = "https://api.resend.com"
_TIMEOUT_S = 30.0

_logger = get_logger(__name__)


class ResendClient:
    """The few Resend calls the provisioning steps need."""

    def __init__(
        self, token: str, transport: Optional[httpx.AsyncBaseTransport] = None
    ) -> None:
        self._token = token
        self._transport = transport

    @classmethod
    def from_settings(
        cls, settings: Settings, transport: Optional[httpx.AsyncBaseTransport] = None
    ) -> "ResendClient":
        """Build the client from the Resend key of ``Settings``."""
        return cls(settings.resend_api_key.get_secret_value(), transport)

    @property
    def configured(self) -> bool:
        """Tell whether a key is set; without one no request is ever sent."""
        return bool(self._token.strip())

    async def _send(
        self, method: str, path: str, body: Optional[dict[str, object]] = None
    ) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with httpx.AsyncClient(
                base_url=_BASE_URL, transport=self._transport, timeout=_TIMEOUT_S
            ) as http:
                reponse = await http.request(method, path, json=body, headers=headers)
        except httpx.HTTPError:
            # Le message d'une erreur réseau peut citer la requête : on le coupe.
            raise ServiceError(SERVICE, 0, "unreachable") from None
        _logger.info(
            "resend_request",
            extra={"method": method, "path": path, "status": reponse.status_code},
        )
        if reponse.status_code >= 400:
            raise ServiceError.from_response(SERVICE, reponse.status_code, reponse.content)
        return reponse

    async def find_domain(self, name: str) -> Optional[ResendDomain]:
        """Return the domain called ``name`` (without its records), if any."""
        reponse = await self._send("GET", "/domains")
        for brut in as_list(as_dict(reponse.json()).get("data")):
            domaine = domain_from(as_dict(brut))
            if domaine.name == name:
                return domaine
        return None

    async def create_domain(self, name: str) -> ResendDomain:
        """Create a sending domain; the response carries its DNS records."""
        reponse = await self._send("POST", "/domains", {"name": name})
        return domain_from({"name": name, **as_dict(reponse.json())})

    async def get_domain(self, domain_id: str) -> ResendDomain:
        """Read a domain with its DNS records and its current status."""
        reponse = await self._send("GET", f"/domains/{quote(domain_id, safe='')}")
        return domain_from(as_dict(reponse.json()))

    async def verify_domain(self, domain_id: str) -> None:
        """Ask Resend to check the DNS records; the outcome is read afterwards."""
        await self._send("POST", f"/domains/{quote(domain_id, safe='')}/verify")

    async def has_api_key(self, name: str) -> bool:
        """Tell whether a key with this name exists; its token is not readable."""
        reponse = await self._send("GET", "/api-keys")
        cles = as_list(as_dict(reponse.json()).get("data"))
        return any(as_str(as_dict(cle).get("name")) == name for cle in cles)

    async def create_sending_key(self, name: str, domain_id: str) -> str:
        """Create a key limited to sending from one domain; return its token."""
        corps: dict[str, object] = {
            "name": name,
            "permission": "sending_access",
            "domain_id": domain_id,
        }
        reponse = await self._send("POST", "/api-keys", corps)
        token = as_str(as_dict(reponse.json()).get("token"))
        if not token:
            # La clé existe désormais sans valeur : le prochain passage la nommera.
            raise ServiceError(SERVICE, reponse.status_code, "missing_token")
        return token
