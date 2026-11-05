"""Verification script: runs backend and frontend checks in parallel chains.

Three chains run side by side — pytest, typing (mypy → mypy-linux) and
frontend (tsc → eslint → vitest) — each stopping at its first failure. Outputs
are captured and printed together once every chain finishes — never
interleaved.

Only the chains the change touches run: a diff limited to `frontend/` skips
pytest and mypy, one limited to `backend/` skips the frontend chain, and a diff
that touches neither runs nothing. GitHub CI runs everything before any merge.
When the diff cannot be read, every chain runs.

`--impact <ref>` limits pytest to the test files the change since `<ref>` can
affect, working tree included; `--impact base` uses the ticket's own diff. The
tester runs with `--impact base`, and the retest after a rebase adds its own
`--impact <sha>`, the last one winning (ticket-793). The last line gives the
duration of every step that ran.

Run from backend/ with: uv run python ../scripts/verifier.py

Never calls a console-script launcher (`pytest.exe`, `mypy.exe`): Windows
application control refuses them (os error 4551). Python tools run as
`<interpreter> -m <tool>`, with the interpreter that runs this script.
"""
from __future__ import annotations

import importlib.util
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

# `python` seul désigne, sous Windows, l'interpréteur du système et non celui
# du `.venv` : pytest et mypy n'y sont pas. `npx` est un `.cmd`, qu'un
# `subprocess` sans shell ne trouve pas sous son nom court.
_PYTHON = sys.executable
_NPX = "npx.cmd" if os.name == "nt" else "npx"

# 1 973 tests en série prenaient douze minutes, et la suite complète
# dépassait les 900 s du testeur à elle seule (ticket-357). Huit processus la
# ramènent à deux minutes et demie sans saturer une machine qui fait tourner
# d'autres files. Le 04/11/2026, avec 4 824 tests et deux files en parallèle,
# la suite en prenait de nouveau quatorze et demie (ticket-793).
_PYTEST_WORKERS = "8"

# Ligne max renvoyée au codeur pour ne pas inonder sa fenêtre.
_MAX_LINES = 120


@dataclass
class Step:
    name: str
    cmd: list[str]
    cwd: Path


def pytest_command() -> list[str]:
    """Return the pytest command, spread over several workers when xdist is installed."""
    cmd = [_PYTHON, "-m", "pytest", "-q", "-x", "-m", "not integration"]
    # Sans xdist (environnement synchronisé sans l'extra `dev`), la suite
    # tourne en série plutôt que d'échouer sur une option inconnue.
    if importlib.util.find_spec("xdist") is not None:
        cmd += ["-n", _PYTEST_WORKERS]
    return cmd


BACKEND_STEPS: list[Step] = [
    Step(
        name="pytest",
        cmd=pytest_command(),
        cwd=BACKEND_DIR,
    ),
]

# Une chaîne à part, à côté de pytest plutôt qu'après lui. Chaque plateforme a
# son propre cache : partagé, chaque passage invalidait celui de l'autre (39 s
# à froid, 12 s à chaud pour win32 seul ; 46 s puis 47 s en alternant).
TYPE_STEPS: list[Step] = [
    Step(
        name="mypy",
        cmd=[_PYTHON, "-m", "mypy", "--cache-dir", ".mypy_cache/native", "src/"],
        cwd=BACKEND_DIR,
    ),
    # La CI tourne sous Linux : un attribut propre à Windows (`stat.FILE_ATTRIBUTE_…`,
    # `os.killpg` dans l'autre sens) passe le mypy local et casse la CI, après la revue.
    Step(
        name="mypy-linux",
        cmd=[
            _PYTHON, "-m", "mypy", "--platform", "linux",
            "--cache-dir", ".mypy_cache/linux", "src/",
        ],
        cwd=BACKEND_DIR,
    ),
]

