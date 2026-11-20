"""The `signaler` tool: queued, project read from the run, refusals, roles — ticket-863."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tessera.config import settings
from tessera.services.pipeline.signalements_en_attente import chemin_attente, mettre_en_attente
from tessera.services.providers.agent_sdk import _build_options
from tessera.services.providers.signal_agent import SOURCE_PROFESSIONNELLE
from tessera.services.providers.signaler import (
    ERREUR_INTERNE,
    ROLES_SANS_SIGNALER,
    SIGNALER_TOOL_NAME,
    CompteurRun,
    ContexteSignal,
    Deposer,
    build_signaler_tool,
    role_recoit_signaler,
)
from tests.test_agent_runner import _make_ticket, _runner
from tests.test_providers_base import FakeProvider

TEXTE_LIBRE = "texte libre du projet"


@pytest.fixture(autouse=True)
def _etat_isole(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ide_state_dir", tmp_path / "etat")


def _args(**remplacements: object) -> dict[str, object]:
    args: dict[str, object] = {
        "titre": "La garde d'écriture refuse un fichier du projet",
        "description": f"Un Write sous tickets/ est refusé ; {TEXTE_LIBRE}.",
        "categorie": "garde_trop_strict",
        "composant": "garde_ecriture",
    }
    args.update(remplacements)
    return args


def _contexte(
    deposer: Deposer = mettre_en_attente,
    *,
    confidentialite: str = "personal",
    role: str = "codeur",
    compteur: CompteurRun | None = None,
) -> ContexteSignal:
    return ContexteSignal(
        projet="mon-projet",
        ticket="ticket-863",
        role=role,
        confidentialite=confidentialite,
        deposer=deposer,
        compteur=compteur or CompteurRun(),
    )


async def _appeler(contexte: ContexteSignal, args: dict[str, object]) -> str:
    resultat: dict[str, Any] = await build_signaler_tool(contexte).handler(args)
    return " ".join(bloc["text"] for bloc in resultat["content"])


def _file() -> list[dict[str, str]]:
    chemin = chemin_attente()
    return json.loads(chemin.read_text(encoding="utf-8")) if chemin.is_file() else []


async def test_accepted_report_is_queued_not_written_into_the_repository(tmp_path: Path) -> None:
    depot = tmp_path / "depot"
    depot.mkdir()

    reponse = await _appeler(_contexte(), _args())

    assert "reçu" in reponse
    file = _file()
    assert len(file) == 1
    assert file[0]["type"] == "fix"
    assert file[0]["titre"] == _args()["titre"]
    assert "agent:codeur@ticket-863" in file[0]["corps"]
    assert "Nature : bug" in file[0]["corps"]
    assert list(depot.rglob("*")) == []


async def test_source_project_comes_from_the_run_not_the_arguments() -> None:
    outil = build_signaler_tool(_contexte())

    await outil.handler(_args(projet="projet-usurpe", ticket="ticket-999", role="reviewer"))

    corps = _file()[0]["corps"]
    assert "Projet source : mon-projet" in corps
    assert "projet-usurpe" not in corps
    assert "agent:codeur@ticket-863" in corps
    assert "projet" not in outil.input_schema["properties"]  # type: ignore[call-overload]


async def test_refusal_is_returned_to_the_agent_without_failing_the_turn() -> None:
    reponse = await _appeler(_contexte(), _args(categorie="inconnue"))

    assert "Signalement refusé" in reponse
    assert _file() == []


async def test_a_duplicate_is_refused_and_a_fault_does_not_raise() -> None:
    contexte = _contexte()
    await _appeler(contexte, _args())

    doublon = await _appeler(_contexte(), _args())
    assert "déjà signalé" in doublon
    assert len(_file()) == 1

    def _casse(titre: str, type_ticket: str, corps: str) -> int:
        raise OSError("disque plein")

    panne = await _appeler(_contexte(_casse), _args(titre="Un autre défaut de l'outil"))
    assert panne == ERREUR_INTERNE


async def test_the_run_counter_bounds_the_reports_across_roles() -> None:
    compteur = CompteurRun()
    for rang in range(3):
        reponse = await _appeler(_contexte(compteur=compteur), _args(titre=f"Défaut numéro {rang} distinct"))
        assert "reçu" in reponse

    quatrieme = await _appeler(_contexte(role="reviewer", compteur=compteur), _args(titre="Un quatrième"))

    assert "3 par run" in quatrieme
    assert len(_file()) == 3


async def test_professional_project_report_carries_no_free_text() -> None:
    contexte = _contexte(confidentialite="professional")

    await _appeler(contexte, _args())

    corps = _file()[0]["corps"]
    assert TEXTE_LIBRE not in corps
    assert "mon-projet" not in corps
    assert SOURCE_PROFESSIONNELLE in corps
    assert "## Description" not in corps
    assert _file()[0]["titre"] == "[codeur] garde_trop_strict — garde_ecriture"


def test_tool_name_is_in_allowed_tools_for_tooled_roles() -> None:
    options = _build_options(
        system="s", model="m", max_turns=3, max_budget_usd=1.0, cwd=None,
        allowed_tools=["Read"], signaler=_contexte(),
    )

    assert SIGNALER_TOOL_NAME == "mcp__tessera__signaler"
    assert "tessera" in options.mcp_servers
    assert SIGNALER_TOOL_NAME in (options.allowed_tools or [])
    assert SIGNALER_TOOL_NAME in (options.tools or [])


def test_without_a_context_the_tool_is_not_exposed() -> None:
    options = _build_options(
        system="s", model="m", max_turns=3, max_budget_usd=1.0, cwd=None,
        allowed_tools=["Read"],
    )

    assert options.mcp_servers == {}
    assert SIGNALER_TOOL_NAME not in (options.allowed_tools or [])


def test_toolless_roles_and_the_supervisor_do_not_get_it() -> None:
    sans_outils = _build_options(
        system="s", model="m", max_turns=3, max_budget_usd=1.0, cwd=None,
        allowed_tools=[], signaler=_contexte(),
    )
    superviseur = _build_options(
        system="s", model="m", max_turns=3, max_budget_usd=1.0, cwd=None,
        allowed_tools=["Read"], signaler=_contexte(role="superviseur"),
    )

    for options in (sans_outils, superviseur):
        assert options.mcp_servers == {}
        assert SIGNALER_TOOL_NAME not in (options.allowed_tools or [])
    assert ROLES_SANS_SIGNALER == {"lecons", "validateur", "superviseur"}
    assert role_recoit_signaler("codeur") and role_recoit_signaler("architect")


@pytest.mark.parametrize("role", sorted(ROLES_SANS_SIGNALER))
async def test_the_runner_withholds_the_context_from_those_roles(
    tmp_path: Path, role: str
) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    (prompts / f"{role}.md").write_text(f"Tu es le {role}.", encoding="utf-8")
    provider = FakeProvider()

    await _runner(tmp_path, provider).run(
        role, _make_ticket(), "ctx", signaler=_contexte(role="codeur")
    )

    assert "signaler" not in provider.calls[0]


async def test_the_runner_hands_the_context_to_a_tooled_role_with_its_own_role(
    tmp_path: Path,
) -> None:
    provider = FakeProvider()
    contexte = _contexte()

    await _runner(tmp_path, provider).run("architect", _make_ticket(), "ctx", signaler=contexte)

    recu = provider.calls[0]["signaler"]
    assert recu.role == "architect"
    assert recu.compteur is contexte.compteur
    assert recu.projet == "mon-projet"


async def _rien(_evenement: object) -> None:
    return None


def _contexte_du_run(chemin: Path | None) -> ContexteSignal | None:
    from types import SimpleNamespace

    from tessera.services.pipeline.pipeline_run import PipelineRun
    from tessera.services.pipeline.signaler_du_run import signaler_for

    run = PipelineRun(project_id="mon-projet", ticket=_make_ticket(id="ticket-863"), on_event=_rien)
    return signaler_for(SimpleNamespace(_project_path=chemin), run)  # type: ignore[arg-type]


def test_the_run_context_is_read_from_the_run_and_the_project_manifest(tmp_path: Path) -> None:
    (tmp_path / "agents.json").write_text('{"confidentiality": "professional"}', encoding="utf-8")

    contexte = _contexte_du_run(tmp_path)

    assert contexte is not None
    assert (contexte.projet, contexte.ticket) == ("mon-projet", "ticket-863")
    assert contexte.confidentialite == "professional"


def test_a_run_without_a_project_folder_gets_no_context() -> None:
    assert _contexte_du_run(None) is None
