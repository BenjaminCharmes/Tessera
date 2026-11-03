"""The DNS step: publish in Cloudflare the records other steps asked for — ticket-469.

It reads before it writes, creates only a record that does not exist as is
(same type, name and content), and never updates or deletes anything. A record
with the same type and name but another content is the user's: the step stops
on ``needs_human`` and writes nothing, even for the records that were missing.
Records are public, so they may appear in a detail and in an event.
"""
from dataclasses import dataclass
from typing import Optional

from tessera.services.provisioning.cloudflare import CloudflareClient, CloudflareZone
from tessera.services.provisioning.steps import (
    DnsRecord,
    ProvisioningContext,
    StepResult,
    StepState,
)
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Types whose content is a host name: case and a final dot do not matter.
_TYPES_HOTE = frozenset({"CNAME", "MX", "NS"})


def _full_name(name: str, zone: str) -> str:
    """Return the absolute lower-case name; ``@`` and relative names are completed."""
    nom = name.strip().lower().rstrip(".")
    if nom in ("", "@"):
        return zone
    return nom if nom == zone or nom.endswith(f".{zone}") else f"{nom}.{zone}"


def _content_key(record_type: str, content: str) -> str:
    """Normalise a content for comparison: Cloudflare returns TXT between quotes."""
    contenu = content.strip()
    if record_type == "TXT" and len(contenu) >= 2 and contenu[0] == contenu[-1] == '"':
        contenu = contenu[1:-1]
    if record_type in _TYPES_HOTE:
        contenu = contenu.lower().rstrip(".")
    return contenu


def _describe(record: DnsRecord) -> str:
    return f"{record.type} {record.name} {record.content}"


def _zone_candidates(domain: str) -> list[str]:
    """The domain, then its parents down to two labels (the zone may be the apex)."""
    labels = domain.split(".")
    return [".".join(labels[i:]) for i in range(len(labels) - 1)]


@dataclass
class _Classified:
    """What the wanted records are, compared with the zone."""

    missing: list[DnsRecord]
    conflicts: list[str]


class DnsStep:
    """Publish ``ctx.wanted_dns`` in the project's zone, never overwriting."""

    name = "dns"

    def __init__(self, client: CloudflareClient) -> None:
        self._client = client

    async def inspect(self, ctx: ProvisioningContext) -> StepResult:
        """Read the zone and its records; nothing is written."""
        return await self._run(ctx, write=False)

    async def apply(self, ctx: ProvisioningContext) -> StepResult:
        """Create the records that are missing, and only if none conflicts."""
        return await self._run(ctx, write=True)

    async def _run(self, ctx: ProvisioningContext, write: bool) -> StepResult:
        court = self._shortcut(ctx)
        if court is not None:
            return court
        zone = await self._find_zone(ctx.online.domain)
        if isinstance(zone, StepResult):
            return self._with_records(zone, ctx)
        classes = await self._classify(zone, ctx.wanted_dns)
        if classes.conflicts:
            return StepResult(StepState.NEEDS_HUMAN, self._conflict_detail(classes))
        if not classes.missing:
            ctx.dns_published = True
            return StepResult(StepState.SKIPPED, "every requested record is already published")
        if not write:
            return StepResult(StepState.TODO, f"{len(classes.missing)} record(s) to create")
        for record in classes.missing:
            await self._client.create_record(zone.id, record)
        ctx.dns_published = True
        _logger.info("dns_records_created", extra={"count": len(classes.missing)})
        return StepResult(StepState.DONE, "created: " + "; ".join(map(_describe, classes.missing)))

    def _shortcut(self, ctx: ProvisioningContext) -> Optional[StepResult]:
        """Answer without asking Cloudflare when the step is off, has no token or no work."""
        if not ctx.online.wants("dns"):
            return self._manual(ctx, "dns is not listed in online.resources")
        if not self._client.configured:
            return self._manual(ctx, "CLOUDFLARE_API_TOKEN is not set in the Tessera .env")
        if not ctx.wanted_dns:
            return StepResult(StepState.SKIPPED, "no DNS record was requested")
        return None

    @staticmethod
    def _manual(ctx: ProvisioningContext, raison: str) -> StepResult:
        if not ctx.wanted_dns:
            return StepResult(StepState.MANUAL, f"{raison}; no DNS record was requested")
        liste = "; ".join(_describe(r) for r in ctx.wanted_dns)
        return StepResult(StepState.MANUAL, f"{raison}. Add these records yourself: {liste}")

    @staticmethod
    def _with_records(resultat: StepResult, ctx: ProvisioningContext) -> StepResult:
        if resultat.state is not StepState.NEEDS_HUMAN:
            return resultat
        liste = "; ".join(_describe(r) for r in ctx.wanted_dns)
        return StepResult(resultat.state, f"{resultat.detail}. Records to add: {liste}")

    async def _find_zone(self, domain: str) -> CloudflareZone | StepResult:
        for candidat in _zone_candidates(domain):
            zones = await self._client.find_zones(candidat)
            if len(zones) > 1:
                return StepResult(StepState.FAILED, f"several zones are named '{candidat}'")
            if zones:
                return zones[0]
        return StepResult(
            StepState.NEEDS_HUMAN,
            f"no Cloudflare zone for {domain}: add the domain to Cloudflare yourself",
        )

    async def _classify(self, zone: CloudflareZone, wanted: list[DnsRecord]) -> _Classified:
        classes = _Classified([], [])
        for voulu in wanted:
            nom = _full_name(voulu.name, zone.name)
            existants = await self._client.list_records(zone.id, voulu.type, nom)
            memes = [e for e in existants if self._same_slot(e, voulu, zone.name)]
            if any(self._same_content(e, voulu) for e in memes):
                continue
            if memes:
                actuel = memes[0].content
                classes.conflicts.append(
                    f"{voulu.type} {voulu.name} already exists with another content "
                    f"({actuel}); Tessera wanted {voulu.content}"
                )
            else:
                classes.missing.append(voulu)
        return classes

    @staticmethod
    def _same_slot(existant: DnsRecord, voulu: DnsRecord, zone: str) -> bool:
        return existant.type.upper() == voulu.type.upper() and _full_name(
            existant.name, zone
        ) == _full_name(voulu.name, zone)

    @staticmethod
    def _same_content(existant: DnsRecord, voulu: DnsRecord) -> bool:
        type_ = voulu.type.upper()
        return _content_key(type_, existant.content) == _content_key(type_, voulu.content)

    @staticmethod
    def _conflict_detail(classes: _Classified) -> str:
        return "; ".join(classes.conflicts) + ". Nothing was written: fix it in Cloudflare"
