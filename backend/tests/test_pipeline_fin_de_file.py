"""End-of-queue steps live outside the Orchestrator class — ticket-686."""
import asyncio
import re
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock

from tessera.services import orchestrator as orchestrator_module
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_documentation import documenter_le_run
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.services.pipeline_fin_de_file import (
    attendre_merge_et_syncer,
    finaliser_livraison,
    nettoyer_apres_file,
    realigner_base,
    sur_la_base,
)
from tessera.models.ticket import TicketStatus

_SERVICES = Path(orchestrator_module.__file__).parent


def _orch(
    git: object | None, base: str | None = "main", **extra: object
) -> tuple[Orchestrator, list[str]]:
    logs: list[str] = []
    orch = MagicMock()
    orch._git_workspace = git
    orch._base_branch = base
    orch._log = logs.append
    for nom, valeur in extra.items():
        setattr(orch, nom, valeur)
    return cast(Orchestrator, orch), logs


def _git(courante: str = "ticket-686-x") -> MagicMock:
    git = MagicMock()
    git.branche_courante = AsyncMock(return_value=courante)
    git.commit_bookkeeping = AsyncMock()
    git.retourner_sur_base = AsyncMock()
    git.sync_base_depuis_distant = AsyncMock(return_value=None)
    git.commit_all = AsyncMock()
    return git


def test_the_seven_methods_are_not_defined_in_the_class() -> None:
    source = (_SERVICES / "orchestrator.py").read_text(encoding="utf-8")
    interdites = (
        "_documenter_le_run|_attendre_merge_et_syncer|_realigner_base|"
        "_finaliser_livraison|_signaler_fichiers_non_suivis|"
        "_nettoyer_apres_file|_sur_la_base"
    )
    assert re.search(rf"def ({interdites})\b", source) is None


def test_the_new_modules_import_orchestrator_only_for_typing() -> None:
    for nom in ("pipeline_documentation.py", "pipeline_fin_de_file.py"):
        source = (_SERVICES / nom).read_text(encoding="utf-8")
        hors_typage = re.findall(
            r"^from tessera\.services\.orchestrator import", source, re.M
        )
        assert len(hors_typage) == 0
        assert source.count("from tessera.services.orchestrator import") == 1
        assert source.index("if TYPE_CHECKING:") < source.index(
            "from tessera.services.orchestrator import"
        )


async def test_sur_la_base_reads_the_current_branch() -> None:
    assert await sur_la_base(_orch(_git("main"))[0]) is True
    assert await sur_la_base(_orch(_git("ticket-1"))[0]) is False
    assert await sur_la_base(_orch(None)[0]) is False
    assert await sur_la_base(_orch(_git("main"), base=None)[0]) is False


async def test_realigner_base_logs_the_outcome() -> None:
    git = _git()
    orch, logs = _orch(git)
    await realigner_base(orch, "proj", "ticket-1")
    assert logs == ["[proj] ticket-1 : base réalignée sur main"]

    git.sync_base_depuis_distant = AsyncMock(return_value="divergée")
    await realigner_base(orch, "proj", "ticket-1")
    assert "ignoré — divergée" in logs[-1]


async def test_realigner_base_does_nothing_without_workspace() -> None:
    orch, logs = _orch(None)
    await realigner_base(orch, "proj", "ticket-1")
    assert logs == []


async def test_finaliser_livraison_commits_then_returns_to_base() -> None:
    git = _git("ticket-1")
    orch, _ = _orch(git)
    await finaliser_livraison(orch, Livraison())
    git.commit_bookkeeping.assert_awaited_once()
    git.retourner_sur_base.assert_awaited_once_with("main")


async def test_nettoyer_apres_file_skips_the_commit_on_the_base() -> None:
    git = _git("main")
    orch, _ = _orch(git)
    await nettoyer_apres_file(orch)
    git.commit_bookkeeping.assert_not_awaited()
    git.retourner_sur_base.assert_awaited_once_with("main")


async def test_attendre_merge_times_out_without_realigning() -> None:
    async def _jamais(*_a: object, **_k: object) -> bool:
        await asyncio.sleep(5)
        return True

    watcher = MagicMock()
    watcher.attendre_merge = _jamais
    git = _git()
    orch, logs = _orch(
        git, _ci_watcher=watcher, _attente_merge_max_s=0.01, _etat_pr=None
    )
    assert await attendre_merge_et_syncer(orch, "proj", "ticket-1", 7) is False
    assert "délai d'attente du merge dépassé" in logs[0]
    git.sync_base_depuis_distant.assert_not_awaited()


async def test_documenter_le_run_commits_and_reports() -> None:
    class _Doc:
        fichiers_modifies = ["docs/a.md"]
        refus: list[str] = []
        marqueur_ecrit = False

    async def _documenter() -> _Doc:
        return _Doc()

    git = _git()
    orch, logs = _orch(git, _documenter=_documenter)
    evenements: list[OrchestratorEvent] = []

    async def _on_event(e: OrchestratorEvent) -> None:
        evenements.append(e)

    resultat = PipelineResult(
        ticket_id="ticket-1", final_status=TicketStatus.done, rounds=1,
        approved=True, branch="ticket-1-x",
    )
    await documenter_le_run(orch, resultat, _on_event)

    git.commit_all.assert_awaited_once_with("docs: update documentation for ticket-1")
    assert "documentation: 1 fichier(s)" in logs[0]
    assert [e.type for e in evenements] == [
        EventType.DOCUMENTATION_STARTED, EventType.DOC_UPDATED,
    ]
