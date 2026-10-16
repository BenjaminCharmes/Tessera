"""Cloudflare REST client — ADR-053, ticket-469.

Written against the Cloudflare API reference
(https://developers.cloudflare.com/api/), sections:

- Zones, list: https://developers.cloudflare.com/api/resources/zones/methods/list/
  (``GET /zones?name=``, the answer is ``{"result": [{"id", "name"}]}``);
- DNS records, list:
  https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/list/
  (``GET /zones/{zone_id}/dns_records?type=&name=&page=&per_page=``, paginated
  through ``result_info.total_pages``);
- DNS records, create:
  https://developers.cloudflare.com/api/resources/dns/subresources/records/methods/create/
  (``POST /zones/{zone_id}/dns_records`` with ``type``, ``name``, ``content``,
  ``ttl`` (1 is automatic) and ``proxied``).

The records Tessera creates point to Vercel and are DNS-only, never proxied.
The client has no update and no delete call: it cannot overwrite a record.
The token never appears in a log or an error, which only carry the HTTP status
and the API's error code.
"""
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import httpx

from tessera.config import Settings
from tessera.services.provisioning.errors import ServiceError
from tessera.services.provisioning.jsonview import as_dict, as_list, as_str
from tessera.services.provisioning.steps import DnsRecord
from tessera.utils.logger import get_logger

SERVICE = "cloudflare"
_BASE_URL = "https://api.cloudflare.com/client/v4"
_TIMEOUT_S = 30.0
_PAGE_SIZE = 100
_MAX_PAGES = 10
#: Cloudflare reads a TTL of 1 as "automatic".
_TTL_AUTO = 1

_logger = get_logger(__name__)


@dataclass(frozen=True)
class CloudflareZone:
    """A zone of the account the token can reach."""

    id: str
    name: str


class CloudflareClient:
    """The few Cloudflare calls the DNS step needs; nothing updates, nothing deletes."""

    def __init__(
        self, api_token: str, transport: Optional[httpx.AsyncBaseTransport] = None
    ) -> None:
        self._api_token = api_token
        self._transport = transport

    @classmethod
    def from_settings(
        cls, settings: Settings, transport: Optional[httpx.AsyncBaseTransport] = None
    ) -> "CloudflareClient":
        """Build the client from the token of ``Settings``."""
        return cls(settings.cloudflare_api_token.get_secret_value(), transport)

    @property
    def configured(self) -> bool:
        """Tell whether a token is set; without one no request is ever sent."""
        return bool(self._api_token.strip())

    async def _send(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, str]] = None,
        body: Optional[dict[str, object]] = None,
    ) -> dict[str, object]:
        headers = {"Authorization": f"Bearer {self._api_token}"}
        try:
            async with httpx.AsyncClient(
                base_url=_BASE_URL, transport=self._transport, timeout=_TIMEOUT_S
            ) as http:
                reponse = await http.request(
                    method, path, params=params, json=body, headers=headers
                )
        except httpx.HTTPError:
            # Le message d'une erreur réseau peut citer la requête : on le coupe.
            raise ServiceError(SERVICE, 0, "unreachable") from None
        _logger.info(
            "cloudflare_request",
            extra={"method": method, "path": path, "status": reponse.status_code},
        )
        if reponse.status_code >= 400:
            raise ServiceError.from_response(SERVICE, reponse.status_code, reponse.content)
        try:
            return as_dict(reponse.json())
        except ValueError:
            raise ServiceError(SERVICE, reponse.status_code, "unreadable") from None

    async def find_zones(self, name: str) -> list[CloudflareZone]:
        """Return the zones named exactly ``name`` (usually 0 or 1)."""
        corps = await self._send("GET", "/zones", params={"name": name})
        zones = [as_dict(z) for z in as_list(corps.get("result"))]
        trouvees = [CloudflareZone(as_str(z.get("id")), as_str(z.get("name"))) for z in zones]
        return [z for z in trouvees if z.id and z.name.lower() == name]

    async def list_records(self, zone_id: str, record_type: str, name: str) -> list[DnsRecord]:
        """Return the records of one type and name; the name is checked here too."""
        chemin = f"/zones/{quote(zone_id, safe='')}/dns_records"
        trouves: list[DnsRecord] = []
        for page in range(1, _MAX_PAGES + 1):
            params = {
                "type": record_type,
                "name": name,
                "page": str(page),
                "per_page": str(_PAGE_SIZE),
            }
            corps = await self._send("GET", chemin, params=params)
            trouves += _records_of(corps)
            total = as_dict(corps.get("result_info")).get("total_pages")
            if not isinstance(total, int) or page >= total:
                break
        return trouves

    async def create_record(self, zone_id: str, record: DnsRecord) -> None:
        """Create one record, DNS-only (not proxied)."""
        corps: dict[str, object] = {
            "type": record.type,
            "name": record.name,
            "content": record.content,
            "ttl": _TTL_AUTO,
            "proxied": False,
        }
        await self._send("POST", f"/zones/{quote(zone_id, safe='')}/dns_records", body=corps)


def _records_of(corps: dict[str, object]) -> list[DnsRecord]:
    lus: list[DnsRecord] = []
    for brut in as_list(corps.get("result")):
        item = as_dict(brut)
        genre, nom = as_str(item.get("type")), as_str(item.get("name"))
        if genre and nom:
            lus.append(DnsRecord(genre, nom, as_str(item.get("content"))))
    return lus
