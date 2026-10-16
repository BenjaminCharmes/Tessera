"""Only the user's request reaches provisioning — ADR-053, ticket-471.

Checked on the imports themselves: a pipeline, chat or agent module that
imported ``tessera.services.provisioning`` could put a project online by itself.
"""
import ast
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1] / "src" / "tessera"
_CIBLE = "tessera.services.provisioning"

#: Les seuls modules hors du paquet qui ont le droit de l'importer.
_AUTORISES = {"routers/provisioning.py"}

#: Ce que la mise en ligne ne doit jamais atteindre, au-delà de la liste blanche.
_INTERDITS = (
    "services/orchestrator.py",
    "services/pipeline_*.py",
    "services/run_*.py",
    "services/chat*.py",
    "services/agent_*.py",
    "agents/*.py",
    "routers/orchestrator.py",
    "routers/chat.py",
    "routers/agents.py",
    "routers/agent_admin.py",
)


def _imports(fichier: Path) -> set[str]:
    """Return every module a file imports, ``from x import y`` as ``x.y`` too."""
    arbre = ast.parse(fichier.read_text(encoding="utf-8"))
    noms: set[str] = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            noms.update(alias.name for alias in noeud.names)
        elif isinstance(noeud, ast.ImportFrom) and noeud.module:
            noms.add(noeud.module)
            noms.update(f"{noeud.module}.{alias.name}" for alias in noeud.names)
    return noms


def _importe_provisioning(fichier: Path) -> bool:
    return any(n == _CIBLE or n.startswith(f"{_CIBLE}.") for n in _imports(fichier))


def _relatif(fichier: Path) -> str:
    return fichier.relative_to(_SRC).as_posix()


def test_pipeline_chat_and_agent_modules_do_not_import_provisioning() -> None:
    fichiers = sorted({f for motif in _INTERDITS for f in _SRC.glob(motif)})

    assert fichiers, "the patterns must match the modules they guard"
    fautifs = [_relatif(f) for f in fichiers if _importe_provisioning(f)]
    assert fautifs == []


def test_only_the_provisioning_router_imports_the_package_from_outside() -> None:
    importeurs = {
        _relatif(f)
        for f in _SRC.rglob("*.py")
        if not _relatif(f).startswith("services/provisioning/") and _importe_provisioning(f)
    }

    assert importeurs == _AUTORISES


def test_the_detector_sees_an_import_in_either_form(tmp_path: Path) -> None:
    direct = tmp_path / "a.py"
    direct.write_text("import tessera.services.provisioning.plan\n", encoding="utf-8")
    depuis = tmp_path / "b.py"
    depuis.write_text("from tessera.services import provisioning\n", encoding="utf-8")
    sans = tmp_path / "c.py"
    sans.write_text("from tessera.services import run_lock\n", encoding="utf-8")

    assert _importe_provisioning(direct)
    assert _importe_provisioning(depuis)
    assert not _importe_provisioning(sans)