FRONTEND_STEPS: list[Step] = [
    Step(
        name="tsc",
        cmd=[_NPX, "tsc", "-b"],
        cwd=FRONTEND_DIR,
    ),
    Step(
        name="eslint",
        cmd=[_NPX, "eslint", "."],
        cwd=FRONTEND_DIR,
    ),
    Step(
        name="vitest",
        cmd=[_NPX, "vitest", "run"],
        cwd=FRONTEND_DIR,
    ),
]

# Kept for backward compatibility and for tools that iterate all steps.
# Un diff qui ne touche que des consignes (ADR, contraintes, CLAUDE.md, prompts,
# skills) ne lançait aucun test : l'ADR-069 du ticket-674 a dépassé son budget sans
# qu'aucun testeur ne le voie (ticket-734). Dix secondes suffisent à le dire.
CONSIGNES_STEPS: list[Step] = [
    Step(
        name="consignes",
        cmd=[_PYTHON, "-m", "pytest", "-q", "-p", "no:cacheprovider", "tests/test_consignes_coherentes.py"],
        cwd=BACKEND_DIR,
    ),
]

STEPS: list[Step] = BACKEND_STEPS + TYPE_STEPS + FRONTEND_STEPS


def _extract_errors(output: str) -> str:
    """Return the most relevant lines, capped to avoid flooding the codeur."""
    lines = output.splitlines()
    if len(lines) <= _MAX_LINES:
        return output
    # La fin porte le résumé et le test en échec : c'est elle qu'on garde.
    omitted = len(lines) - _MAX_LINES
    return "\n".join([f"… ({omitted} ligne(s) omise(s))", *lines[-_MAX_LINES:]])


@dataclass
class _StepFailure:
    step_name: str
    returncode: int
    excerpt: str


