"""Ratchet on backend file length: no file grows, no new file exceeds the cap."""

from pathlib import Path

PLAFOND_GENERAL = 300

# Fichiers qui dépassaient déjà le plafond général à l'ouverture du ticket-544 :
# chemin relatif à src/tessera -> taille maximale. Le cliquet ne remonte pas :
# un découpage baisse l'entrée (ou la retire sous 300 lignes), jamais l'inverse.
PLAFONDS: dict[str, int] = {
    "routers/chat.py": 378,
    "routers/orchestrator.py": 1115,
    "routers/projects.py": 826,
    "routers/tickets.py": 563,
    "services/agent_runner.py": 304,
    "services/ci_watcher.py": 607,
    "services/database.py": 772,
    # 714 : le ticket-542, mergé dans la même file avant ce cliquet, y a ajouté une ligne.
    "services/documentation.py": 714,
    "services/github_service.py": 592,
    "services/github_workflow.py": 520,
    "services/livraison.py": 626,
    "services/orchestrator.py": 1341,
    "services/pipeline_outcomes.py": 490,
    "services/pipeline_stages.py": 842,
    "services/process_registry.py": 409,
    "services/project_loader.py": 648,
    "services/providers/agent_sdk.py": 505,
    "services/reprise_orphelin.py": 384,
    "services/run_executor.py": 414,
    "services/test_runner.py": 631,
    "services/ticket_service.py": 483,
}

SOURCES = Path(__file__).resolve().parent.parent / "src" / "tessera"


def _taille(fichier: Path) -> int:
    return len(fichier.read_text(encoding="utf-8").splitlines())


def _fichiers(racine: Path) -> dict[str, int]:
    """Map each Python file under racine (relative POSIX path) to its line count."""
    return {
        p.relative_to(racine).as_posix(): _taille(p)
        for p in sorted(racine.rglob("*.py"))
        if "__pycache__" not in p.parts
    }


def _verifier_fichier(chemin: str, taille: int, plafonds: dict[str, int]) -> str | None:
    """Return the failure message for one file, or None when it complies."""
    plafond = plafonds.get(chemin, PLAFOND_GENERAL)
    if taille > plafond:
        return (
            f"{chemin} : {taille} lignes, plafond {plafond}. "
            "Découpe le fichier plutôt que de relever le plafond."
        )
    if chemin in plafonds and taille < plafond:
        cible = (
            f"baisse le plafond à {taille}"
            if taille > PLAFOND_GENERAL
            else "retire l'entrée de PLAFONDS"
        )
        return (
            f"{chemin} : {taille} lignes, plafond {plafond}. "
            f"Le fichier a rétréci, {cible} pour que le cliquet se resserre."
        )
    return None


def controler(racine: Path, plafonds: dict[str, int]) -> list[str]:
    """Check every Python file under racine against its ceiling."""
    tailles = _fichiers(racine)
    messages = [
        m
        for chemin, taille in tailles.items()
        if (m := _verifier_fichier(chemin, taille, plafonds)) is not None
    ]
    for chemin, plafond in plafonds.items():
        if chemin not in tailles:
            messages.append(
                f"{chemin} : fichier absent, plafond {plafond}. "
                "Retire l'entrée de PLAFONDS."
            )
    return messages


def _ecrire(racine: Path, chemin: str, lignes: int) -> None:
    cible = racine / chemin
    cible.parent.mkdir(parents=True, exist_ok=True)
    cible.write_text("x = 1\n" * lignes, encoding="utf-8")


def test_backend_files_respect_their_ceilings() -> None:
    assert controler(SOURCES, PLAFONDS) == []


def test_general_ceiling_is_300_lines() -> None:
    assert PLAFOND_GENERAL == 300


def test_table_lists_only_files_above_general_ceiling() -> None:
    assert all(plafond > PLAFOND_GENERAL for plafond in PLAFONDS.values())


def test_file_outside_table_at_300_lines_passes(tmp_path: Path) -> None:
    _ecrire(tmp_path, "a.py", 300)
    assert controler(tmp_path, {}) == []


def test_file_outside_table_at_301_lines_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "pkg/a.py", 301)
    messages = controler(tmp_path, {})
    assert len(messages) == 1
    assert "pkg/a.py" in messages[0]
    assert "301" in messages[0]
    assert "plafond 300" in messages[0]
    assert "Découpe le fichier plutôt que de relever le plafond" in messages[0]


def test_listed_file_above_its_ceiling_fails(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/gros.py", 401)
    messages = controler(tmp_path, {"services/gros.py": 400})
    assert len(messages) == 1
    assert "services/gros.py" in messages[0]
    assert "401" in messages[0]
    assert "plafond 400" in messages[0]
    assert "plutôt que de relever le plafond" in messages[0]


def test_listed_file_at_its_ceiling_passes(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/gros.py", 400)
    assert controler(tmp_path, {"services/gros.py": 400}) == []


def test_listed_file_below_its_ceiling_asks_to_lower_it(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/gros.py", 350)
    messages = controler(tmp_path, {"services/gros.py": 400})
    assert len(messages) == 1
    assert "services/gros.py" in messages[0]
    assert "350" in messages[0]
    assert "plafond 400" in messages[0]
    assert "baisse le plafond à 350" in messages[0]


def test_listed_file_back_under_general_ceiling_asks_to_drop_entry(tmp_path: Path) -> None:
    _ecrire(tmp_path, "services/gros.py", 120)
    messages = controler(tmp_path, {"services/gros.py": 400})
    assert len(messages) == 1
    assert "retire l'entrée de PLAFONDS" in messages[0]


def test_listed_file_that_no_longer_exists_fails(tmp_path: Path) -> None:
    messages = controler(tmp_path, {"services/disparu.py": 400})
    assert len(messages) == 1
    assert "services/disparu.py" in messages[0]
    assert "Retire l'entrée" in messages[0]


def test_pycache_is_ignored(tmp_path: Path) -> None:
    _ecrire(tmp_path, "__pycache__/gros.py", 500)
    assert controler(tmp_path, {}) == []
