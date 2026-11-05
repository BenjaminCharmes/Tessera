"""Tests for scripts/deplacer_domaine.py (ticket-827).

Every test builds a temporary repository: a table `scripts/domaines_services.py`,
flat modules under `backend/src/tessera/services/`, and the files that refer to
them. Module names are made up, so the script never meets them in the real tree.
"""

import sys
from pathlib import Path

import pytest

_SCRIPTS = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

from deplacer_domaine import lire_table, main  # noqa: E402
from deplacer_domaine_texte import references_mortes, reecrire  # noqa: E402

_ORDRE = ("bas", "git_workspace", "sup")
_TABLE = {"alpha": "sup", "beta": "sup", "gamma": "bas", "alpha_suite": "bas"}
_SERVICES = "backend/src/tessera/services"


def _ecrire(racine: Path, chemin: str, texte: str = "") -> Path:
    cible = racine / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text(texte, encoding="utf-8")
    return cible


def _arbre(racine: Path, table: dict[str, str] = _TABLE) -> Path:
    lignes = "".join(f'    "{nom}": "{dom}",\n' for nom, dom in table.items())
    _ecrire(
        racine,
        "scripts/domaines_services.py",
        f'"""Table."""\n\nORDRE: tuple[str, ...] = {_ORDRE!r}\n\n'
        f"A_DEPLACER: dict[str, str] = {{\n    # domaines\n{lignes}}}\n",
    )
    _ecrire(racine, f"{_SERVICES}/__init__.py")
    for nom in table:
        _ecrire(racine, f"{_SERVICES}/{nom}.py", f'"""Module {nom}."""\n')
    return racine


def _lire(racine: Path, chemin: str) -> str:
    return (racine / chemin).read_text(encoding="utf-8")


def _deplacer(racine: Path, domaine: str = "sup", *options: str) -> int:
    return main([domaine, "--racine", str(racine), *options])


def test_module_is_moved_and_removed_from_the_table(tmp_path: Path) -> None:
    _arbre(tmp_path)
    assert _deplacer(tmp_path) == 0
    services = tmp_path / _SERVICES
    assert (services / "sup" / "alpha.py").read_text(encoding="utf-8") == '"""Module alpha."""\n'
    assert (services / "sup" / "beta.py").exists()
    assert not (services / "alpha.py").exists()
    assert (services / "sup" / "__init__.py").read_text(encoding="utf-8") == ""
    assert (services / "gamma.py").exists()
    ordre, table = lire_table(tmp_path)
    assert ordre == _ORDRE
    assert table == {"gamma": "bas", "alpha_suite": "bas"}


def test_dotted_import_is_rewritten(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "backend/tests/test_x.py",
            "from tessera.services.alpha import f\nimport tessera.services.beta as b\n"
            "from tessera.services.gamma import g\n")
    assert _deplacer(tmp_path) == 0
    assert _lire(tmp_path, "backend/tests/test_x.py") == (
        "from tessera.services.sup.alpha import f\nimport tessera.services.sup.beta as b\n"
        "from tessera.services.gamma import g\n"
    )


def test_from_package_import_is_split_by_target_domain(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, f"{_SERVICES}/gamma.py",
            "def f() -> None:\n    from tessera.services import alpha, gamma, beta\n")
    assert _deplacer(tmp_path) == 0
    assert _lire(tmp_path, f"{_SERVICES}/gamma.py") == (
        "def f() -> None:\n"
        "    from tessera.services import gamma\n"
        "    from tessera.services.sup import alpha, beta\n"
    )


def test_parenthesised_multiline_import_is_rewritten(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "scripts/outil.py",
            "from tessera.services import (  # noqa: E402\n    alpha,\n    gamma,\n)\nx = 1\n")
    assert _deplacer(tmp_path) == 0
    assert _lire(tmp_path, "scripts/outil.py") == (
        "from tessera.services import gamma  # noqa: E402\n"
        "from tessera.services.sup import alpha  # noqa: E402\n"
        "x = 1\n"
    )


def test_alias_is_kept(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "backend/src/tessera/routers/r.py",
            "from tessera.services import alpha as a, beta\n")
    assert _deplacer(tmp_path) == 0
    assert _lire(tmp_path, "backend/src/tessera/routers/r.py") == (
        "from tessera.services.sup import alpha as a, beta\n"
    )


def test_string_literal_in_a_patch_is_rewritten(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "backend/tests/test_p.py",
            'monkeypatch.setattr("tessera.services.alpha.f", g)\n'
            "patch('tessera.services.beta')\n"
            'importlib.import_module("tessera.services.alpha")\n')
    assert _deplacer(tmp_path) == 0
    assert _lire(tmp_path, "backend/tests/test_p.py") == (
        'monkeypatch.setattr("tessera.services.sup.alpha.f", g)\n'
        "patch('tessera.services.sup.beta')\n"
        'importlib.import_module("tessera.services.sup.alpha")\n'
    )


def test_python_dash_m_in_a_makefile_is_rewritten(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "Makefile", 'cible:\n\tuv run python -m tessera.services.alpha "$(P)"\n')
    _ecrire(tmp_path, "scripts/t.ps1", "& uv run python -m tessera.services.alpha $P\n")
    assert _deplacer(tmp_path) == 0
    assert _lire(tmp_path, "Makefile") == (
        'cible:\n\tuv run python -m tessera.services.sup.alpha "$(P)"\n'
    )
    assert _lire(tmp_path, "scripts/t.ps1") == "& uv run python -m tessera.services.sup.alpha $P\n"


