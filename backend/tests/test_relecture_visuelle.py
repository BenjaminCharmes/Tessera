"""Visual check in `relire` mode: the PR waits for a human — ticket-619, ADR-062."""
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from tessera.models.ticket import TicketStatus
from tessera.services import pipeline_approbation, pipeline_capture
from tessera.services.controle_visuel import ControleVisuel, lire_le_controle
from tessera.services.etape_de_capture import ResultatCapture
from tessera.services.livraison import Livraison
from tessera.services.orchestrator import Orchestrator
from tessera.services.pipeline_approbation import retenir_pour_relecture
from tessera.services.pipeline_capture import capturer_le_run
from tessera.services.pipeline_events import OrchestratorEvent, PipelineResult


def _declarer(projet: Path, mode: str = "relire", **extra: object) -> ControleVisuel:
    captures: dict[str, object] = {
        **extra,
        "url": "http://localhost:{port}",
        "ecrans": [{"nom": "accueil", "chemin": "/"}],
        "largeurs": [390],
        "themes": ["clair"],
        "interface": ["app/"],
        "demarrage": {"commande": "npm run dev -- -p {port}", "delai_s": 5},
    }
    (projet / "agents.json").write_text(
        json.dumps({"pipeline": {"controle_visuel": mode}, "captures": captures}),
        encoding="utf-8",
    )
    controle = lire_le_controle(projet)
    assert controle is not None
    return controle


def _orch(projet: Path, fichiers: list[str], controle: ControleVisuel | None) -> Any:
    diff = "".join(
        f"diff --git a/{f} b/{f}\n--- a/{f}\n+++ b/{f}\n@@ -1 +1 @@\n-a\n+b\n" for f in fichiers
    )

    async def diff_depuis_base() -> str:
        return diff

    journal: list[str] = []
    return SimpleNamespace(
        _controle_visuel=controle,
        _worktree=SimpleNamespace(projet=projet / "wt"),
        _depot=projet,
        _git_workspace=SimpleNamespace(diff_depuis_base=diff_depuis_base),
        _log=journal.append,
        journal=journal,
    )


def _resultat(approuve: bool = True) -> PipelineResult:
    return PipelineResult(
        ticket_id="ticket-1", final_status=TicketStatus.done, rounds=1, approved=approuve
    )


def _prises(monkeypatch: pytest.MonkeyPatch, prise: ResultatCapture) -> None:
    async def faux(*_a: Any, **_kw: Any) -> ResultatCapture:
        return prise

    monkeypatch.setattr(pipeline_capture, "prendre_les_captures", faux)


async def _rien(_e: OrchestratorEvent) -> None:
    return None


async def _passer(orch: Any, resultat: PipelineResult | None = None) -> str | None:
    return await capturer_le_run(cast(Any, orch), resultat or _resultat(), "demo", _rien)


_PRISES = ResultatCapture(["accueil-390-clair.png"], demarrage_ms=10, capture_ms=20)
_ECHEC = ResultatCapture(cause="l'app n'a pas répondu", demarrage_ms=10)


async def test_relire_with_captures_taken_asks_for_a_reading(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prises(monkeypatch, _PRISES)
    relecture = await _passer(_orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path)))
    assert relecture is not None and "1 capture(s) prise(s)" in relecture


async def test_relire_with_failed_captures_asks_for_a_reading_and_logs_the_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prises(monkeypatch, _ECHEC)
    orch = _orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path))
    relecture = await _passer(orch)
    assert relecture is not None and "l'app n'a pas répondu" in relecture
    assert "échec — l'app n'a pas répondu" in orch.journal[0]


async def test_relire_without_worktree_is_a_stop_too(tmp_path: Path) -> None:
    orch = _orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path))
    orch._worktree = None
    relecture = await _passer(orch)
    assert relecture is not None and "pas de worktree" in relecture


async def test_relire_with_a_missing_token_is_a_stop_too(tmp_path: Path) -> None:
    session = {"chemin": "/api/session", "jeton_env": "DEMO_TOKEN", "fichier_env": ".env"}
    orch = _orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path, session=session))
    relecture = await _passer(orch)
    assert relecture is not None and "DEMO_TOKEN" in relecture


