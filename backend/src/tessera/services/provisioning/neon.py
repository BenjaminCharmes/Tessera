"""Neon REST client — ADR-053, ticket-467.

Written against the Neon API reference (https://api-docs.neon.tech/reference),
sections:

- Projects: list with a name filter (``GET /projects?search=&limit=&cursor=``,
  ``search`` is a substring match, so the exact name is checked here) and create
  (``POST /projects``, the response carries ``connection_uris``);
- Branches: list (``GET /projects/{id}/branches``, the default one is flagged);
- Databases: list a branch's databases
  (``GET /projects/{id}/branches/{branch}/databases``, each has an ``owner_name``);
- Connection URI: ``GET /projects/{id}/connection_uri`` (``database_name`` and
  ``role_name`` are required, the answer is ``{"uri": ...}``).

The connection URI holds the database password. It is returned to the caller
and never logged: the request log carries the method, the path and the status,
and a failure carries the HTTP status, the API's error code and its ``message``
field (URLs and the key removed, bounded) — never a header.

An account attached to an organization needs ``org_id`` on the project calls
(ticket-499): it comes from ``NEON_ORG_ID``, or from
``GET /users/me/organizations`` when the account has exactly one.
"""
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import quote

import httpx

from tessera.config import Settings
from tessera.services.provisioning.errors import ServiceError
from tessera.services.provisioning.jsonview import as_dict, as_list, as_str
from tessera.utils.logger import get_logger

SERVICE = "neon"
_BASE_URL = "https://console.neon.tech/api/v2"
_TIMEOUT_S = 30.0
_PAGE_SIZE = 100
_MAX_PAGES = 10

_logger = get_logger(__name__)


@dataclass(frozen=True)
class NeonProject:
    """A project just created; ``uri`` is empty when the API did not return one."""

    id: str
    # Hors du repr : un traceback ou un log de dataclass ne doit pas citer le mot de passe.
    uri: str = field(default="", repr=False)


class AmbiguousOrganization(Exception):
    """The account has several organizations and ``NEON_ORG_ID`` does not pick one."""


class NeonClient:
    """The few Neon calls the database step needs; nothing deletes."""

    def __init__(
        self,
        api_key: str,
        transport: Optional[httpx.AsyncBaseTransport] = None,
        org_id: str = "",
    ) -> None:
        self._api_key = api_key
        self._transport = transport
        # None : pas encore résolu ; "" : compte personnel, aucun org_id à envoyer.
        self._org_id: Optional[str] = org_id.strip() or None

    @classmethod
    def from_settings(
        cls, settings: Settings, transport: Optional[httpx.AsyncBaseTransport] = None
    ) -> "NeonClient":
        """Build the client from the key and the organization of ``Settings``."""
        return cls(settings.neon_api_key.get_secret_value(), transport, settings.neon_org_id)

    async def organization(self) -> str:
        """Return the ``org_id`` to send (empty for a personal account).

        Raises ``AmbiguousOrganization`` when the account has several and none
        is configured. The answer is read once per client.
        """
        if self._org_id is not None:
            return self._org_id
        corps = as_dict(await self._send("GET", "/users/me/organizations"))
        ids = [as_str(as_dict(o).get("id")) for o in as_list(corps.get("organizations"))]
        ids = [identifiant for identifiant in ids if identifiant]
        if len(ids) > 1:
            raise AmbiguousOrganization
        self._org_id = ids[0] if ids else ""
        return self._org_id

    @property
    def configured(self) -> bool:
        """Tell whether a key is set; without one no request is ever sent."""
        return bool(self._api_key.strip())

    async def _send(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, str]] = None,
        body: Optional[dict[str, object]] = None,
    ) -> object:
        headers = {"Authorization": f"Bearer {self._api_key}"}
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
            "neon_request",
            extra={"method": method, "path": path, "status": reponse.status_code},
        )
        if reponse.status_code >= 400:
            raise ServiceError.from_response(
                SERVICE,
                reponse.status_code,
                reponse.content,
                with_reason=True,
                redact=(self._api_key,),
            )
        try:
            return reponse.json()
        except ValueError:
            raise ServiceError(SERVICE, reponse.status_code, "unreadable") from None

    async def find_projects(self, name: str) -> list[str]:
        """Return the ids of every project named exactly ``name`` (usually 0 or 1)."""
        trouves: list[str] = []
        curseur = ""
        org_id = await self.organization()
        for _ in range(_MAX_PAGES):
            params = {"search": name, "limit": str(_PAGE_SIZE)}
            if org_id:
                params["org_id"] = org_id
            if curseur:
                params["cursor"] = curseur
            corps = as_dict(await self._send("GET", "/projects", params=params))
            page = [as_dict(p) for p in as_list(corps.get("projects"))]
            trouves += [as_str(p.get("id")) for p in page if p.get("name") == name]
            pagination = as_dict(corps.get("pagination"))
            curseur = as_str(pagination.get("next")) or as_str(pagination.get("cursor"))
            if len(page) < _PAGE_SIZE or not curseur:
                break
        return [identifiant for identifiant in trouves if identifiant]

    async def create_project(self, name: str) -> NeonProject:
        """Create a project; its connection URI comes back with it when available."""
        projet: dict[str, object] = {"name": name}
        org_id = await self.organization()
        if org_id:
            projet["org_id"] = org_id
        corps = as_dict(await self._send("POST", "/projects", body={"project": projet}))
        identifiant = as_str(as_dict(corps.get("project")).get("id"))
        if not identifiant:
            raise ServiceError(SERVICE, 200, "unreadable")
        premiere = as_dict(next(iter(as_list(corps.get("connection_uris"))), None))
        return NeonProject(identifiant, as_str(premiere.get("connection_uri")))

    async def connection_uri(self, project_id: str) -> str:
        """Read the connection URI of the default branch's first database."""
        projet = quote(project_id, safe="")
        branche = await self._default_branch(projet)
        chemin_bases = f"/projects/{projet}/branches/{quote(branche, safe='')}/databases"
        bases = as_dict(await self._send("GET", chemin_bases))
        premiere = as_dict(next(iter(as_list(bases.get("databases"))), None))
        base, role = as_str(premiere.get("name")), as_str(premiere.get("owner_name"))
        if not (base and role):
            raise ServiceError(SERVICE, 200, "no_database")
        params = {"branch_id": branche, "database_name": base, "role_name": role}
        chemin_uri = f"/projects/{projet}/connection_uri"
        corps = as_dict(await self._send("GET", chemin_uri, params=params))
        uri = as_str(corps.get("uri"))
        if not uri:
            raise ServiceError(SERVICE, 200, "unreadable")
        return uri

    async def _default_branch(self, projet: str) -> str:
        corps = as_dict(await self._send("GET", f"/projects/{projet}/branches"))
        branches = [as_dict(b) for b in as_list(corps.get("branches"))]
        defaut = next((b for b in branches if b.get("default") is True), None)
        identifiant = as_str((defaut or (branches[0] if branches else {})).get("id"))
        if not identifiant:
            raise ServiceError(SERVICE, 200, "no_branch")
        return identifiant
