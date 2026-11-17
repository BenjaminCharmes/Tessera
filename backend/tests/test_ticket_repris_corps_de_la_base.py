"""A resumed branch reads the ticket body its base wrote — ticket-987.

Real git repositories: the branch moved the ticket file out of `todo/`, then
the base rewrote its body under `todo/`.
"""
from pathlib import Path

from tessera.services.noyau.pipeline_events import EventType, OrchestratorEvent
from tessera.services.pipeline.pipeline_run import PipelineRun
from tessera.services.pipeline.ticket_apres_avance import creer_branche_et_relire, relire_apres_branche
from tests.test_ticket_relu_depot_reel import _git, _identite, _Orch

_TODO = "tickets/todo/ticket-100-compteur.md"
_BLOCKED = "tickets/blocked/ticket-100-compteur.md"
_ANCIEN = "Compter par pseudo seul."
_NOUVEAU = "Compter par couple pseudo et appareil."


def _fiche(corps: str, statut: str = "todo") -> str:
    return (
        "---\nagent: codeur\ncreated: 2026-11-14\ndepends_on: []\nid: ticket-100\n"
        f"pr_number: null\npriority: high\nstatus: {statut}\n"
        "title: Compteur\ntype: feat\n---\n\n" + corps + "\n"
    )


def _fichiers_du_ticket(racine: Path) -> list[str]:
    return sorted(p.as_posix() for p in (racine / "tickets").rglob("ticket-100*.md"))


async def _depot(tmp_path: Path, corps_branche: str, deplacer: bool = True, code: bool = False) -> Path:
    """Branch `ticket-100-compteur` holds the file in `blocked/`; the base rewrites `todo/`."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    await _git(bare, "init", "--bare", "-q")
    local = tmp_path / "local"
    local.mkdir()
    await _git(local, "init", "-q")
    await _identite(local)
    (local / "tickets/todo").mkdir(parents=True)
    (local / _TODO).write_text(_fiche(_ANCIEN), encoding="utf-8")
    (local / "code.txt").write_text("a\n", encoding="utf-8")
    await _git(local, "add", _TODO, "code.txt")
    await _git(local, "commit", "-q", "-m", "init")
    await _git(local, "branch", "-M", "develop")
    await _git(local, "remote", "add", "origin", str(bare))
    await _git(local, "push", "-q", "--set-upstream", "origin", "develop")

    await _git(local, "checkout", "-q", "-b", "ticket-100-compteur")
    fiche = _BLOCKED if deplacer else _TODO
    if deplacer:
        (local / "tickets/blocked").mkdir()
        await _git(local, "mv", _TODO, _BLOCKED)
    (local / fiche).write_text(_fiche(corps_branche, "blocked"), encoding="utf-8")
    await _git(local, "add", fiche)
    if code:
        (local / "code.txt").write_text("branche\n", encoding="utf-8")
        await _git(local, "add", "code.txt")
    await _git(local, "commit", "-q", "-m", "chore: ticket-100 blocked")
    await _git(local, "checkout", "-q", "develop")

    autre = tmp_path / "autre"
    await _git(tmp_path, "clone", "-q", "-b", "develop", str(bare), str(autre))
    await _identite(autre)
    (autre / _TODO).write_text(_fiche(_NOUVEAU), encoding="utf-8")
    await _git(autre, "add", _TODO)
    if code:
        (autre / "code.txt").write_text("base\n", encoding="utf-8")
        await _git(autre, "add", "code.txt")
    await _git(autre, "commit", "-q", "-m", "docs: rewrite ticket-100")
    await _git(autre, "push", "-q", "origin", "develop")
    return local


async def _lancer(local: Path) -> tuple[PipelineRun, _Orch, list[OrchestratorEvent]]:
    orch = _Orch(local)
    ticket = await orch._ticket_svc.get_ticket("ticket-100")
    assert ticket is not None
    evenements: list[OrchestratorEvent] = []

    async def on_event(e: OrchestratorEvent) -> None:
        evenements.append(e)

    run = PipelineRun(project_id="projet", ticket=ticket, on_event=on_event)
    assert await creer_branche_et_relire(orch, run) is None  # type: ignore[arg-type]
    return run, orch, evenements


def _relus(evenements: list[OrchestratorEvent]) -> list[OrchestratorEvent]:
    return [e for e in evenements if e.type == EventType.TICKET_RELU_APRES_AVANCE]


async def test_replayed_branch_reads_the_base_body(tmp_path: Path) -> None:
    local = await _depot(tmp_path, _ANCIEN)
    run, orch, evenements = await _lancer(local)

    assert _NOUVEAU in run.ticket.body and _ANCIEN not in run.ticket.body
    assert await _git(local, "branch", "--list", "stale/*") == ""
    assert _fichiers_du_ticket(local) == [(local / _BLOCKED).as_posix()]
    assert (local / _BLOCKED).read_text(encoding="utf-8").count("status: blocked") == 1
    assert len(_relus(evenements)) == 1
    assert any("fiche relue" in ligne for ligne in orch.logs)


async def test_ticket_conflict_resolved_for_the_branch_still_reads_the_base_body(
    tmp_path: Path,
) -> None:
    local = await _depot(tmp_path, "Compter par appareil.", deplacer=False)
    run, _orch, evenements = await _lancer(local)

    assert await _git(local, "branch", "--list", "stale/*") == ""
    assert _NOUVEAU in run.ticket.body and "par appareil." not in run.ticket.body
    assert len(_fichiers_du_ticket(local)) == 1
    assert len(_relus(evenements)) == 1


async def test_stale_renamed_branch_reads_the_base_body(tmp_path: Path) -> None:
    local = await _depot(tmp_path, "Compter par appareil.", deplacer=False, code=True)
    run, _orch, evenements = await _lancer(local)

    assert await _git(local, "branch", "--list", "stale/*") != ""
    assert _NOUVEAU in run.ticket.body and "par appareil." not in run.ticket.body
    assert len(_fichiers_du_ticket(local)) == 1
    assert len(_relus(evenements)) == 1


async def test_stale_copy_in_a_second_folder_is_removed(tmp_path: Path) -> None:
    local = await _depot(tmp_path, _ANCIEN)
    run, orch, evenements = await _lancer(local)
    copie = local / "tickets/in-progress/ticket-100-compteur.md"
    copie.parent.mkdir(exist_ok=True)
    copie.write_text(_fiche(_ANCIEN, "in-progress"), encoding="utf-8")

    assert await relire_apres_branche(orch, run, None) is None  # type: ignore[arg-type]

    assert len(_fichiers_du_ticket(local)) == 1
    relu = await orch._ticket_svc.get_ticket("ticket-100")
    assert relu is not None and _NOUVEAU in relu.body
    assert len(_relus(evenements)) == 2


async def test_unchanged_base_ticket_emits_nothing_and_commits_nothing(tmp_path: Path) -> None:
    local = await _depot(tmp_path, _ANCIEN)
    await _git(local, "pull", "-q", "--ff-only", "origin", "develop")
    # La base porte maintenant le texte neuf ; la branche aussi, déplacée.
    await _git(local, "checkout", "-q", "ticket-100-compteur")
    (local / _BLOCKED).write_text(_fiche(_NOUVEAU, "blocked"), encoding="utf-8")
    await _git(local, "add", _BLOCKED)
    await _git(local, "commit", "-q", "-m", "chore: align")
    await _git(local, "checkout", "-q", "develop")

    run, _orch, evenements = await _lancer(local)

    assert _relus(evenements) == []
    assert await _git(local, "status", "--porcelain") == ""
    assert _NOUVEAU in run.ticket.body