async def test_relire_with_a_diff_without_interface_file_changes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prises(monkeypatch, _PRISES)
    assert await _passer(_orch(tmp_path, ["backend/api.py"], _declarer(tmp_path))) is None


async def test_joindre_changes_nothing_even_when_it_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prises(monkeypatch, _ECHEC)
    orch = _orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path, "joindre"))
    assert await _passer(orch) is None


async def test_a_project_without_declaration_changes_nothing(tmp_path: Path) -> None:
    assert await _passer(_orch(tmp_path, ["app/page.tsx"], None)) is None


async def test_an_unapproved_run_asks_for_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _prises(monkeypatch, _PRISES)
    orch = _orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path))
    assert await _passer(orch, _resultat(approuve=False)) is None


def test_an_open_pr_is_kept_from_the_watcher_with_the_reason() -> None:
    retenue = retenir_pour_relecture(
        Livraison(pr_number=7, pushed_sha="abc"), "captures échouées (démarrage)"
    )
    assert retenue.pr_number == 7 and retenue.pushed_sha == "abc"
    assert retenue.arret is not None
    assert "captures échouées (démarrage)" in retenue.arret and "#7" in retenue.arret


def test_an_orphan_pr_is_not_watched_either() -> None:
    orpheline = Livraison(pr_number=7, arret="Livraison interrompue : x", pr_orpheline=True)
    retenue = retenir_pour_relecture(orpheline, "1 capture(s) prise(s)")
    assert retenue.pr_orpheline is False
    assert retenue.arret is not None and retenue.arret.startswith("Livraison interrompue : x")


def test_without_a_reading_or_without_a_pr_the_delivery_is_unchanged() -> None:
    ouverte = Livraison(pr_number=7)
    assert retenir_pour_relecture(ouverte, None) == ouverte
    sans_pr = Livraison(arret="Rebase refusé")
    assert retenir_pour_relecture(sans_pr, "1 capture(s) prise(s)") == sans_pr


class _Double(Orchestrator):
    def __init__(self, resultat: PipelineResult, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._resultat = resultat

    async def _run_pipeline(self, *_a: Any, **_kw: Any) -> PipelineResult:
        return self._resultat


async def _livrer_et_surveiller(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, relecture: str | None
) -> tuple[PipelineResult, list[int]]:
    async def capture(*_a: Any, **_kw: Any) -> str | None:
        return relecture

    monkeypatch.setattr(pipeline_approbation, "capturer_le_run", capture)
    surveilles: list[int] = []

    async def livrer(_r: PipelineResult) -> Livraison:
        return Livraison(pr_number=7)

    async def surveiller(_p: str, _t: str, pr: int, _on: Any) -> None:
        surveilles.append(pr)

    tickets = AsyncMock()
    tickets.get_ticket.return_value = None
    orch = _Double(
        _resultat(),
        runner=MagicMock(),
        ticket_service=tickets,
        project_context="ctx",
        agent_configs=[],
        pipeline_log_path=tmp_path / "memory" / "log.md",
        livrer=livrer,
        surveiller=surveiller,
    )
    return await orch.run_pipeline("proj", "ticket-1", _rien), surveilles


async def test_the_watcher_does_not_receive_a_pr_to_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resultat, surveilles = await _livrer_et_surveiller(tmp_path, monkeypatch, "1 capture(s) prise(s)")
    assert surveilles == []
    assert resultat.final_status is TicketStatus.done
    assert resultat.livraison is not None and resultat.livraison.pr_number == 7
    assert resultat.livraison.arret is not None and "relire" in resultat.livraison.arret


async def test_without_a_reading_the_watcher_gets_the_pr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    resultat, surveilles = await _livrer_et_surveiller(tmp_path, monkeypatch, None)
    assert surveilles == [7]
    assert resultat.livraison is not None and resultat.livraison.arret is None
