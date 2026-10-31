"""Untracked pipeline log brought by a merge, and untracked files a run leaves — ticket-480.

Couverture :
- Un journal non suivi en local, suivi sur la base distante : le réalignement
  (CIWatcher) et la synchro de début de run aboutissent, les lignes locales
  restent une seule fois.
- Un journal absent de la base distante, ou ignoré, n'est pas touché.
- Les fichiers non suivis laissés par un run sont listés, jamais supprimés, et
  une ligne de journal les nomme.
"""
import asyncio
from pathlib import Path
from typing import Any

import pytest
from unittest.mock import AsyncMock, MagicMock

from tessera.models.ticket import TicketStatus
from tessera.services import journal_en_attente
from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_fin_de_file import signaler_fichiers_non_suivis
from tessera.services.pipeline_events import OrchestratorEvent, PipelineResult
from tessera.services.realignement_base import realigner_base

_JOURNAL = Path("memory") / "pipeline-log.md"
_LIGNE = "- 2026-10-16 10:00:00 UTC — [ticket-001] PR #1 confiée au CIWatcher"


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode().strip()


async def _cloner(distant: Path, cible: Path) -> None:
    await _git(distant.parent, "clone", "-q", str(distant), str(cible))
    await _git(cible, "config", "user.email", "test@tessera.local")
    await _git(cible, "config", "user.name", "Tessera test")


@pytest.fixture(params=["", "projects/demo"], ids=["racine", "ancestor"])
async def depot(tmp_path: Path, request: pytest.FixtureRequest) -> tuple[Path, Path]:
    """Project dirs of a local clone and of an upstream clone; no log committed yet.

    C'est le premier run d'un projet : le journal n'existe sur aucune base.
    """
    sous: str = request.param
    distant = tmp_path / "distant.git"
    await _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(distant))
    amont = tmp_path / "amont"
    await _cloner(distant, amont)
    await _git(amont, "symbolic-ref", "HEAD", "refs/heads/main")
    (amont / sous).mkdir(parents=True, exist_ok=True)
    (amont / sous / "app.txt").write_text("v0\n", encoding="utf-8")
    await _git(amont, "add", ".")
    await _git(amont, "commit", "-q", "-m", "init")
    await _git(amont, "push", "-q", "-u", "origin", "main")
    local = tmp_path / "local"
    await _cloner(distant, local)
    return local / sous, amont / sous


async def _publier_journal(amont: Path, lignes: str = "# log\n") -> None:
    """Push the merge of a first run: code plus its own copy of the log."""
    (amont / "app.txt").write_text("v1\n", encoding="utf-8")
    (amont / "memory").mkdir(exist_ok=True)
    (amont / _JOURNAL).write_text(lignes, encoding="utf-8")
    await _git(amont, "add", ".")
    await _git(amont, "commit", "-q", "-m", "feat: ticket-001 (#1)")
    await _git(amont, "push", "-q", "origin", "main")


def _journal_local(local: Path) -> None:
    (local / "memory").mkdir(exist_ok=True)
    (local / _JOURNAL).write_text(f"# log local\n{_LIGNE}\n", encoding="utf-8")


async def test_realignment_succeeds_with_an_untracked_log_the_remote_tracks(
    depot: tuple[Path, Path],
) -> None:
    local, amont = depot
    await _publier_journal(amont)
    _journal_local(local)

    assert await realigner_base(local, "main", "proj") is True

    assert await _git(local, "rev-parse", "HEAD") == await _git(
        local, "rev-parse", "origin/main"
    )
    lignes = (local / _JOURNAL).read_text(encoding="utf-8").splitlines()
    assert lignes.count(_LIGNE) == 1
    assert lignes.count("# log") == 1


async def test_log_the_remote_does_not_track_is_left_alone(
    depot: tuple[Path, Path],
) -> None:
    local, amont = depot
    (amont / "app.txt").write_text("v1\n", encoding="utf-8")
    await _git(amont, "commit", "-q", "-am", "feat: sans journal")
    await _git(amont, "push", "-q", "origin", "main")
    _journal_local(local)

    assert await realigner_base(local, "main", "proj") is True

    contenu = (local / _JOURNAL).read_text(encoding="utf-8")
    assert contenu == f"# log local\n{_LIGNE}\n"


