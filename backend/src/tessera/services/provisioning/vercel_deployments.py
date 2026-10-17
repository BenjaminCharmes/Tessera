"""A Vercel deployment as the provisioning steps read it — ticket-489."""
from dataclasses import dataclass
from typing import Optional

from tessera.services.provisioning.jsonview import as_dict, as_str

#: États Vercel d'un déploiement qui n'a pas fini de construire.
IN_PROGRESS_STATES: frozenset[str] = frozenset({"QUEUED", "INITIALIZING", "BUILDING"})


@dataclass(frozen=True)
class VercelDeployment:
    """The id, the state and the error code of one deployment; never its build log."""

    id: str
    state: str
    error_code: str = ""

    @property
    def failed(self) -> bool:
        """Tell whether the build ended in ``ERROR``."""
        return self.state == "ERROR"

    @property
    def canceled(self) -> bool:
        """Tell whether the deployment was canceled, so it serves nothing."""
        return self.state == "CANCELED"

    @property
    def in_progress(self) -> bool:
        """Tell whether the build is still queued or running."""
        return self.state in IN_PROGRESS_STATES

    @property
    def ready(self) -> bool:
        """Tell whether the deployment is live."""
        return self.state == "READY"


def deployment_from(raw: object) -> Optional[VercelDeployment]:
    """Read a deployment from a list entry or a creation response, ``None`` without an id."""
    corps = as_dict(raw)
    identifiant = as_str(corps.get("uid")) or as_str(corps.get("id"))
    if not identifiant:
        return None
    etat = as_str(corps.get("readyState")) or as_str(corps.get("state"))
    return VercelDeployment(identifiant, etat.upper(), as_str(corps.get("errorCode")))
