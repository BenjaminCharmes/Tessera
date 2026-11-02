"""What a project says about going online, for its card — ticket-472.

A raw read of the ``online`` block of ``agents.json``, on purpose: the validated
reader lives in ``services/provisioning``, which only the provisioning router may
import (ADR-053). The card needs to know whether to offer the button, and what
to name in the confirmation; an invalid block is still refused, with its reason,
by ``POST …/provision``.
"""
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel

from tessera.services.manifeste import lire_objet

StripeMode = Literal["test", "live"]


class OnlineDeclaration(BaseModel):
    """The part of the ``online`` block the confirmation names."""

    declared: bool = False
    domain: Optional[str] = None
    stripe_mode: Optional[StripeMode] = None


def _stripe_mode(bloc: dict[str, object]) -> Optional[StripeMode]:
    stripe = bloc.get("stripe")
    if not isinstance(stripe, dict):
        return None
    # Le mode réel ne s'implique jamais : tout ce qui n'est pas « live » se lit « test ».
    return "live" if stripe.get("mode") == "live" else "test"


def read_online_declaration(project_path: Path) -> OnlineDeclaration:
    """Read the ``online`` block of a project; undeclared when absent or unreadable."""
    bloc = lire_objet(project_path, "online")
    if bloc is None:
        return OnlineDeclaration()
    domain = bloc.get("domain")
    return OnlineDeclaration(
        declared=True,
        domain=domain.strip().lower() if isinstance(domain, str) else None,
        stripe_mode=_stripe_mode(bloc),
    )
