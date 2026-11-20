"""What a project declares about its supervisor — ticket-852.

The `pipeline.superviseur` key of `agents.json` (ADR-080). Only a human writes
it (ADR-027): absent, the supervisor sorts and reports but accepts and
dismisses nothing.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: Hard ceiling of the daily spend, in USD. A declared budget above it is
#: refused, not clamped: money is the human's call (ADR-080).
BUDGET_JOUR_PLAFOND_USD = 20.0
BUDGET_JOUR_DEFAUT_USD = 2.0


class ConfigSuperviseur(BaseModel):
    """The validated `pipeline.superviseur` declaration of a project."""

    # Une clé inconnue est une faute de frappe sur une délégation : refusée.
    model_config = ConfigDict(frozen=True, extra="forbid")

    #: What the supervisor may decide on its own. Empty: nothing.
    delegation: list[Literal["lecons", "regles"]] = Field(default_factory=list)
    budget_jour_usd: float = Field(
        default=BUDGET_JOUR_DEFAUT_USD, gt=0, le=BUDGET_JOUR_PLAFOND_USD
    )
    #: May reopen a queue cut by the infrastructure.
    relance_file: bool = False
