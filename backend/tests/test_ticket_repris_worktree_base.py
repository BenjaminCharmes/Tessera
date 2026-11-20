"""A resumed branch in a worktree reads the gate fields of its base — ticket-1000.

Real git repositories: the branch rewrote the ticket (`preuve_reelle`, criteria)
and is checked out as a run worktree would be; the base keeps the original.
"""
from pathlib import Path

from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.pipeline.ticket_apres_avance import relire_apres_branche
from tests.test_ticket_relu_depot_reel import _git, _identite, _Orch

_FICHE = "tickets/todo/ticket-100-compteur.md"
_CRITERES_BASE = "- [ ] Le compteur est par couple pseudo et appareil."
_CRITERES_BRANCHE = "- [ ] Rien à vérifier."


def _fiche(preuve: str, criteres: str) -> str:
    return (
        "---\nagent: codeur\ncreated: 2026-11-14\ndepends_on: []\nid: ticket-100\n"
        f"pr_number: null\npreuve_reelle: {preuve}\npriority: high\nstatus: todo\n"
        f"title: Compteur\ntype: feat\n---\n\n## Critères d'acceptation\n\n{criteres}\n"
    )


class _OrchWorktree(_Orch):
    def __init__(self, racine: Path) -> None:
        super().__init__(racine)
        self._worktree = object()


async def _depot(tmp_path: Path) -> Path:
    """The base holds `preuve_reelle: true`; the resumed branch holds `false`."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, "init", "--bare", "-q")
    local = tmp_path / "local"
    local.mkdir()
    await _git(local, "init", "-q")
    await _identite(local)
    (local / "tickets/todo").mkdir(parents=True)
    (local / _FICHE).write_text(_fiche("true", _CRITERES_BASE), encoding="utf-8")
    await _git(local, "add", _FICHE)
    await _git(local, "commit", "-q", "-m", "init")
    await _git(local, "branch", "-M", "develop")
    await _git(local, "remote", "add", "origin", str(bare))
    await _git(local, "push", "-q", "--set-upstream", "origin", "develop")
    await _git(local, "checkout", "-q", "-b", "ticket-100-compteur")
    (local / _FICHE).write_text(_fiche("false", _CRITERES_BRANCHE), encoding="utf-8")
    await _git(local, "add", _FICHE)
    await _git(local, "commit", "-q", "-m", "chore: rewrite ticket-100")
    return local


async def _lancer(local: Path) -> tuple[PipelineRun, _OrchWorktree]:
    orch = _OrchWorktree(local)
    ticket = await orch._ticket_svc.get_ticket("ticket-100")
    assert ticket is not None and ticket.preuve_reelle is False
    run = PipelineRun(project_id="projet", ticket=ticket, on_event=_ignorer)
    await orch._git_workspace.adopter_worktree("ticket-100-compteur", "develop")
    assert await relire_apres_branche(orch, run, None) is None  # type: ignore[arg-type]
    return run, orch


async def _ignorer(_evenement: object) -> None:
    return None


async def test_worktree_resumed_branch_reads_preuve_reelle_of_the_base(tmp_path: Path) -> None:
    run, orch = await _lancer(await _depot(tmp_path))

    assert run.ticket.preuve_reelle is True
    assert orch._preuves_reelles["ticket-100"] is True


async def test_worktree_resumed_branch_gives_the_validator_the_base_criteria(
    tmp_path: Path,
) -> None:
    run, _orch = await _lancer(await _depot(tmp_path))

    assert _CRITERES_BASE in run.ticket.body
    assert _CRITERES_BRANCHE not in run.ticket.body
