"""Vercel REST client and the env writer built on it — ADR-053, ticket-466.

Written against the Vercel REST API reference
(https://vercel.com/docs/rest-api/reference), sections:

- Projects: retrieve a project (``GET /v9/projects/{idOrName}``), create one
  (``POST /v11/projects``, ``gitRepository`` links the repository);
- Domains: read a project domain (``GET /v9/projects/{id}/domains/{domain}``),
  add one (``POST /v10/projects/{id}/domains``), read its DNS recommendation
  (``GET /v6/domains/{domain}/config``);
- Environment variables: list (``GET /v10/projects/{id}/env``) and create
  (``POST /v10/projects/{id}/env``). A ``sensitive`` variable is never returned
  with its value, so only its name is known — hence "write only if absent";
- Deployments: list (``GET /v6/deployments``) and redeploy
  (``POST /v13/deployments`` with ``deploymentId``).

Every call goes through `httpx`. The ``Authorization`` header is built per
request and appears in no log and no error: a failure only carries the HTTP
status and the API's error code (`ServiceError`).
"""
from typing import Optional
from urllib.parse import quote

import httpx

from tessera.config import Settings
from tessera.services.provisioning.errors import ServiceError
from tessera.services.provisioning.jsonview import as_dict, as_list, as_str
from tessera.services.provisioning.steps import DnsRecord
from tessera.services.provisioning.vercel_dns import VercelDomain, domain_from, records_from_config
from tessera.utils.logger import get_logger

SERVICE = "vercel"
PUBLIC_PREFIX = "NEXT_PUBLIC_"
_BASE_URL = "https://api.vercel.com"
_TIMEOUT_S = 30.0

_logger = get_logger(__name__)


def vercel_name(project_id: str) -> str:
    """Return the Vercel project name for a Tessera project (lowercase only)."""
    return project_id.lower()


