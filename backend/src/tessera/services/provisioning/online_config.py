"""The ``online`` block of ``agents.json`` — ADR-053, ticket-465.

Distinct from ``services`` (the local commands of ADR-042). Absent block: no
button, nothing to provision. Only known values are accepted, and an invalid
block is refused by naming the offending field.
"""
import json
import re
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError, ValidationInfo, field_validator

Resource = Literal["vercel", "database", "resend", "dns", "stripe"]

_DOMAINE = re.compile(
    r"^(?!-)[a-z0-9-]{1,63}(?<!-)(\.(?!-)[a-z0-9-]{1,63}(?<!-))+$"
)


_VARIABLE = re.compile(r"^[A-Z_][A-Z0-9_]*$")


class OnlineConfigError(ValueError):
    """The ``online`` block is invalid; the message names each field."""


def _nom_variable(nom: str) -> str:
    if not _VARIABLE.match(nom):
        raise ValueError(f"{nom!r} is not an environment variable name such as MY_SECRET")
    return nom


class StripeConfig(BaseModel):
    """What a project declares for Stripe (ticket-470 consumes it)."""

    model_config = ConfigDict(extra="forbid")

    webhook_path: str
    events: list[str] = Field(min_length=1)
    product: Optional[str] = None
    price_cents: Optional[int] = Field(default=None, gt=0)
    #: Live mode is never implied: it must be declared.
    mode: Literal["test", "live"] = "test"

    @field_validator("webhook_path")
    @classmethod
    def _chemin_absolu(cls, valeur: str) -> str:
        if not valeur.startswith("/"):
            raise ValueError("must start with '/'")
        return valeur


class OnlineConfig(BaseModel):
    """The online resources of one project."""

    model_config = ConfigDict(extra="forbid")

    domain: str
    resources: list[Resource] = Field(default_factory=list)
    stripe: Optional[StripeConfig] = Field(default=None, validate_default=True)
    #: Secrets aléatoires à poser ; ``None`` laisse le défaut de l'étape Variables.
    generate: Optional[list[str]] = None
    #: Variables calculées ; ``{domain}`` est remplacé par le domaine déclaré.
    derive: dict[str, str] = Field(default_factory=dict)
    #: Route du projet qui lit la base et rend 200 ; ``None`` : seule la racine est contrôlée.
    health_path: Optional[str] = None

    @field_validator("health_path")
    @classmethod
    def _health_path_valide(cls, valeur: Optional[str]) -> Optional[str]:
        if valeur is not None and not valeur.startswith("/"):
            raise ValueError("must start with '/'")
        return valeur

    @field_validator("generate")
    @classmethod
    def _generate_valide(cls, valeur: Optional[list[str]]) -> Optional[list[str]]:
        for nom in valeur or []:
            _nom_variable(nom)
        return valeur

    @field_validator("derive")
    @classmethod
    def _derive_valide(cls, valeur: dict[str, str]) -> dict[str, str]:
        for nom in valeur:
            _nom_variable(nom)
        return valeur

    @field_validator("domain")
    @classmethod
    def _domaine_valide(cls, valeur: str) -> str:
        domaine = valeur.strip().lower()
        if not _DOMAINE.match(domaine):
            raise ValueError("must be a bare domain name such as example.com")
        return domaine

    @field_validator("stripe")
    @classmethod
    def _stripe_declare(
        cls, valeur: Optional[StripeConfig], info: ValidationInfo
    ) -> Optional[StripeConfig]:
        # Les événements dépendent du code du projet : Tessera ne les devine pas.
        if valeur is None and "stripe" in info.data.get("resources", []):
            raise ValueError("required when 'stripe' is listed in resources")
        return valeur

    def wants(self, resource: Resource) -> bool:
        """Tell whether the project lists this resource."""
        return resource in self.resources


def _format_errors(erreur: ValidationError) -> str:
    champs = []
    for detail in erreur.errors():
        chemin = ".".join(["online", *(str(p) for p in detail["loc"])])
        champs.append(f"{chemin}: {detail['msg']}")
    return "; ".join(champs)


def parse_online_config(bloc: object) -> OnlineConfig:
    """Validate a raw ``online`` block, or raise `OnlineConfigError`."""
    if not isinstance(bloc, dict):
        raise OnlineConfigError("online: must be an object")
    try:
        return OnlineConfig.model_validate(bloc)
    except ValidationError as erreur:
        raise OnlineConfigError(_format_errors(erreur)) from None


def load_online_config(project_path: Path) -> Optional[OnlineConfig]:
    """Read the ``online`` block of a project, ``None`` when it declares none.

    A missing or unreadable ``agents.json`` means no block, like the other
    sections; a block that is present but invalid raises.
    """
    agents_json = project_path / "agents.json"
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    bloc = data.get("online") if isinstance(data, dict) else None
    if bloc is None:
        return None
    return parse_online_config(bloc)
