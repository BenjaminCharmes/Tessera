"""Reading the DNS parts of Vercel's domain responses — ticket-466."""
from dataclasses import dataclass

from tessera.services.provisioning.jsonview import as_dict, as_list, as_str
from tessera.services.provisioning.steps import DnsRecord

_RANG_INCONNU = 99


@dataclass(frozen=True)
class VercelDomain:
    """A domain attached to a project, with the records proving ownership."""

    name: str
    verified: bool
    verification: tuple[DnsRecord, ...] = ()


def domain_from(domain: str, corps: dict[str, object]) -> VercelDomain:
    """Read a project-domain response: the verified flag and its TXT challenges."""
    records: list[DnsRecord] = []
    for brut in as_list(corps.get("verification")):
        item = as_dict(brut)
        kind = as_str(item.get("type"))
        name = as_str(item.get("domain"))
        value = as_str(item.get("value"))
        if kind and name and value:
            records.append(DnsRecord(kind, name, value))
    return VercelDomain(domain, corps.get("verified") is True, tuple(records))


def _rank(proposition: dict[str, object]) -> int:
    rang = proposition.get("rank")
    return rang if isinstance(rang, int) else _RANG_INCONNU


def _best_value(propositions: object) -> str:
    """Pick the value of the best-ranked recommendation (rank 1 is preferred)."""
    candidats = sorted((as_dict(p) for p in as_list(propositions)), key=_rank)
    for candidat in candidats:
        valeur = candidat.get("value")
        if isinstance(valeur, list):
            valeur = valeur[0] if valeur else ""
        if as_str(valeur):
            return as_str(valeur).rstrip(".")
    return ""


def records_from_config(domain: str, corps: dict[str, object]) -> list[DnsRecord]:
    """Turn a domain-config response into the one A or CNAME record to publish."""
    # Un domaine à deux libellés est un apex (A), au-delà un sous-domaine (CNAME).
    # Heuristique : sans liste des suffixes publics, `example.co.uk` serait mal rangé.
    ip = _best_value(corps.get("recommendedIPv4"))
    cname = _best_value(corps.get("recommendedCNAME"))
    apex = domain.count(".") == 1
    if ip and (apex or not cname):
        return [DnsRecord("A", domain, ip)]
    return [DnsRecord("CNAME", domain, cname)] if cname else []