def test_longer_module_name_is_not_touched(tmp_path: Path) -> None:
    _arbre(tmp_path)
    texte = (
        "from tessera.services.alpha_suite import f\n"
        'patch("tessera.services.alpha_suite.f")\n'
        'LIMITES = {"services/alpha_suite.py": 400}\n'
    )
    _ecrire(tmp_path, "backend/tests/test_l.py", texte)
    assert _deplacer(tmp_path) == 0
    assert _lire(tmp_path, "backend/tests/test_l.py") == texte


def test_file_paths_are_rewritten(tmp_path: Path) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "backend/tests/test_f.py",
            'LIMITES = {"services/alpha.py": 400}\n'
            'CHEMIN = src / "services" / "beta.py"\n')
    assert _deplacer(tmp_path) == 0
    assert _lire(tmp_path, "backend/tests/test_f.py") == (
        'LIMITES = {"services/sup/alpha.py": 400}\n'
        'CHEMIN = src / "services" / "sup" / "beta.py"\n'
    )


def test_domain_named_like_one_of_its_modules(tmp_path: Path) -> None:
    _arbre(tmp_path, {"sup": "sup", "sup_x": "sup", "gamma": "bas"})
    _ecrire(tmp_path, "backend/tests/test_d.py",
            "from tessera.services.sup import f\n"
            "from tessera.services import sup, sup_x\n"
            'patch("tessera.services.sup.sup_x")\n')
    assert _deplacer(tmp_path) == 0
    assert (tmp_path / _SERVICES / "sup" / "sup.py").exists()
    assert _lire(tmp_path, "backend/tests/test_d.py") == (
        "from tessera.services.sup.sup import f\n"
        "from tessera.services.sup import sup, sup_x\n"
        'patch("tessera.services.sup.sup.sup_x")\n'
    )


def test_file_based_path_in_a_moved_module_is_reported(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, f"{_SERVICES}/alpha.py", "RACINE = Path(__file__).resolve().parents[4]\n")
    _ecrire(tmp_path, "backend/tests/test_s.py", 'source = (_SERVICES / "beta.py").read_text()\n')
    _ecrire(tmp_path, "docs/archi.md", "Voir `tessera.services.alpha`.\n")
    assert _deplacer(tmp_path) == 0
    sortie = capsys.readouterr().out
    assert "services/sup/alpha.py:1" in sortie and "parents[4]" in sortie
    assert "backend/tests/test_s.py:1" in sortie and '"beta.py"' in sortie
    assert "docs/archi.md:1" in sortie
    assert _lire(tmp_path, "docs/archi.md") == "Voir `tessera.services.alpha`.\n"


def test_dry_run_changes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _arbre(tmp_path)
    _ecrire(tmp_path, "backend/tests/test_x.py", "from tessera.services.alpha import f\n")
    avant = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert _deplacer(tmp_path, "sup", "--dry-run") == 0
    apres = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert apres == avant
    sortie = capsys.readouterr().out
    assert f"{_SERVICES}/alpha.py -> {_SERVICES}/sup/alpha.py" in sortie
    assert "backend/tests/test_x.py:1" in sortie
    assert "from tessera.services.sup.alpha import f" in sortie


def test_unknown_domain_fails(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _arbre(tmp_path)
    assert _deplacer(tmp_path, "inconnu") == 2
    assert "inconnu" in capsys.readouterr().err
    # Un domaine connu sans module à plat sort aussi en erreur.
    assert _deplacer(tmp_path, "git_workspace") == 2
    assert (tmp_path / _SERVICES / "alpha.py").exists()


def test_existing_package_keeps_its_init(tmp_path: Path) -> None:
    _arbre(tmp_path, {"delta": "git_workspace", "gamma": "bas"})
    init = _ecrire(tmp_path, f"{_SERVICES}/git_workspace/__init__.py", "from .socle import x\n")
    assert _deplacer(tmp_path, "git_workspace") == 0
    assert init.read_text(encoding="utf-8") == "from .socle import x\n"
    assert (tmp_path / _SERVICES / "git_workspace" / "delta.py").exists()


def test_old_paths_left_behind_are_detected() -> None:
    deplaces = {"alpha": "sup"}
    modules = {"sup": {"alpha"}}
    assert references_mortes("from tessera.services.sup.alpha import f\n", deplaces, modules) == []
    assert references_mortes('patch("tessera.services.alpha.f")\n', deplaces, modules) == [
        "1: tessera.services.alpha"
    ]
    assert references_mortes("from tessera.services import alpha\n", deplaces, modules) == [
        "1: from tessera.services import alpha"
    ]
    assert references_mortes('"services/alpha.py"\n', deplaces, modules) == ["1: services/alpha.py"]


def test_rewrite_is_a_single_pass() -> None:
    deplaces = {"sup": "sup", "alpha": "sup"}
    texte = "import tessera.services.sup\nfrom tessera.services import alpha\n"
    attendu = "import tessera.services.sup.sup\nfrom tessera.services.sup import alpha\n"
    assert reecrire(texte, deplaces, python=True) == attendu
