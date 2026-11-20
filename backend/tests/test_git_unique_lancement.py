"""Every git the backend launches goes through `build_command` — ticket-941."""
import ast
from pathlib import Path

import pytest

from tessera.services.git_workspace.socle import GitCore
from tessera.services.noyau.git_commande import build_command

SOURCES = Path(__file__).resolve().parent.parent / "src" / "tessera"
POINT_UNIQUE = "services/noyau/git_commande.py"


_LANCEURS = {"create_subprocess_exec", "run", "Popen", "check_output", "check_call", "call"}


def _est_un_lancement(appel: ast.Call) -> bool:
    nom = appel.func.attr if isinstance(appel.func, ast.Attribute) else getattr(appel.func, "id", "")
    return nom in _LANCEURS


def _lancements_directs(fichier: Path) -> list[int]:
    """Lines where a list or call argument starts with the literal "git"."""
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    lignes: list[int] = []
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.List | ast.Tuple):
            elements = noeud.elts
        elif isinstance(noeud, ast.Call) and _est_un_lancement(noeud):
            elements = noeud.args
        else:
            continue
        if elements and isinstance(elements[0], ast.Constant) and elements[0].value == "git":
            lignes.append(noeud.lineno)
    return lignes


def test_no_direct_git_launch_outside_the_single_point() -> None:
    fautifs = [
        f"{f.relative_to(SOURCES).as_posix()}:{n}"
        for f in sorted(SOURCES.rglob("*.py"))
        if f.relative_to(SOURCES).as_posix() != POINT_UNIQUE
        for n in _lancements_directs(f)
    ]
    assert fautifs == []


def test_build_command_always_disables_fsmonitor() -> None:
    assert "core.fsmonitor=false" in build_command(("status",))
    assert "core.fsmonitor=false" in build_command(("commit", "-m", "x"))


async def test_git_core_run_builds_a_command_with_fsmonitor_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    vus: list[tuple[str, ...]] = []

    class _Proc:
        returncode = 0

        async def communicate(self) -> tuple[bytes, bytes]:
            return b"", b""

    async def faux(*cmd: str, **_: object) -> _Proc:
        vus.append(cmd)
        return _Proc()

    monkeypatch.setattr("asyncio.create_subprocess_exec", faux)
    await GitCore(tmp_path)._run("status")
    assert "core.fsmonitor=false" in vus[0]