def _run_chain(steps: list[Step], durees: dict[str, float] | None = None) -> list[_StepFailure]:
    """Run steps sequentially; stop at first failure and return it.

    Returns a list with at most one entry: the failing step, with its
    return code and extracted output. Returns an empty list when all pass.
    Each step's duration in seconds is recorded in `durees` when given.
    """
    for step in steps:
        debut = time.monotonic()
        result = subprocess.run(
            step.cmd,
            cwd=step.cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if durees is not None:
            durees[step.name] = time.monotonic() - debut
        if result.returncode != 0:
            combined = result.stdout + result.stderr
            return [_StepFailure(step.name, result.returncode, _extract_errors(combined))]
    return []


def run_parallel(
    backend_steps: list[Step],
    frontend_steps: list[Step],
    type_steps: list[Step] | None = None,
) -> int:
    """Run the chains concurrently; return non-zero if any fails.

    Each chain is sequential and stops at its first failure. Outputs are
    captured independently — never interleaved. The report (backend, then
    typing, then frontend) is printed to stderr once every chain finishes.
    """
    chains = [backend_steps, type_steps or [], frontend_steps]
    durees: dict[str, float] = {}
    with ThreadPoolExecutor(max_workers=len(chains)) as executor:
        futures = [executor.submit(_run_chain, steps, durees) for steps in chains]
        results = [future.result() for future in futures]

    all_failures = [failure for result in results for failure in result]
    for failure in all_failures:
        print(f"{failure.step_name} :\n{failure.excerpt}", file=sys.stderr)
    if durees:
        print(ligne_des_durees(durees), file=sys.stderr)

    return all_failures[0].returncode if all_failures else 0


def ligne_des_durees(durees: dict[str, float]) -> str:
    """One line with the duration of every step that ran, in run order of the chains."""
    # On ne savait pas laquelle des étapes coûtait : le retest après rebase
    # prenait 12 à 17 minutes sans dire pourquoi (ticket-793).
    return "durées : " + ", ".join(f"{nom} {secondes:.0f} s" for nom, secondes in durees.items())


def run_steps(steps: list[Step]) -> int:
    """Run all steps in order; stop and report the first failure.

    Returns the exit code of the first failing step, or 0 if all pass.
    Kept for backward compatibility with tests and tooling that calls it directly.
    """
    for step in steps:
        result = subprocess.run(
            step.cmd,
            cwd=step.cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            combined = result.stdout + result.stderr
            print(f"{step.name} :\n{_extract_errors(combined)}", file=sys.stderr)
            return result.returncode
    return 0


# Les branches de base essayées, dans l'ordre, pour trouver le point de départ
# du ticket. Aucune trouvée : on teste tout.
_BASES = ("origin/develop", "origin/main")


def _git(*args: str) -> str | None:
    """Run a read-only git command from the repository root; None when it fails."""
    try:
        result = subprocess.run(
            ["git", *args], cwd=REPO_ROOT, capture_output=True, text=True,
            encoding="utf-8", errors="replace",
        )
    except OSError:
        return None
    return result.stdout if result.returncode == 0 else None


def changed_paths() -> list[str] | None:
    """Paths the ticket changes since its base, working tree included; None when unknown."""
    for base in _BASES:
        depart = _git("merge-base", "HEAD", base)
        if depart is None:
            continue
        modifies = _git("diff", "--name-only", depart.strip())
        nouveaux = _git("ls-files", "--others", "--exclude-standard")
        if modifies is None or nouveaux is None:
            return None
        return [p for p in (modifies + nouveaux).splitlines() if p.strip()]
    return None


def chains_for(paths: list[str] | None) -> tuple[bool, bool]:
    """Whether the backend chains and the frontend chain must run for these paths.

    Unknown paths run everything. ``scripts/`` counts as backend: the test
    command itself lives there.
    """
    if paths is None:
        return True, True
    backend = any(p.startswith(("backend/", "scripts/")) for p in paths)
    frontend = any(p.startswith("frontend/") for p in paths)
    return backend, frontend


_CONSIGNES = ("projects/ide-core/memory/", "agents/prompts/", ".claude/skills/")


def consignes_touchees(paths: list[str]) -> bool:
    """Whether the diff touches an instruction file that the consistency tests check."""
    return any(p.startswith(_CONSIGNES) or p.endswith("CLAUDE.md") for p in paths)


_SOURCES = "backend/src/"
_TESTS = "backend/tests/"

#: Tests qui jugent tout le dépôt : toujours lancés en mode impact (ticket-793).
TESTS_GLOBAUX = (
    "tests/test_longueur_des_fichiers.py",
    "tests/test_consignes_coherentes.py",
    "tests/test_contrat_des_routes.py",
    "tests/test_openapi_export.py",
)


def _module_de(chemin: str) -> str:
    """`backend/src/tessera/a/b.py` → `tessera.a.b` ; un `__init__.py` donne son paquet."""
    module = chemin[len(_SOURCES):-len(".py")].replace("/", ".")
    return module.removesuffix(".__init__")


def _importe(texte: str, module: str) -> bool:
    """Whether `texte` imports `module`, as `tessera.a.b` or as `from tessera.a import b`."""
    if module in texte:
        return True
    parent, _, nom = module.rpartition(".")
    if not parent:
        return False
    return re.search(rf"from {re.escape(parent)} import [^\n]*\b{re.escape(nom)}\b", texte) is not None


def fichiers_de_test_impactes(chemins: list[str], racine: Path = REPO_ROOT) -> list[str] | None:
    """Backend test files a change to `chemins` can affect, relative to `backend/`.

    None means « toute la suite » : un fichier de configuration, un utilitaire de
    test ou `scripts/` peuvent toucher n'importe quel test. Un module modifié
    entraîne les tests qui l'importent, et ceux qui importent un module qui
    l'importe (un niveau). La CI rejoue de toute façon la suite complète.
    """
    selection: set[str] = set()
    modules: set[str] = set()
    for chemin in chemins:
        if chemin.startswith("scripts/"):
            return None
        if not chemin.startswith("backend/"):
            continue
        nom = chemin.rsplit("/", 1)[-1]
        if chemin.startswith(_TESTS) and nom.startswith("test_") and nom.endswith(".py"):
            if (racine / chemin).exists():
                selection.add(chemin[len("backend/"):])
        elif chemin.startswith(_SOURCES) and chemin.endswith(".py"):
            modules.add(_module_de(chemin))
        else:
            return None
    if modules:
        modifies = frozenset(modules)
        for source in (racine / _SOURCES).rglob("*.py"):
            texte = source.read_text(encoding="utf-8", errors="replace")
            if any(_importe(texte, m) for m in modifies):
                modules.add(_module_de(source.relative_to(racine).as_posix()))
        for test in (racine / _TESTS).rglob("test_*.py"):
            texte = test.read_text(encoding="utf-8", errors="replace")
            if any(_importe(texte, m) for m in modules):
                selection.add(test.relative_to(racine / "backend").as_posix())
    return sorted(selection)


def _option_impact(argv: list[str]) -> str | None:
    """The ref given with the last `--impact <ref>`, or None.

    La dernière l'emporte : le retest après rebase ajoute la sienne à la
    commande du testeur, qui peut déjà porter `--impact base`.
    """
    indices = [i for i, arg in enumerate(argv) if arg == "--impact" and i + 1 < len(argv)]
    return argv[indices[-1] + 1] if indices else None


def _chemins_depuis(ref: str, paths: list[str] | None) -> list[str] | None:
    """Paths changed since `ref`, working tree included; `base` reuses the ticket's own diff."""
    if ref == "base":
        # Le testeur juge l'arbre de travail du codeur, pas encore commité (ticket-793).
        return paths
    diff = _git("diff", "--name-only", ref)
    nouveaux = _git("ls-files", "--others", "--exclude-standard")
    if diff is None or nouveaux is None:
        return None
    return [p for p in (diff + nouveaux).splitlines() if p.strip()]


def _pytest_impacte(ref: str, paths: list[str] | None = None) -> list[Step] | None:
    """The pytest step limited to the tests the change since `ref` can affect; None for all."""
    chemins = _chemins_depuis(ref, paths)
    if chemins is None:
        return None
    fichiers = fichiers_de_test_impactes(chemins)
    if fichiers is None:
        return None
    # Les tests globaux lisent tout le dépôt sans importer le module touché :
    # le cliquet des longueurs a laissé passer le ticket-761 (CI rouge, PR #909).
    fichiers = sorted({*fichiers, *(t for t in TESTS_GLOBAUX if (BACKEND_DIR / t).exists())})
    if not fichiers:
        print(f"Aucun test backend concerné depuis {ref} : pytest sauté.", file=sys.stderr)
        return []
    return [Step(name="pytest", cmd=pytest_command() + fichiers, cwd=BACKEND_DIR)]


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    ref = _option_impact(sys.argv[1:] if argv is None else argv)
    paths = changed_paths()
    backend, frontend = chains_for(paths)
    if not (backend or frontend) and paths is not None and consignes_touchees(paths):
        return run_parallel(CONSIGNES_STEPS, [], [])
    if not (backend or frontend):
        print("Aucun fichier de backend/ ni de frontend/ modifié : rien à tester.", file=sys.stderr)
        return 0
    pytest_steps = BACKEND_STEPS
    if backend and ref is not None:
        # Le testeur et le retest après rebase ne relancent que ce que le
        # changement peut toucher ; la CI rejoue toute la suite (ticket-793).
        impacte = _pytest_impacte(ref, paths)
        pytest_steps = BACKEND_STEPS if impacte is None else impacte
    return run_parallel(
        pytest_steps if backend else [],
        FRONTEND_STEPS if frontend else [],
        TYPE_STEPS if backend else [],
    )


if __name__ == "__main__":
    sys.exit(main())
