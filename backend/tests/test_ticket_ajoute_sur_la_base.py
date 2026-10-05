"""A ticket added on the base while the repo sits on a delivered branch — ticket-336.

Après une file, le dépôt reste sur la branche du dernier ticket livré. Un
ticket ajouté sur la base entre-temps n'existe pas dans l'arbre : le run
suivant le cherchait sur disque, avant toute synchronisation, et s'arrêtait
sur « Ticket introuvable » (démineur, 2026-10-05).
"""
import asyncio
from pathlib import Path

from tessera.services.git_workspace import GitWorkspaceService
from tessera.services.politique_run import PolitiqueRun

_TICKET = "tickets/todo/ticket-040-nouvelle-feature.md"


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    assert proc.returncode == 0, stderr.decode()
    return stdout.decode().strip()


async def _clone(cwd: Path, bare: Path) -> None:
    cwd.mkdir()
    await _git(cwd, "init", "-q")
    await _git(cwd, "config", "user.email", "test@tessera.local")
    await _git(cwd, "config", "user.name", "Tessera test")
    await _git(cwd, "remote", "add", "origin", str(bare))


async def _depot_sur_une_branche_livree(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, "init", "--bare", "-q")

    local = tmp_path / "local"
    await _clone(local, bare)
    (local / "README.md").write_text("# projet\n", encoding="utf-8")
    await _git(local, "add", ".")
    await _git(local, "commit", "-q", "-m", "init")
    await _git(local, "branch", "-M", "develop")
    await _git(local, "push", "-q", "--set-upstream", "origin", "develop")
    # La file a livré son dernier ticket : le dépôt reste sur sa branche.
    await _git(local, "checkout", "-q", "-b", "ticket-039-derniere-livraison")

    # Pendant ce temps, le ticket-040 arrive sur la base distante.
    autre = tmp_path / "autre"
    await _clone(autre, bare)
    await _git(autre, "fetch", "-q", "origin")
    await _git(autre, "checkout", "-q", "-b", "develop", "origin/develop")
    (autre / _TICKET).parent.mkdir(parents=True)
    (autre / _TICKET).write_text("---\nid: ticket-040\n---\n", encoding="utf-8")
    await _git(autre, "add", ".")
    await _git(autre, "commit", "-q", "-m", "chore: add ticket 040")
    await _git(autre, "push", "-q", "origin", "develop")
    return local


async def test_a_fresh_workspace_restores_a_ticket_added_on_the_remote_base(
    tmp_path: Path,
) -> None:
    local = await _depot_sur_une_branche_livree(tmp_path)
    # Neuf, comme à chaque requête (ADR-008) : aucune base encore initialisée.
    service = GitWorkspaceService(local, politique=PolitiqueRun(base_branch="develop"))

    restored = await service.restaurer_ticket_depuis_base("ticket-040")

    assert restored is True
    assert "ticket-040" in (local / _TICKET).read_text(encoding="utf-8")


async def test_without_a_declared_base_nothing_is_restored(tmp_path: Path) -> None:
    local = await _depot_sur_une_branche_livree(tmp_path)
    service = GitWorkspaceService(local)

    assert await service.restaurer_ticket_depuis_base("ticket-040") is False
    assert not (local / _TICKET).exists()
