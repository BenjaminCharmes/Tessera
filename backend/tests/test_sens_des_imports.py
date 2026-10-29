"""Ratchet on import direction: routers -> services -> models, never backwards."""

import ast
from pathlib import Path

SOURCES = Path(__file__).resolve().parent.parent / "src" / "tessera"

# Couches interdites à importer, par couche : models ne remonte ni vers services
# ni vers routers, services ne remonte pas vers routers.
INTERDITS: dict[str, frozenset[str]] = {
    "models": frozenset({"services", "routers"}),
    "services": frozenset({"routers"}),
}

# Écarts présents à l'ouverture du ticket-670, au format
# "chemin relatif à src/tessera -> couche importée". Il n'y en avait aucun.
# Le cliquet ne remonte pas : un écart corrigé se retire d'ici, jamais l'inverse.
ECARTS_CONNUS: frozenset[str] = frozenset()


def _paquet_du_module(chemin: Path, racine: Path) -> list[str]:
    """Return the package parts of a module, relative to racine."""
    return list(chemin.relative_to(racine).parts[:-1])


def _cibles_import_from(noeud: ast.ImportFrom, paquet: list[str]) -> list[list[str]]:
    """Return the dotted targets (without the leading 'tessera') of a from-import."""
    if noeud.level:
        base = paquet[: max(len(paquet) - (noeud.level - 1), 0)]
    else:
        base = []
    module = noeud.module.split(".") if noeud.module else []
    if not noeud.level:
        if not module or module[0] != "tessera":
            return []
        module = module[1:]
    cible = base + module
    if cible:
        return [cible]
    return [[alias.name] for alias in noeud.names]


def _couches_importees(arbre: ast.AST, paquet: list[str]) -> set[str]:
    """Return the top-level tessera packages a module imports from."""
    couches: set[str] = set()
    for noeud in ast.walk(arbre):
        if isinstance(noeud, ast.Import):
            for alias in noeud.names:
                parties = alias.name.split(".")
                if parties[0] == "tessera" and len(parties) > 1:
                    couches.add(parties[1])
        elif isinstance(noeud, ast.ImportFrom):
            couches.update(c[0] for c in _cibles_import_from(noeud, paquet) if c)
    return couches


def mesurer(racine: Path) -> set[str]:
    """List every backwards import under racine as 'path -> layer'."""
    ecarts: set[str] = set()
    for fichier in sorted(racine.rglob("*.py")):
        if "__pycache__" in fichier.parts:
            continue
        relatif = fichier.relative_to(racine)
        interdites = INTERDITS.get(relatif.parts[0]) if len(relatif.parts) > 1 else None
        if interdites is None:
            continue
        arbre = ast.parse(fichier.read_text(encoding="utf-8"))
        paquet = _paquet_du_module(fichier, racine)
        for couche in _couches_importees(arbre, paquet) & interdites:
            ecarts.add(f"{relatif.as_posix()} -> {couche}")
    return ecarts


def controler(racine: Path, connus: frozenset[str]) -> list[str]:
    """Compare the measured gaps with the listed ones, both ways."""
    mesures = mesurer(racine)
    messages = [
        f"{e} : import à contresens des couches (routers > services > models)."
        for e in sorted(mesures - connus)
    ]
    messages += [
        f"{e} : écart corrigé mais toujours listé. Retire l'entrée de ECARTS_CONNUS."
        for e in sorted(connus - mesures)
    ]
    return messages


def _ecrire(racine: Path, chemin: str, source: str) -> None:
    cible = racine / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(source, encoding="utf-8")


def test_backend_imports_follow_their_layers() -> None:
    assert controler(SOURCES, ECARTS_CONNUS) == []


def test_models_importing_services_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "models/a.py", "from tessera.services.x import y\n")
    messages = controler(tmp_path, frozenset())
    assert len(messages) == 1
    assert "models/a.py -> services" in messages[0]


def test_models_importing_routers_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "models/a.py", "import tessera.routers.x\n")
    assert mesurer(tmp_path) == {"models/a.py -> routers"}


def test_services_importing_routers_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/a.py", "from tessera.routers import chat\n")
    assert mesurer(tmp_path) == {"services/a.py -> routers"}


def test_relative_imports_are_resolved(tmp_path: Path) -> None:
    _ecrire(tmp_path, "models/a.py", "from ..services import x\n")
    _ecrire(tmp_path, "services/sub/b.py", "from ...routers import x\n")
    _ecrire(tmp_path, "services/sub/c.py", "from . import x\n")
    assert mesurer(tmp_path) == {"models/a.py -> services", "services/sub/b.py -> routers"}


def test_from_tessera_import_layer_is_seen(tmp_path: Path) -> None:
    _ecrire(tmp_path, "models/a.py", "from tessera import services\n")
    assert mesurer(tmp_path) == {"models/a.py -> services"}


def test_lazy_import_inside_function_is_seen(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/a.py", "def f() -> None:\n    from tessera.routers import x\n")
    assert mesurer(tmp_path) == {"services/a.py -> routers"}


def test_allowed_directions_pass(tmp_path: Path) -> None:
    _ecrire(tmp_path, "routers/a.py", "from tessera.services import s\nfrom tessera.models import m\n")
    _ecrire(tmp_path, "services/b.py", "from tessera.models import m\nimport json\n")
    _ecrire(tmp_path, "models/c.py", "from tessera.utils import u\nfrom .d import e\n")
    assert controler(tmp_path, frozenset()) == []


def test_listed_gap_passes_while_it_exists(tmp_path: Path) -> None:
    _ecrire(tmp_path, "models/a.py", "from tessera.services import s\n")
    assert controler(tmp_path, frozenset({"models/a.py -> services"})) == []


def test_listed_gap_already_fixed_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "models/a.py", "x = 1\n")
    messages = controler(tmp_path, frozenset({"models/a.py -> services"}))
    assert len(messages) == 1
    assert "models/a.py -> services" in messages[0]
    assert "Retire l'entrée de ECARTS_CONNUS" in messages[0]


def test_pycache_is_ignored(tmp_path: Path) -> None:
    _ecrire(tmp_path, "models/__pycache__/a.py", "from tessera.services import s\n")
    assert mesurer(tmp_path) == set()
