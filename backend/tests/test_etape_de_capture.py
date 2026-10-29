"""The capture step of a run — ticket-618, ADR-062 (mode `joindre`)."""
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from tessera.config import settings
from tessera.services import pipeline_capture
from tessera.services.captures import CapturesEchouees, dossier_des_captures
from tessera.services.captures_config import ConfigCaptures
from tessera.services.controle_visuel import ControleVisuel, lire_le_controle
from tessera.services.etape_de_capture import ResultatCapture, prendre_les_captures
from tessera.services.pipeline_capture import capturer_le_run
from tessera.services.pipeline_events import EventType, OrchestratorEvent, PipelineResult
from tessera.models.ticket import TicketStatus

JETON = "s3cr3t-token-618"


class _App:
    def __init__(self, sortie: int | None = None) -> None:
        self.sortie = sortie
        self.arretee = False

    @property
    def code_de_sortie(self) -> int | None:
        return self.sortie

    async def arreter(self) -> None:
        self.arretee = True


class _Demarreur:
    """Stands in for the launcher: records the command and the folder."""

    def __init__(self, app: _App) -> None:
        self.app = app
        self.appels: list[tuple[list[str], Path]] = []

    async def __call__(self, args: list[str], cwd: Path) -> _App:
        self.appels.append((args, cwd))
        return self.app


async def _repond(_url: str) -> bool:
    return True


async def _ne_repond_pas(_url: str) -> bool:
    return False


@pytest.fixture(autouse=True)
def etat(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")


def _declarer(projet: Path, interface: list[str] | None = None, **extra: object) -> ControleVisuel:
    captures: dict[str, object] = {
        "url": "http://localhost:{port}",
        "ecrans": [{"nom": "accueil", "chemin": "/"}],
        "largeurs": [390],
        "themes": ["clair"],
        "interface": interface if interface is not None else ["app/"],
        "demarrage": {"commande": "npm run dev -- -p {port}", "delai_s": 5},
        **extra,
    }
    pipeline = {"controle_visuel": "joindre"}
    (projet / "agents.json").write_text(
        json.dumps({"pipeline": pipeline, "captures": captures}), encoding="utf-8"
    )
    controle = lire_le_controle(projet)
    assert controle is not None
    return controle


async def _ecrit_les_images(config: ConfigCaptures, sortie: Path, _jeton: str | None) -> None:
    for nom in ("accueil-390-clair.png",):
        (sortie / nom).write_bytes(b"png")


async def test_command_starts_in_the_worktree_on_a_free_port(tmp_path: Path) -> None:
    controle = _declarer(tmp_path)
    demarreur = _Demarreur(_App())
    resultat = await prendre_les_captures(
        controle, tmp_path / "wt", "demo", "ticket-1", demarreur=demarreur,
        executeur=_ecrit_les_images, sonde=_repond, choisir_port=lambda: 5444,
    )
    assert demarreur.appels == [(["npm", "run", "dev", "--", "-p", "5444"], tmp_path / "wt")]
    assert resultat.images == ["accueil-390-clair.png"] and resultat.cause is None
    assert demarreur.app.arretee
    assert (dossier_des_captures("demo", "ticket-1") / "accueil-390-clair.png").is_file()


async def test_a_start_that_dies_is_reported_and_stopped(tmp_path: Path) -> None:
    app = _App(sortie=1)
    resultat = await prendre_les_captures(
        _declarer(tmp_path), tmp_path, "demo", "ticket-1", demarreur=_Demarreur(app),
        sonde=_ne_repond_pas, pause_s=0,
    )
    assert resultat.cause is not None and "code 1" in resultat.cause
    assert resultat.images == [] and app.arretee


async def test_a_start_past_its_delay_is_reported_and_stopped(tmp_path: Path) -> None:
    controle = _declarer(tmp_path)
    delai_nul = ControleVisuel(
        controle.mode, controle.captures, controle.interface,
        type(controle.demarrage)(controle.demarrage.commande, delai_s=0),
    )
    app = _App()
    resultat = await prendre_les_captures(
        delai_nul, tmp_path, "demo", "ticket-1", demarreur=_Demarreur(app),
        sonde=_ne_repond_pas, pause_s=0,
    )
    assert resultat.cause is not None and "n'a pas répondu" in resultat.cause
    assert app.arretee


async def test_missing_images_are_a_failure_and_the_app_is_stopped(tmp_path: Path) -> None:
    async def rien(_c: ConfigCaptures, _s: Path, _j: str | None) -> None:
        return None

    app = _App()
    resultat = await prendre_les_captures(
        _declarer(tmp_path), tmp_path, "demo", "ticket-1", demarreur=_Demarreur(app),
        executeur=rien, sonde=_repond,
    )
    assert resultat.cause is not None and "manquantes" in resultat.cause
    assert app.arretee


async def test_the_process_is_stopped_when_the_step_raises(tmp_path: Path) -> None:
    async def plante(_c: ConfigCaptures, _s: Path, _j: str | None) -> None:
        raise RuntimeError("playwright a planté")

    app = _App()
    resultat = await prendre_les_captures(
        _declarer(tmp_path), tmp_path, "demo", "ticket-1", demarreur=_Demarreur(app),
        executeur=plante, sonde=_repond,
    )
    assert app.arretee
    assert resultat.cause is not None and "planté" in resultat.cause


async def test_the_token_is_masked_in_every_failure(tmp_path: Path) -> None:
    async def plante(_c: ConfigCaptures, _s: Path, jeton: str | None) -> None:
        raise CapturesEchouees(f"401 avec {jeton}")

    resultat = await prendre_les_captures(
        _declarer(tmp_path), tmp_path, "demo", "ticket-1", JETON,
        demarreur=_Demarreur(_App()), executeur=plante, sonde=_repond,
    )
    assert resultat.cause is not None and JETON not in resultat.cause and "***" in resultat.cause


def _orch(projet: Path, fichiers: list[str], controle: ControleVisuel | None) -> Any:
    diff = "".join(f"diff --git a/{f} b/{f}\n--- a/{f}\n+++ b/{f}\n@@ -1 +1 @@\n-a\n+b\n" for f in fichiers)

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


@pytest.fixture
def prises(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Any, ...]]:
    appels: list[tuple[Any, ...]] = []

    async def faux(*args: Any, **_kw: Any) -> ResultatCapture:
        appels.append(args)
        return ResultatCapture(["accueil-390-clair.png"], demarrage_ms=4200, capture_ms=8100)

    monkeypatch.setattr(pipeline_capture, "prendre_les_captures", faux)
    return appels


