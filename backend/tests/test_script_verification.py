"""Le script que `test_command` lance se refuse en écriture — ticket-490."""
import json
from pathlib import Path

import pytest

from tessera.services.providers.chemins_proteges import PROTECTION_REFUS
from tessera.services.providers.perimetre import hook_refus_hors_perimetre
from tessera.services.providers.script_verification import script_de_verification

_VERIFIER = "uv run python ../scripts/verifier.py"


def _depot(tmp_path: Path, test_command: str | None, test_cwd: str = "../../backend") -> Path:
    """A repo shaped like ide-core: the project sits under projects/, code above it."""
    depot = tmp_path / "depot"
    projet = depot / "projects" / "ide-core"
    projet.mkdir(parents=True)
    (depot / "backend").mkdir()
    (depot / "scripts").mkdir()
    (depot / "scripts" / "verifier.py").write_text("print('ok')\n", encoding="utf-8")
    pipeline: dict[str, str] = {"test_cwd": test_cwd}
    if test_command is not None:
        pipeline["test_command"] = test_command
    (projet / "agents.json").write_text(
        json.dumps({"git_root": "ancestor", "pipeline": pipeline}), encoding="utf-8"
    )
    return depot


async def _ecrire(depot: Path, relatif: str, outil: str = "Write") -> dict[str, object]:
    projet = depot / "projects" / "ide-core"
    hook = hook_refus_hors_perimetre(projet, racine=depot.resolve())
    sortie = await hook(
        {"tool_name": outil, "tool_input": {"file_path": str(depot / relatif)}},
        None,
        None,
    )
    return dict(sortie)


@pytest.mark.parametrize("outil", ["Write", "Edit"])
async def test_le_hook_refuse_le_script_de_test_command(tmp_path: Path, outil: str) -> None:
    depot = _depot(tmp_path, _VERIFIER)

    sortie = await _ecrire(depot, "scripts/verifier.py", outil)

    decision = sortie["hookSpecificOutput"]
    assert isinstance(decision, dict)
    assert decision["permissionDecision"] == "deny"
    raison = decision["permissionDecisionReason"]
    assert raison.startswith(PROTECTION_REFUS[:20])
    assert "verifier.py" in raison and "test_command" in raison


async def test_le_hook_refuse_aussi_un_chemin_qui_remonte(tmp_path: Path) -> None:
    depot = _depot(tmp_path, _VERIFIER)

    sortie = await _ecrire(depot, "backend/../scripts/verifier.py")

    assert sortie["hookSpecificOutput"]["permissionDecision"] == "deny"  # type: ignore[index]


async def test_les_autres_fichiers_du_depot_restent_ecrivables(tmp_path: Path) -> None:
    depot = _depot(tmp_path, _VERIFIER)

    assert await _ecrire(depot, "backend/app.py") == {}


@pytest.mark.parametrize("commande", ["npm test", "uv run pytest", None])
async def test_sans_fichier_designe_rien_de_plus_nest_refuse(
    tmp_path: Path, commande: str | None
) -> None:
    depot = _depot(tmp_path, commande)

    assert script_de_verification(depot / "projects" / "ide-core") is None
    assert await _ecrire(depot, "scripts/verifier.py") == {}


def test_le_script_se_resout_depuis_test_cwd(tmp_path: Path) -> None:
    depot = _depot(tmp_path, _VERIFIER)

    script = script_de_verification(depot / "projects" / "ide-core")

    assert script == (depot / "scripts" / "verifier.py").resolve()


def test_un_script_qui_nexiste_pas_nest_pas_protege(tmp_path: Path) -> None:
    depot = _depot(tmp_path, "uv run python ../scripts/absent.py")

    assert script_de_verification(depot / "projects" / "ide-core") is None


def test_un_agents_json_illisible_ne_protege_rien(tmp_path: Path) -> None:
    depot = _depot(tmp_path, _VERIFIER)
    (depot / "projects" / "ide-core" / "agents.json").write_text("{", encoding="utf-8")

    assert script_de_verification(depot / "projects" / "ide-core") is None
