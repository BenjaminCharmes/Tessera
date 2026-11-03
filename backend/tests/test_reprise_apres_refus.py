"""Une branche reprise après le refus d'une porte repart par le codeur — ticket-528."""
from pathlib import Path

from tessera.models.agent import AgentRole
from tessera.services.orchestrator import EventType
from tessera.services.refus_precedent import Refus, refus_precedent
from tests.test_pipeline_reprise import (
    _VERT,
    _FakeTestRunner,
    _GitReprise,
    _lancer,
    _orchestrateur,
    _reprises,
    _roles,
)

_T = "ticket-001"
_DEBUT = f"- 2026-10-19 22:11:19 UTC — [{_T}] branche {_T}-slug"
_BLOCK = (
    f"- 2026-10-19 22:20:44 UTC — [{_T}] securite: BLOCK — "
    "**Path Traversal CRITIQUE** dans run_worktree.py (165859ms)"
)
_CHANGES = (
    f"- 2026-10-19 21:51:22 UTC — [{_T}] CHANGES_REQUESTED tour 3: "
    "Validateur : le troisième critère n'est pas rempli"
)
_EPUISE = f"- 2026-10-19 21:51:23 UTC — [{_T}] BLOCKED après 3 tour(s) sans approbation"
_COUPURE = f"- 2026-10-19 22:25:00 UTC — [{_T}] INTERROMPU au tour 1 — redémarrage"
_APPROUVE = f"- 2026-10-19 22:25:00 UTC — [{_T}] APPROVED après 2 tour(s)"


def _journal(tmp_path: Path, *lignes: str) -> Path:
    chemin = tmp_path / "memory" / "pipeline-log.md"
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    return chemin


def _courant(ligne_debut: str = _DEBUT) -> str:
    return ligne_debut.replace("22:11:19", "22:30:00")


async def _reprise_avec_journal(
    tmp_path: Path, *lignes: str
) -> tuple[list[AgentRole], str, Path]:
    _journal(tmp_path, *lignes)
    orchestrator, runner = _orchestrateur(tmp_path, _GitReprise(3), _FakeTestRunner(_VERT))
    await _lancer(orchestrator)
    contexte = str(runner.calls[0]["project_context"])
    return _roles(runner), contexte, tmp_path / "memory" / "pipeline-log.md"


async def test_resume_after_a_security_block_starts_with_the_coder(tmp_path: Path) -> None:
    roles, _, _ = await _reprise_avec_journal(tmp_path, _DEBUT, _BLOCK)

    assert roles[0] == AgentRole.codeur


async def test_the_previous_refusal_reason_reaches_the_coder_context(tmp_path: Path) -> None:
    _, contexte, _ = await _reprise_avec_journal(tmp_path, _DEBUT, _BLOCK)

    assert "securite" in contexte
    assert "Path Traversal CRITIQUE" in contexte


async def test_resume_after_an_interruption_still_skips_the_coder(tmp_path: Path) -> None:
    roles, _, _ = await _reprise_avec_journal(tmp_path, _DEBUT, _COUPURE)

    assert roles == [AgentRole.reviewer]


async def test_the_log_line_says_why_the_coder_runs(tmp_path: Path) -> None:
    _, _, journal = await _reprise_avec_journal(tmp_path, _DEBUT, _BLOCK)

    assert (
        "branche reprise (3 commit(s)) — refus précédent : securite, codeur en premier"
        in journal.read_text(encoding="utf-8")
    )


async def test_the_resumed_event_names_the_refusing_gate(tmp_path: Path) -> None:
    # Le run écrit lui-même sa ligne `branche …` : le journal n'a que l'histoire.
    _journal(tmp_path, _DEBUT, _BLOCK)
    orchestrator, _ = _orchestrateur(tmp_path, _GitReprise(3), _FakeTestRunner(_VERT))

    events = await _lancer(orchestrator)

    (event,) = _reprises(events)
    assert event.type == EventType.RUN_RESUMED_FROM_EXISTING_WORK
    assert event.data == {"commits": 3, "verdict": "refused", "refus": "securite"}


async def test_resume_after_exhausted_rounds_carries_the_last_objection(tmp_path: Path) -> None:
    roles, contexte, _ = await _reprise_avec_journal(tmp_path, _DEBUT, _CHANGES, _EPUISE)

    assert roles[0] == AgentRole.codeur
    assert "le troisième critère n'est pas rempli" in contexte


async def test_an_approved_previous_run_is_not_a_refusal(tmp_path: Path) -> None:
    roles, _, _ = await _reprise_avec_journal(tmp_path, _DEBUT, _BLOCK, _DEBUT, _APPROUVE)

    assert roles == [AgentRole.reviewer]


async def test_a_refusal_older_than_the_last_run_does_not_count(tmp_path: Path) -> None:
    roles, _, _ = await _reprise_avec_journal(tmp_path, _DEBUT, _BLOCK, _DEBUT, _COUPURE)

    assert roles == [AgentRole.reviewer]


def test_the_refusal_is_read_from_the_run_before_the_current_one(tmp_path: Path) -> None:
    chemin = _journal(tmp_path, _DEBUT, _BLOCK, _courant())

    refus = refus_precedent(chemin, _T)

    assert refus is not None
    assert refus.porte == "securite"
    assert "Path Traversal CRITIQUE" in refus.motif


def test_other_tickets_lines_are_ignored(tmp_path: Path) -> None:
    autre = _BLOCK.replace(_T, "ticket-002")
    chemin = _journal(tmp_path, _DEBUT, autre, _courant())

    assert refus_precedent(chemin, _T) is None


def test_without_the_current_run_start_line_nothing_is_concluded(tmp_path: Path) -> None:
    chemin = _journal(tmp_path, _DEBUT, _BLOCK)

    assert refus_precedent(chemin, _T) is None


def test_a_missing_or_foreign_log_gives_no_refusal(tmp_path: Path) -> None:
    assert refus_precedent(tmp_path / "absent.md", _T) is None
    assert refus_precedent(None, _T) is None


def test_refus_is_a_plain_value() -> None:
    assert Refus("securite", "m") == Refus("securite", "m")