async def test_ignored_log_is_not_set_aside(depot: tuple[Path, Path]) -> None:
    local, _ = depot
    _journal_local(local)
    exclude = Path(await _git(local, "rev-parse", "--git-path", "info/exclude"))
    exclude = exclude if exclude.is_absolute() else local / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    exclude.write_text("memory/\n", encoding="utf-8")

    assert await journal_en_attente.journal_non_suivi(local) is False
    assert await journal_en_attente.mettre_de_cote_non_suivi(local, "origin/main") == []
    assert (local / _JOURNAL).is_file()


async def test_sync_base_at_run_start_keeps_untracked_log_lines_once(
    depot: tuple[Path, Path],
) -> None:
    local, amont = depot
    await _publier_journal(amont)
    _journal_local(local)
    service = GitWorkspaceService(local)

    raison = await service.sync_base_depuis_distant("main")

    assert raison is None, raison
    assert await _git(local, "rev-parse", "HEAD") == await _git(
        local, "rev-parse", "origin/main"
    )
    lignes = (local / _JOURNAL).read_text(encoding="utf-8").splitlines()
    assert lignes.count(_LIGNE) == 1


async def test_files_left_untracked_by_the_run_are_listed_not_deleted(
    depot: tuple[Path, Path],
) -> None:
    local, _ = depot
    (local / "ancien.txt").write_text("avant le run\n", encoding="utf-8")
    service = GitWorkspaceService(local)
    service._preexisting_untracked = await service._untracked_files()
    genere = local / "src" / "generated" / "x.ts"
    genere.parent.mkdir(parents=True)
    genere.write_text("export {}\n", encoding="utf-8")

    laisses = await service.fichiers_non_suivis_laisses()

    assert laisses == ("src/generated/x.ts",)
    assert genere.read_text(encoding="utf-8") == "export {}\n"


@pytest.mark.parametrize("approuve", [True, False], ids=["approuve", "bloque"])
async def test_log_line_names_the_untracked_files_and_keeps_them(
    depot: tuple[Path, Path], tmp_path: Path, approuve: bool,
) -> None:
    local, _ = depot
    service = GitWorkspaceService(local)
    genere = local / "src" / "generated" / "x.ts"
    genere.parent.mkdir(parents=True)
    genere.write_text("export {}\n", encoding="utf-8")
    # Journal hors du dépôt : il ne doit pas compter parmi les fichiers non suivis.
    log = tmp_path / "journal.md"

    async def _livrer(resultat: object) -> Livraison:
        return Livraison(arret="Conflit sur rebase — aucune PR ouverte")

    orch = _OrchestrateurDouble(
        approuve,
        runner=MagicMock(),
        ticket_service=AsyncMock(**{"get_ticket.return_value": None}),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log,
        git_workspace=service,
        base_branch="main",
        livrer=_livrer,
    )

    await orch.run_pipeline("proj", "ticket-002", _rien)

    contenu = log.read_text(encoding="utf-8")
    assert (
        "[ticket-002] fichiers non suivis laissés par le run : src/generated/x.ts "
        "(à ignorer dans .gitignore ?)"
    ) in contenu
    assert genere.is_file()


async def test_no_log_line_when_the_run_left_nothing(
    depot: tuple[Path, Path], tmp_path: Path,
) -> None:
    local, _ = depot
    log = tmp_path / "journal.md"
    orch = _OrchestrateurDouble(
        True,
        runner=MagicMock(),
        ticket_service=AsyncMock(),
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=log,
        git_workspace=GitWorkspaceService(local),
        base_branch="main",
    )

    await signaler_fichiers_non_suivis(orch, "ticket-002")

    assert not log.exists()


async def _rien(event: OrchestratorEvent) -> None:
    return None


class _OrchestrateurDouble(Orchestrator):
    """Orchestrateur dont seul le pipeline interne est doublé."""

    def __init__(self, approuve: bool, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._approuve = approuve

    async def _run_pipeline(self, *args: Any, **kwargs: Any) -> PipelineResult:
        return PipelineResult(
            ticket_id="ticket-002",
            final_status=TicketStatus.done if self._approuve else TicketStatus.blocked,
            rounds=1,
            approved=self._approuve,
            branch="ticket-002-slug",
            commit_sha="abc",
        )
