"""An approved run that corrected a failure proposes one lesson (ticket-803).

Le fournisseur est toujours un double : aucun test n'appelle un vrai modèle.
"""
import json
from datetime import date
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from tessera.models.ticket import Ticket, TicketPriority, TicketStatus, TicketType
from tessera.services import lecons_run, pipeline_outcomes as outcomes
from tessera.services.gardes.lecons import lire_lecons
from tessera.services.lecons_run import produire_lecon, proposer_lecon
from tessera.services.pipeline_events import OrchestratorEvent
from tessera.services.pipeline_run import PipelineRun
from tessera.services.project_loader import load_pipeline_config
from tessera.services.providers.base import ProviderResult
from tests.doubles_git import GitWorkspaceDouble

RETOUR = (
    "Les tests sont rouges : FakeWorkspace ne définit pas la nouvelle méthode "
    "ajoutée à GitWorkspaceService, trois doubles de test sont à mettre à jour."
)
PREUVE = "FakeWorkspace ne définit pas la nouvelle méthode"
LECON = (
    "Quand une méthode s'ajoute à `GitWorkspaceService`, chercher les doubles de test "
    "qui la redéfinissent et les mettre à jour dans le même commit."
)


class _Fournisseur:
    """A provider double answering a fixed text, counting its calls."""

    name = "double"

    def __init__(self, contenu: str | Exception) -> None:
        self.contenu = contenu
        self.appels: list[dict[str, Any]] = []

    async def complete(self, **kwargs: Any) -> ProviderResult:
        self.appels.append(kwargs)
        if isinstance(self.contenu, Exception):
            raise self.contenu
        return ProviderResult(content=self.contenu)


def _reponse(lecon: str | None, preuve: str | None) -> str:
    return json.dumps({"lecon": lecon, "preuve": preuve})


async def _produire(
    fournisseur: _Fournisseur, memory: Path, retours: list[str] | None = None
) -> tuple[bool, list[str]]:
    journal: list[str] = []
    ecrit = await produire_lecon(
        fournisseur=fournisseur,  # type: ignore[arg-type]
        modele="m", systeme="s", ticket_id="ticket-736",
        retours=[RETOUR] if retours is None else retours,
        diff="diff --git a/x b/x", memory_dir=memory, jour=date(2026, 11, 5),
        journal=journal.append,
    )
    return ecrit, journal


async def test_produire_lecon_writes_one_proposed_line_with_source(tmp_path: Path) -> None:
    fournisseur = _Fournisseur(_reponse(LECON, PREUVE))
    ecrit, journal = await _produire(fournisseur, tmp_path)
    assert ecrit is True
    assert lire_lecons(tmp_path).proposees == (f"{LECON} (source : ticket-736, 2026-11-05)",)
    assert fournisseur.appels[0]["schema"] == lecons_run.SCHEMA
    assert "RETOUR" not in journal[-1] and "proposée" in journal[-1]


async def test_produire_lecon_without_feedback_does_not_call_the_provider(tmp_path: Path) -> None:
    fournisseur = _Fournisseur(_reponse(LECON, PREUVE))
    ecrit, _ = await _produire(fournisseur, tmp_path, retours=["  ", ""])
    assert ecrit is False
    assert fournisseur.appels == []
    assert not (tmp_path / "lecons.md").exists()


@pytest.mark.parametrize(
    ("contenu", "motif"),
    [
        (_reponse(None, None), "rien à retenir"),
        ("pas du json", "échec"),
        (json.dumps({"autre": 1}), "échec"),
        (json.dumps({"lecon": 3, "preuve": "x"}), "échec"),
        (_reponse(LECON, "un passage inventé de plus de vingt signes"), "preuve"),
        (_reponse("Quand conftest.py change, tout relire.", PREUVE), "configuration"),
        (RuntimeError("provider indisponible"), "échec"),
    ],
)
async def test_produire_lecon_failures_write_nothing_and_say_why(
    tmp_path: Path, contenu: str | Exception, motif: str
) -> None:
    ecrit, journal = await _produire(_Fournisseur(contenu), tmp_path)
    assert ecrit is False
    assert not (tmp_path / "lecons.md").exists()
    assert motif in journal[-1]


async def test_produire_lecon_refuses_a_duplicate(tmp_path: Path) -> None:
    await _produire(_Fournisseur(_reponse(LECON, PREUVE)), tmp_path)
    ecrit, journal = await _produire(_Fournisseur(_reponse(LECON, PREUVE)), tmp_path)
    assert ecrit is False
    assert "doublon" in journal[-1]
    assert len(lire_lecons(tmp_path).proposees) == 1


async def test_produire_lecon_reports_a_full_file(tmp_path: Path) -> None:
    lignes = "".join(f"- Q{i}\n" for i in range(25))
    (tmp_path / "lecons.md").write_text(
        f"## Proposées\n\n## En vigueur\n{lignes}", encoding="utf-8"
    )
    ecrit, journal = await _produire(_Fournisseur(_reponse(LECON, PREUVE)), tmp_path)
    assert ecrit is False
    assert "plein" in journal[-1]


def test_retour_borne_keeps_the_most_recent_four_kilobytes() -> None:
    ancien, recent = "A" * 3000, "B" * 3000
    borne = lecons_run.retour_borne([ancien, recent])
    assert len(borne.encode("utf-8")) <= lecons_run.RETOUR_MAX_OCTETS
    assert borne.endswith("B" * 3000)
    assert "A" * 3000 not in borne


# ------------------------------------------------------------------
# Le pipeline : opt-in, dossier du run, run approuvé seulement
# ------------------------------------------------------------------


