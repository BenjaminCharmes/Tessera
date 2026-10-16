"""Reading Resend's domain responses — ticket-468."""
from dataclasses import dataclass

from tessera.services.provisioning.jsonview import as_dict, as_list, as_str
from tessera.services.provisioning.steps import DnsRecord

STATUS_VERIFIED = "verified"
STATUS_FAILED = "failed"


@dataclass(frozen=True)
class ResendDomain:
    """A sending domain, with the DNS records Resend asks for it."""

    id: str
    name: str
    status: str
    records: tuple[DnsRecord, ...] = ()

    @property
    def verified(self) -> bool:
        """Tell whether Resend has verified the domain."""
        return self.status == STATUS_VERIFIED


def _fqdn(nom: str, domain: str) -> str:
    # Resend rend des noms relatifs à la zone ("send", "resend._domainkey").
    if nom in ("", "@"):
        return domain
    return nom if nom == domain or nom.endswith(f".{domain}") else f"{nom}.{domain}"


def _record_from(brut: object, domain: str) -> DnsRecord | None:
    item = as_dict(brut)
    kind = as_str(item.get("type")).upper()
    value = as_str(item.get("value"))
    if not kind or not value:
        return None
    priorite = item.get("priority")
    return DnsRecord(
        kind,
        _fqdn(as_str(item.get("name")), domain),
        value,
        priorite if isinstance(priorite, int) and not isinstance(priorite, bool) else None,
    )


def domain_from(corps: dict[str, object]) -> ResendDomain:
    """Read a domain object; a record without type or value is dropped."""
    nom = as_str(corps.get("name"))
    records = (_record_from(brut, nom) for brut in as_list(corps.get("records")))
    return ResendDomain(
        as_str(corps.get("id")),
        nom,
        as_str(corps.get("status")),
        tuple(r for r in records if r is not None),
    )
