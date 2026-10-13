"""Realign the local base after a watched merge — ticket-422.

Couverture :
- Après un merge surveillé, sans run en cours, HEAD égale origin/<base>.
- La ligne de journal non commitée est conservée, sans doublon (qu'elle soit
  absente ou déjà présente dans le commit distant).
- Aucun réalignement quand un run occupe le projet.
- Aucun réalignement, arbre intact, quand un autre fichier que le journal est
  modifié, ou quand l'arbre n'est pas sur la base.
- Un pull qui échoue laisse `merged` à vrai et le journal intact.
"""
import asyncio
from collections.abc import Iterator
from pathlib import Path

import pytest

from tessera.services.ci_watcher import CIWatcher
from tessera.services.livraison import Livraison
from tessera.services.pipeline_events import EventType, OrchestratorEvent
from tessera.services.realignement_base import Realignement, realigner_base
from tessera.services.run_registry import RUN_REGISTRY

_JOURNAL = Path("memory") / "pipeline-log.md"
_LIGNE = "- 2026-10-13 13:27:20 UTC — [ticket-051] PR #71 confiée au CIWatcher"


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
    """The project dir of a local clone, and of a second clone publishing the merge.

    Deux dispositions : le projet est la racine du dépôt, ou un sous-dossier
    (`git_root: ancestor`, comme ide-core) où `git status` donne des chemins
    préfixés.
    """
    sous: str = request.param
    distant = tmp_path / "distant.git"
    await _git(tmp_path, "init", "-q", "--bare", "-b", "main", str(distant))
    amont = tmp_path / "amont"
    await _cloner(distant, amont)
    await _git(amont, "symbolic-ref", "HEAD", "refs/heads/main")
    projet_amont = amont / sous
    (projet_amont / "memory").mkdir(parents=True)
    (projet_amont / _JOURNAL).write_text("# log\n", encoding="utf-8")
    (projet_amont / "app.txt").write_text("v0\n", encoding="utf-8")
    await _git(amont, "add", ".")
    await _git(amont, "commit", "-q", "-m", "init")
    await _git(amont, "push", "-q", "-u", "origin", "main")
    local = tmp_path / "local"
    await _cloner(distant, local)
    return local / sous, projet_amont


async def _publier_merge(amont: Path, journal: str | None = None) -> None:
    """Push a new commit on the remote base, as a PR merge would."""
    (amont / "app.txt").write_text("v1\n", encoding="utf-8")
    if journal is not None:
        with (amont / _JOURNAL).open("a", encoding="utf-8") as f:
            f.write(journal)
    await _git(amont, "add", ".")
    await _git(amont, "commit", "-q", "-m", "merge")
    await _git(amont, "push", "-q", "origin", "main")


@pytest.fixture(autouse=True)
def _aucun_run() -> Iterator[None]:
    assert not RUN_REGISTRY.projet_occupe("proj-realign")
    yield
    assert not RUN_REGISTRY.projet_occupe("proj-realign")


async def _surveiller(local: Path) -> list[OrchestratorEvent]:
    events: list[OrchestratorEvent] = []

    async def collect(event: OrchestratorEvent) -> None:
        events.append(event)

    async def phase2(pr_number: int) -> Livraison:
        return Livraison(pr_number=pr_number, merged=True)

    watcher = CIWatcher()
    await watcher.surveiller(
        "proj-realign", "ticket-051", 71, phase2, collect,
        realignement=Realignement(local, "main"),
    )
    await watcher.attendre_merge("proj-realign", "ticket-051")
    return events


def _merge_vrai(events: list[OrchestratorEvent]) -> bool:
    fini = [e for e in events if e.type == EventType.CI_MERGE_DONE]
    return bool(fini) and fini[-1].data["merged"] is True


def _ajouter_ligne(local: Path) -> None:
    with (local / _JOURNAL).open("a", encoding="utf-8") as f:
        f.write(_LIGNE + "\n")


async def test_base_realigned_after_watched_merge(depot: tuple[Path, Path]) -> None:
    local, amont = depot
    await _publier_merge(amont)

    events = await _surveiller(local)

    assert _merge_vrai(events)
    assert await _git(local, "rev-parse", "HEAD") == await _git(
        local, "rev-parse", "origin/main"
    )
    assert (local / "app.txt").read_text(encoding="utf-8") == "v1\n"


async def test_uncommitted_journal_line_is_kept_once(depot: tuple[Path, Path]) -> None:
    local, amont = depot
    await _publier_merge(amont)
    _ajouter_ligne(local)

    await _surveiller(local)

    lignes = (local / _JOURNAL).read_text(encoding="utf-8").splitlines()
    assert lignes.count(_LIGNE) == 1
    assert await _git(local, "rev-parse", "HEAD") == await _git(
        local, "rev-parse", "origin/main"
    )


async def test_journal_line_already_on_remote_is_not_duplicated(
    depot: tuple[Path, Path],
) -> None:
    local, amont = depot
    await _publier_merge(amont, journal=_LIGNE + "\n")
    _ajouter_ligne(local)

    await _surveiller(local)

    lignes = (local / _JOURNAL).read_text(encoding="utf-8").splitlines()
    assert lignes.count(_LIGNE) == 1


async def test_no_realignment_when_a_run_holds_the_project(
    depot: tuple[Path, Path],
) -> None:
    local, amont = depot
    await _publier_merge(amont)
    avant = await _git(local, "rev-parse", "HEAD")
    run = RUN_REGISTRY.ouvrir("proj-realign", "ticket-052")
    try:
        events = await _surveiller(local)
    finally:
        RUN_REGISTRY.fermer(run.run_id)

    assert _merge_vrai(events)
    assert await _git(local, "rev-parse", "HEAD") == avant


async def test_no_realignment_when_another_file_is_modified(
    depot: tuple[Path, Path],
) -> None:
    local, amont = depot
    await _publier_merge(amont)
    avant = await _git(local, "rev-parse", "HEAD")
    (local / "app.txt").write_text("travail local\n", encoding="utf-8")
    _ajouter_ligne(local)

    events = await _surveiller(local)

    assert _merge_vrai(events)
    assert await _git(local, "rev-parse", "HEAD") == avant
    assert (local / "app.txt").read_text(encoding="utf-8") == "travail local\n"
    assert (local / _JOURNAL).read_text(encoding="utf-8").splitlines().count(_LIGNE) == 1


async def test_no_realignment_when_tree_is_on_another_branch(
    depot: tuple[Path, Path],
) -> None:
    local, amont = depot
    await _publier_merge(amont)
    await _git(local, "checkout", "-q", "-b", "ticket-052-autre")

    assert await realigner_base(local, "main", "proj-realign") is False

    assert await _git(local, "rev-parse", "--abbrev-ref", "HEAD") == "ticket-052-autre"


async def test_failed_pull_keeps_merged_true_and_journal(
    depot: tuple[Path, Path],
) -> None:
    local, amont = depot
    await _publier_merge(amont)
    await _git(local, "remote", "set-url", "origin", str(local.parent / "absent.git"))
    avant = await _git(local, "rev-parse", "HEAD")
    _ajouter_ligne(local)

    events = await _surveiller(local)

    assert _merge_vrai(events)
    assert await _git(local, "rev-parse", "HEAD") == avant
    assert (local / _JOURNAL).read_text(encoding="utf-8").splitlines().count(_LIGNE) == 1