def _projet(racine: Path, lecons: bool | None) -> Path:
    projet = racine / "proj"
    (projet / "memory").mkdir(parents=True)
    pipeline: dict[str, Any] = {} if lecons is None else {"lecons": lecons}
    (projet / "agents.json").write_text(
        json.dumps({"agents": [], "pipeline": pipeline}), encoding="utf-8"
    )
    return projet


def test_load_pipeline_config_reads_the_lessons_flag(tmp_path: Path) -> None:
    assert load_pipeline_config(_projet(tmp_path / "a", True)).lecons is True
    assert load_pipeline_config(_projet(tmp_path / "b", False)).lecons is False
    assert load_pipeline_config(_projet(tmp_path / "c", None)).lecons is False


class _Orch:
    def __init__(self, projet: Path, worktree: Path | None = None) -> None:
        self._project_path = projet
        self._worktree = SimpleNamespace(projet=worktree) if worktree else None
        self.logs: list[str] = []

    def _log(self, message: str) -> None:
        self.logs.append(message)


def _run(feedback: list[str]) -> PipelineRun:
    async def _on_event(event: OrchestratorEvent) -> None:
        return None

    run = PipelineRun(
        project_id="proj",
        ticket=Ticket(
            id="ticket-736", title="T", type=TicketType.feat,
            status=TicketStatus.in_progress, priority=TicketPriority.medium,
            agent="codeur", body="",
        ),
        on_event=_on_event,
    )
    run.branch = "ticket-736-x"
    run.round_num = 2
    run.review_feedback = list(feedback)
    run.reviewed_code = "diff --git a/x b/x"
    return run


def _brancher(monkeypatch: pytest.MonkeyPatch, fournisseur: _Fournisseur) -> None:
    monkeypatch.setattr(lecons_run, "_fournisseur", lambda *a, **k: fournisseur)


async def test_proposer_lecon_writes_in_the_worktree_never_the_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    projet = _projet(tmp_path, True)
    wt = tmp_path / "wt" / "proj"
    (wt / "memory").mkdir(parents=True)
    _brancher(monkeypatch, _Fournisseur(_reponse(LECON, PREUVE)))

    assert await proposer_lecon(_Orch(projet, wt), _run([RETOUR])) is True  # type: ignore[arg-type]

    assert (wt / "memory" / "lecons.md").is_file()
    assert not (projet / "memory" / "lecons.md").exists()


@pytest.mark.parametrize("drapeau", [False, None])
async def test_proposer_lecon_is_off_without_the_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, drapeau: bool | None
) -> None:
    fournisseur = _Fournisseur(_reponse(LECON, PREUVE))
    _brancher(monkeypatch, fournisseur)
    orch = _Orch(_projet(tmp_path, drapeau))

    assert await proposer_lecon(orch, _run([RETOUR])) is False  # type: ignore[arg-type]
    assert fournisseur.appels == []


async def test_proposer_lecon_without_feedback_does_not_call_the_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fournisseur = _Fournisseur(_reponse(LECON, PREUVE))
    _brancher(monkeypatch, fournisseur)

    assert await proposer_lecon(_Orch(_projet(tmp_path, True)), _run([])) is False  # type: ignore[arg-type]
    assert fournisseur.appels == []


async def test_proposer_lecon_fails_open_when_the_provider_cannot_be_built(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def _casse(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("pas de provider")

    monkeypatch.setattr(lecons_run, "_fournisseur", _casse)
    orch = _Orch(_projet(tmp_path, True))

    assert await proposer_lecon(orch, _run([RETOUR])) is False  # type: ignore[arg-type]
    assert "échec" in orch.logs[-1]


class _Git(GitWorkspaceDouble):
    def __init__(self, memory: Path) -> None:
        self.memory = memory
        self.lecon_au_commit: bool | None = None

    async def commit_all(self, message: str) -> str:
        self.lecon_au_commit = (self.memory / "lecons.md").is_file()
        return "abc1234"


class _Tickets:
    async def update_status(self, ticket_id: str, status: TicketStatus) -> None:
        return None


class _OrchLivraison(_Orch):
    def __init__(self, projet: Path) -> None:
        super().__init__(projet)
        self._git_workspace = _Git(projet / "memory")
        self._ticket_svc = _Tickets()
        self._max_review_rounds = 3


async def test_finish_approved_proposes_the_lesson_before_the_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _brancher(monkeypatch, _Fournisseur(_reponse(LECON, PREUVE)))
    orch = _OrchLivraison(_projet(tmp_path, True))

    resultat = await outcomes.finish_approved(orch, _run([RETOUR]))  # type: ignore[arg-type]

    assert resultat.approved is True
    assert orch._git_workspace.lecon_au_commit is True


async def test_a_run_that_is_not_approved_never_calls_the_provider(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fournisseur = _Fournisseur(_reponse(LECON, PREUVE))
    _brancher(monkeypatch, fournisseur)
    orch = _OrchLivraison(_projet(tmp_path, True))

    resultat = await outcomes.finish_rounds_exhausted(orch, _run([RETOUR]))  # type: ignore[arg-type]

    assert resultat.approved is False
    assert fournisseur.appels == []
    assert not (tmp_path / "proj" / "memory" / "lecons.md").exists()


async def test_a_failing_lesson_step_leaves_the_run_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _brancher(monkeypatch, _Fournisseur(RuntimeError("panne")))
    orch = _OrchLivraison(_projet(tmp_path, True))

    resultat = await outcomes.finish_approved(orch, _run([RETOUR]))  # type: ignore[arg-type]

    assert resultat.approved is True
    assert resultat.final_status is TicketStatus.done
    assert resultat.commit_sha == "abc1234"
