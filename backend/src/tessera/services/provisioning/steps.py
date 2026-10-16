"""The contract of a provisioning step — ticket-465."""
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional, Protocol

from tessera.services.provisioning.online_config import OnlineConfig


class StepState(StrEnum):
    """What a step found or did."""

    #: Read-only run: something is missing and nothing was written.
    TODO = "todo"
    DONE = "done"
    #: The world is already complete for this step.
    SKIPPED = "skipped"
    #: Created, but the service has not finished (DNS propagation, say).
    PENDING = "pending"
    #: The user must do it, the detail says how.
    MANUAL = "manual"
    NEEDS_HUMAN = "needs_human"
    FAILED = "failed"


#: States that stop the steps after them.
STOPPING_STATES: frozenset[StepState] = frozenset(
    {StepState.FAILED, StepState.NEEDS_HUMAN}
)


@dataclass(frozen=True)
class StepResult:
    """Outcome of one step; ``detail`` never holds a secret value."""

    state: StepState
    detail: str = ""


@dataclass(frozen=True)
class DnsRecord:
    """A public DNS record a step asks the DNS step to publish."""

    type: str
    name: str
    content: str
    #: Only meaningful for MX records.
    priority: Optional[int] = None


class EnvWriter(Protocol):
    """Where a secret received from one API goes to reach another API."""

    async def has_env(self, name: str) -> bool:
        """Tell whether the variable already exists (its value is never read)."""
        ...

    async def set_env(self, name: str, value: str) -> None:
        """Write a variable that does not exist yet; never overwrite."""
        ...


@dataclass
class ProvisioningContext:
    """What the steps of one run share."""

    project_id: str
    online: OnlineConfig
    env_writer: EnvWriter
    #: 'owner/repo' of the project, ``None`` when it has no remote.
    github_remote: Optional[str] = None
    wanted_dns: list[DnsRecord] = field(default_factory=list)
    changed_env: set[str] = field(default_factory=set)
    dns_published: bool = False


class ProvisioningStep(Protocol):
    """One service, one concern. ``inspect`` reads, ``apply`` creates the missing."""

    name: str

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Read the world; must not write anything."""
        ...

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Create what is missing and nothing else."""
        ...
