"""Livrer après le merge des PR précédentes de la file — ticket-533.

Dans une file, le ticket N+1 est codé pendant que `CIWatcher` attend la CI de
la PR du ticket N. Si N+1 est rebasé et poussé avant que N soit mergée, sa PR
part d'une base qui ne contient pas N : dès que N est mergée, GitHub la déclare
en conflit — `documentation.json` et la documentation les premiers, que chaque
PR de la file modifie au même endroit.

La parade tient en un ordre : **la livraison d'un ticket attend que les PR
déjà confiées au watcher aient fini**. Le rebase de la phase 1 se fait alors
sur une base qui porte N, le conflit n'a pas lieu d'être. Rien n'est forcé, et
la tête poussée reste celle que le reviewer a lue (ADR-022, ADR-039).

L'attente est bornée : passé le délai, ou si une PR précédente reste bloquée,
la livraison se fait comme avant — une PR en conflit s'arrête alors sur
« à rebaser » (ticket-452), elle ne se perd pas.
"""
import asyncio
from collections.abc import Awaitable, Callable
from typing import Protocol

from tessera.services.ci_watcher import CI_WATCHER
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import PipelineResult
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Un peu plus que la phase 2 d'un ticket (attente CI 900 s + merge), pour
#: laisser finir une PR sans bloquer la file au-delà.
_ATTENTE_MAX_S = 1500.0


class _Surveillance(Protocol):
    """Ce que la livraison lit du `CIWatcher`."""

    def en_attente(self, project_id: str) -> tuple[str, ...]: ...

    async def attendre_merge(
        self,
        project_id: str,
        ticket_id: str,
        pr_number: int | None = None,
        etat_pr: Callable[[int], Awaitable[str]] | None = None,
    ) -> bool: ...


async def attendre_les_merges_en_cours(
    surveillance: _Surveillance,
    project_id: str,
    ticket_id: str,
    attente_max_s: float = _ATTENTE_MAX_S,
) -> tuple[str, ...]:
    """Wait until every other ticket the watcher holds for the project is done.

    Returns the tickets that were waited for, in the order they were found;
    empty when nothing was pending. A timeout is logged and ends the wait: it
    never raises, the delivery then goes on as it did before ticket-533.
    """
    precedents = tuple(
        t for t in surveillance.en_attente(project_id) if t != ticket_id
    )
    if not precedents:
        return ()
    _logger.info(
        "livraison_attend_les_merges",
        extra={"project": project_id, "ticket": ticket_id, "attend": list(precedents)},
    )
    try:
        await asyncio.wait_for(
            _attendre_chacun(surveillance, project_id, precedents),
            timeout=attente_max_s,
        )
    except asyncio.TimeoutError:
        _logger.warning(
            "livraison_attente_des_merges_depassee",
            extra={"project": project_id, "ticket": ticket_id},
        )
    return precedents


async def _attendre_chacun(
    surveillance: _Surveillance, project_id: str, tickets: tuple[str, ...]
) -> None:
    for precedent in tickets:
        await surveillance.attendre_merge(project_id, precedent)


def apres_les_merges(
    livrer: Callable[[PipelineResult], Awaitable[Livraison]],
    project_id: str,
    surveillance: _Surveillance | None = None,
    attente_max_s: float = _ATTENTE_MAX_S,
) -> Callable[[PipelineResult], Awaitable[Livraison]]:
    """Wrap `livrer` so it starts once the project's earlier PR are merged or stopped.

    Sans `surveillance`, c'est le `CI_WATCHER` du processus, celui que la
    livraison de phase 2 alimente.
    """

    async def livrer_apres(result: PipelineResult) -> Livraison:
        await attendre_les_merges_en_cours(
            surveillance or CI_WATCHER, project_id, result.ticket_id, attente_max_s
        )
        return await livrer(result)

    return livrer_apres
