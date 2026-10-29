"""Un tour qui laisse deux fiches au même identifiant repart au producteur — ticket-526."""
from pathlib import Path

from tessera.models.agent import AgentResult, AgentRole
from tessera.services.pipeline_run import PipelineRun
from tessera.services.pipeline_tickets import (
    problemes_nouveaux,
    relever_etat_initial,
    renvoyer_si_problemes,
)
from tests.test_orchestrator import (
    _FakeGit,
    _make_orchestrator,
    _make_ticket,
    _noop,
    _RecordingRunner,
)

_FICHE = """---
id: {id}
title: "Une fiche"
type: feat
status: {status}
priority: medium
agent: codeur
---

# {id}
"""


def _fiche(racine: Path, dossier: str, nom: str, ticket_id: str) -> Path:
    repertoire = racine / "tickets" / dossier
    repertoire.mkdir(parents=True, exist_ok=True)
    chemin = repertoire / f"{nom}.md"
    chemin.write_text(_FICHE.format(id=ticket_id, status=dossier), encoding="utf-8")
    return chemin


def _journal(racine: Path) -> str:
    chemin = racine / "memory" / "pipeline-log.md"
    return chemin.read_text(encoding="utf-8") if chemin.exists() else ""


class _CodeurQuiEcrit(_RecordingRunner):
    """Runner whose first coder turn runs ``au_premier_tour``, the next ``au_suivant``."""

    def __init__(self, au_premier_tour: list[Path], au_suivant: list[Path]) -> None:
        super().__init__()
        self._a_ecrire = au_premier_tour
        self._a_supprimer = au_suivant

    async def run(self, **kwargs: object) -> AgentResult:
        if kwargs["role"] == AgentRole.codeur:
            if not self.calls:
                for chemin in self._a_ecrire:
                    chemin.parent.mkdir(parents=True, exist_ok=True)
                    chemin.write_text(
                        _FICHE.format(id="ticket-517", status="todo"), encoding="utf-8"
                    )
            else:
                for chemin in self._a_supprimer:
                    chemin.unlink(missing_ok=True)
        return await super().run(**kwargs)


def _tours_codeur(runner: _RecordingRunner) -> list[dict[str, object]]:
    return [c for c in runner.calls if c["role"] == AgentRole.codeur]


async def _lancer(racine: Path, runner: _RecordingRunner) -> None:
    orchestrateur = _make_orchestrator(
        racine, runner=runner, git_workspace=_FakeGit(), project_path=racine  # type: ignore[arg-type]
    )
    await orchestrateur.run_pipeline("projet", "ticket-001", _noop)


async def test_round_leaving_a_duplicate_id_goes_back_to_the_producer(tmp_path: Path) -> None:
    existante = _fiche(tmp_path, "todo", "ticket-517-a", "ticket-517")
    doublon = tmp_path / "tickets" / "todo" / "ticket-517-b.md"
    runner = _CodeurQuiEcrit([doublon], [doublon])
    # La fiche d'origine existe déjà : l'état de départ n'a aucun défaut.
    assert existante.exists()

    await _lancer(tmp_path, runner)

    tours = _tours_codeur(runner)
    assert len(tours) == 2
    contexte = str(tours[1]["project_context"])
    assert "ticket-517" in contexte
    assert "tickets/todo/ticket-517-a.md" in contexte
    assert "tickets/todo/ticket-517-b.md" in contexte


async def test_round_without_ticket_problem_is_not_affected(tmp_path: Path) -> None:
    _fiche(tmp_path, "todo", "ticket-517-a", "ticket-517")
    runner = _CodeurQuiEcrit([], [])

    await _lancer(tmp_path, runner)

    assert len(_tours_codeur(runner)) == 1
    assert "tickets:" not in _journal(tmp_path)


async def test_old_duplicate_outside_the_run_does_not_block_it(tmp_path: Path) -> None:
    _fiche(tmp_path, "todo", "ticket-517-a", "ticket-517")
    _fiche(tmp_path, "done", "ticket-517-b", "ticket-517")
    runner = _CodeurQuiEcrit([], [])

    await _lancer(tmp_path, runner)

    assert len(_tours_codeur(runner)) == 1
    assert "tickets:" not in _journal(tmp_path)


async def test_problem_is_written_to_the_pipeline_log(tmp_path: Path) -> None:
    _fiche(tmp_path, "todo", "ticket-517-a", "ticket-517")
    doublon = tmp_path / "tickets" / "todo" / "ticket-517-b.md"
    runner = _CodeurQuiEcrit([doublon], [doublon])

    await _lancer(tmp_path, runner)

    journal = _journal(tmp_path)
    assert "[ticket-001] tickets: 2 problème(s) — " in journal
    assert "ticket-517-b.md" in journal


async def test_renvoyer_si_problemes_reports_nothing_on_a_sound_project(
    tmp_path: Path,
) -> None:
    _fiche(tmp_path, "todo", "ticket-001-a", "ticket-001")
    orchestrateur = _make_orchestrator(tmp_path, project_path=tmp_path)
    run = PipelineRun(project_id="projet", ticket=_make_ticket(), on_event=_noop)

    await relever_etat_initial(orchestrateur, run)

    assert await renvoyer_si_problemes(orchestrateur, run) is False
    assert run.review_feedback == []


async def test_problemes_nouveaux_ignores_what_the_baseline_already_holds(
    tmp_path: Path,
) -> None:
    _fiche(tmp_path, "todo", "ticket-517-a", "ticket-517")
    _fiche(tmp_path, "done", "ticket-517-b", "ticket-517")
    orchestrateur = _make_orchestrator(tmp_path, project_path=tmp_path)
    run = PipelineRun(project_id="projet", ticket=_make_ticket(), on_event=_noop)
    await relever_etat_initial(orchestrateur, run)
    assert await problemes_nouveaux(orchestrateur, run) == []

    _fiche(tmp_path, "todo", "ticket-518-a", "ticket-518")
    _fiche(tmp_path, "todo", "ticket-518-b", "ticket-518")

    nouveaux = await problemes_nouveaux(orchestrateur, run)
    assert {p.valeur for p in nouveaux} == {"ticket-518"}
    assert len(nouveaux) == 2


async def test_without_project_path_nothing_is_checked(tmp_path: Path) -> None:
    orchestrateur = _make_orchestrator(tmp_path)
    run = PipelineRun(project_id="projet", ticket=_make_ticket(), on_event=_noop)

    await relever_etat_initial(orchestrateur, run)

    assert await renvoyer_si_problemes(orchestrateur, run) is False


def test_architect_prompt_asks_for_the_next_number_and_deleting_replaced_cards() -> None:
    chemin = Path(__file__).resolve().parents[2] / "agents" / "prompts" / "architect.md"
    prompt = " ".join(chemin.read_text(encoding="utf-8").split())
    assert "suivant le plus grand déjà pris, tous dossiers confondus" in prompt
    assert "scripts/prochain_numero.py ticket" in prompt
    assert "scripts/prochain_numero.py adr" in prompt
    assert "se **supprime**" in prompt