async def _passer(orch: Any, resultat: PipelineResult | None = None) -> list[OrchestratorEvent]:
    evenements: list[OrchestratorEvent] = []

    async def on_event(e: OrchestratorEvent) -> None:
        evenements.append(e)

    await capturer_le_run(cast(Any, orch), resultat or _resultat(), "demo", on_event)
    return evenements


async def test_a_project_without_declaration_starts_nothing(
    tmp_path: Path, prises: list[tuple[Any, ...]]
) -> None:
    orch = _orch(tmp_path, ["app/page.tsx"], None)
    assert await _passer(orch) == []
    assert prises == [] and orch.journal == []


async def test_a_diff_without_interface_file_starts_nothing(
    tmp_path: Path, prises: list[tuple[Any, ...]]
) -> None:
    orch = _orch(tmp_path, ["backend/api.py"], _declarer(tmp_path))
    assert await _passer(orch) == []
    assert prises == [] and orch.journal == []


async def test_an_unapproved_run_starts_nothing(
    tmp_path: Path, prises: list[tuple[Any, ...]]
) -> None:
    orch = _orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path))
    assert await _passer(orch, _resultat(approuve=False)) == []
    assert prises == []


async def test_the_log_line_and_the_event_carry_both_durations(
    tmp_path: Path, prises: list[tuple[Any, ...]]
) -> None:
    orch = _orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path))
    evenements = await _passer(orch)
    assert prises[0][1] == tmp_path / "wt"
    assert orch.journal == [
        "[ticket-1] captures: 1 image(s) — démarrage 4200 ms, capture 8100 ms"
    ]
    assert [e.type for e in evenements] == [EventType.VISUAL_CHECK]
    assert evenements[0].data["startup_ms"] == 4200 and evenements[0].data["outcome"] == "captured"


async def test_a_missing_token_is_a_logged_failure_naming_the_variable(
    tmp_path: Path, prises: list[tuple[Any, ...]]
) -> None:
    session = {"chemin": "/api/session", "jeton_env": "DEMO_TOKEN", "fichier_env": ".env"}
    orch = _orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path, session=session))
    evenements = await _passer(orch)
    assert prises == []
    assert "DEMO_TOKEN" in orch.journal[0] and evenements[0].data["outcome"] == "failed"


async def test_the_token_reaches_neither_the_log_nor_the_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = {"chemin": "/api/session", "jeton_env": "DEMO_TOKEN", "fichier_env": ".env"}
    (tmp_path / ".env").write_text(f"DEMO_TOKEN={JETON}\n", encoding="utf-8")
    orch = _orch(tmp_path, ["app/page.tsx"], _declarer(tmp_path, session=session))

    async def echoue(*args: Any, **_kw: Any) -> ResultatCapture:
        assert args[4] == JETON
        return ResultatCapture(cause="session refusée", demarrage_ms=10)

    monkeypatch.setattr(pipeline_capture, "prendre_les_captures", echoue)
    evenements = await _passer(orch)
    assert JETON not in orch.journal[0] and JETON not in json.dumps(evenements[0].data)
    assert "échec — session refusée" in orch.journal[0]
