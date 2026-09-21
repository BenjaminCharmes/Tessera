"""A project created from the IDE ships a complete, explicit manifest.

`create_project` only wrote `agents.json` when `active_agents` was non-empty,
and the creation modal sends only `project_id`, `name` and `description`. So a
project created from the UI had **no manifest at all**.

Without one, `load_pipeline_config` returns a default `AgentPipelineConfig()`
where the tester, the security audit and the validator are all off. Those
services are already wired in the router — they were merely switched off, and
nothing said so. The pipeline silently fell back to coder → reviewer.
"""
import json
from pathlib import Path

import pytest

from tessera.config import settings
from tessera.models.project import ProjectCreate
from tessera.routers.projects import create_project
from tessera.services.artifacts import default_mode_for, read_artifact_mode
from tessera.services.autonomie import lire_niveau
from tessera.services.project_loader import load_pipeline_config


@pytest.fixture(autouse=True)
def _workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(settings, "ide_workspace_dir", tmp_path)
    monkeypatch.setattr(settings, "ide_prompts_dir", tmp_path / "prompts")
    return tmp_path


async def _cree(tmp_path: Path) -> Path:
    """Crée un projet comme la modale le fait : sans `active_agents`."""
    await create_project(ProjectCreate(project_id="neuf", name="Neuf"))
    return tmp_path / "neuf"


async def test_un_projet_sans_agents_demandes_a_quand_meme_un_manifeste(
    tmp_path: Path,
) -> None:
    projet = await _cree(tmp_path)

    manifeste = projet / "agents.json"
    assert manifeste.exists(), "aucun agents.json : le pipeline retombe sur les défauts"

    data = json.loads(manifeste.read_text(encoding="utf-8"))
    roles = {a["role"] for a in data["agents"]}
    assert roles == {"codeur", "reviewer"}


async def test_la_securite_et_le_validateur_sont_actifs(tmp_path: Path) -> None:
    """Both services are already wired in the router; they were off only
    because no manifest declared them."""
    projet = await _cree(tmp_path)

    config = load_pipeline_config(projet)
    assert config.securite_enabled is True
    assert config.validateur_enabled is True


async def test_le_testeur_reste_eteint_sans_commande(tmp_path: Path) -> None:
    """A flag set to true without a valid command is worse than a flag set to
    false: the runner swallows the error and returns True, so *no tests at
    all* reads as *tests green*.

    A brand-new project has no stack, so no command can be guessed here.
    """
    projet = await _cree(tmp_path)

    # La clef doit être **écrite**, pas seulement fausse par défaut de
    # lecture : un manifeste muet se lit comme un manifeste qui a choisi.
    data = json.loads((projet / "agents.json").read_text(encoding="utf-8"))
    assert data["pipeline"]["testeur_enabled"] is False
    assert data["pipeline"]["test_command"] is None

    config = load_pipeline_config(projet)
    assert config.testeur_enabled is False
    assert config.test_command is None


async def test_le_niveau_d_autonomie_est_commit(tmp_path: Path) -> None:
    """ADR-029: the default protects. We never write `merge` into a generated
    file — merging is deciding that work is good."""
    projet = await _cree(tmp_path)

    data = json.loads((projet / "agents.json").read_text(encoding="utf-8"))
    assert data["autonomy"] == "commit"

    assert lire_niveau(projet) == "commit"


async def test_le_mode_des_artefacts_est_declare_explicitement(
    tmp_path: Path,
) -> None:
    """ADR-023 fails closed: an unreadable or absent declaration falls back to
    `local`. Writing the value the creation path already chose makes the
    manifest say what it means instead of depending on that fallback."""
    projet = await _cree(tmp_path)

    data = json.loads((projet / "agents.json").read_text(encoding="utf-8"))
    assert data["artifacts"] == default_mode_for("create")
    assert read_artifact_mode(projet) == default_mode_for("create")


async def test_le_manifeste_ne_porte_aucune_clef_morte(tmp_path: Path) -> None:
    """`max_instances` was written at 2 for the coder and read nowhere — the
    backend has no `asyncio.gather`, the pipeline is strictly sequential.

    Same defect ticket-091 cleaned up on `auto_merge_on_approve`: a setting
    you read and believe.
    """
    projet = await _cree(tmp_path)
    data = json.loads((projet / "agents.json").read_text(encoding="utf-8"))

    for agent in data["agents"]:
        assert "max_instances" not in agent