class VercelClient:
    """The few Vercel calls the provisioning steps need; nothing deletes."""

    def __init__(
        self,
        token: str,
        team_id: str = "",
        transport: Optional[httpx.AsyncBaseTransport] = None,
    ) -> None:
        self._token = token
        self._team_id = team_id
        self._transport = transport

    @classmethod
    def from_settings(
        cls, settings: Settings, transport: Optional[httpx.AsyncBaseTransport] = None
    ) -> "VercelClient":
        """Build the client from the token and team of ``Settings``."""
        return cls(settings.vercel_token.get_secret_value(), settings.vercel_team_id, transport)

    @property
    def configured(self) -> bool:
        """Tell whether a token is set; without one no request is ever sent."""
        return bool(self._token.strip())

    async def _send(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, str]] = None,
        body: Optional[dict[str, object]] = None,
    ) -> httpx.Response:
        query = dict(params or {})
        if self._team_id:
            query["teamId"] = self._team_id
        headers = {"Authorization": f"Bearer {self._token}"}
        try:
            async with httpx.AsyncClient(
                base_url=_BASE_URL, transport=self._transport, timeout=_TIMEOUT_S
            ) as http:
                reponse = await http.request(
                    method, path, params=query, json=body, headers=headers
                )
        except httpx.HTTPError:
            # Le message d'une erreur réseau peut citer la requête : on le coupe.
            raise ServiceError(SERVICE, 0, "unreachable") from None
        _logger.info(
            "vercel_request",
            extra={"method": method, "path": path, "status": reponse.status_code},
        )
        if reponse.status_code >= 400:
            raise ServiceError.from_response(SERVICE, reponse.status_code, reponse.content)
        return reponse

    async def _send_or_absent(
        self, method: str, path: str, params: Optional[dict[str, str]] = None
    ) -> Optional[httpx.Response]:
        try:
            return await self._send(method, path, params)
        except ServiceError as erreur:
            if erreur.status == 404:
                return None
            raise

    async def get_project(self, name: str) -> Optional[dict[str, object]]:
        """Return the project called ``name``, ``None`` when it does not exist."""
        reponse = await self._send_or_absent("GET", f"/v9/projects/{quote(name, safe='')}")
        return None if reponse is None else as_dict(reponse.json())

    async def create_project(self, name: str, repo: Optional[str]) -> dict[str, object]:
        """Create a project, linked to the GitHub repository ``owner/repo`` if any."""
        corps: dict[str, object] = {"name": name}
        if repo:
            corps["gitRepository"] = {"type": "github", "repo": repo}
        reponse = await self._send("POST", "/v11/projects", body=corps)
        return as_dict(reponse.json())

    async def get_domain(self, project: str, domain: str) -> Optional[VercelDomain]:
        """Return the domain as attached to the project, ``None`` when it is not."""
        chemin = f"/v9/projects/{quote(project, safe='')}/domains/{quote(domain, safe='')}"
        reponse = await self._send_or_absent("GET", chemin)
        return None if reponse is None else domain_from(domain, as_dict(reponse.json()))

    async def add_domain(self, project: str, domain: str) -> VercelDomain:
        """Attach a domain to the project."""
        chemin = f"/v10/projects/{quote(project, safe='')}/domains"
        reponse = await self._send("POST", chemin, body={"name": domain})
        return domain_from(domain, as_dict(reponse.json()))

    async def domain_config(self, domain: str) -> list[DnsRecord]:
        """Return the A or CNAME record Vercel wants, empty once it is correct."""
        reponse = await self._send("GET", f"/v6/domains/{quote(domain, safe='')}/config")
        corps = as_dict(reponse.json())
        if corps.get("misconfigured") is not True:
            return []
        return records_from_config(domain, corps)

    async def list_env_names(self, project: str) -> set[str]:
        """Return the names of the project variables; values are never read."""
        reponse = await self._send_or_absent(
            "GET", f"/v10/projects/{quote(project, safe='')}/env"
        )
        if reponse is None:
            return set()
        envs = as_list(as_dict(reponse.json()).get("envs"))
        return {as_str(as_dict(env).get("key")) for env in envs} - {""}

    async def create_env(self, project: str, name: str, value: str, sensitive: bool) -> None:
        """Create one variable for production and preview."""
        corps: dict[str, object] = {
            "key": name,
            "value": value,
            "type": "sensitive" if sensitive else "plain",
            "target": ["production", "preview"],
        }
        await self._send("POST", f"/v10/projects/{quote(project, safe='')}/env", body=corps)

    async def latest_production_deployment(self, project_id: str) -> Optional[str]:
        """Return the id of the newest ready production deployment, if any."""
        params = {"projectId": project_id, "target": "production", "state": "READY", "limit": "1"}
        reponse = await self._send("GET", "/v6/deployments", params=params)
        premier = as_dict(next(iter(as_list(as_dict(reponse.json()).get("deployments"))), None))
        return as_str(premier.get("uid")) or None

    async def redeploy(self, project: str, deployment_id: str) -> None:
        """Redeploy a deployment to production."""
        corps: dict[str, object] = {
            "name": project,
            "deploymentId": deployment_id,
            "target": "production",
        }
        await self._send("POST", "/v13/deployments", params={"forceNew": "1"}, body=corps)


class VercelEnvWriter:
    """`EnvWriter` over the Vercel project variables; never overwrites."""

    def __init__(self, client: VercelClient, project_id: str) -> None:
        self._client = client
        self._project = vercel_name(project_id)

    async def has_env(self, name: str) -> bool:
        """Tell whether the variable exists; its value is never read."""
        return name in await self._client.list_env_names(self._project)

    async def set_env(self, name: str, value: str) -> None:
        """Write a variable that is absent; an existing one is left untouched."""
        if await self.has_env(name):
            return
        sensitive = not name.startswith(PUBLIC_PREFIX)
        await self._client.create_env(self._project, name, value, sensitive)
        _logger.info("vercel_env_written", extra={"project": self._project, "variable": name})
