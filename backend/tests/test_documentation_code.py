"""The code material the batch documentation reads — ticket-540, ADR-057."""
import asyncio
from pathlib import Path

import pytest

from tessera.services.documentation_code import MatiereCode, matiere_du_lot


async def _git(cwd: Path, *args: str) -> str:
    proc = await asyncio.create_subprocess_exec(
        "git", *args, cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    assert proc.returncode == 0, err.decode()
    return out.decode()


def _ecrire(racine: Path, fichiers: dict[str, str]) -> None:
    for chemin, texte in fichiers.items():
        cible = racine / chemin
        cible.parent.mkdir(parents=True, exist_ok=True)
        cible.write_bytes(texte.encode("utf-8"))


async def _ticket(
    depot: Path, numero: str, fichiers: dict[str, str], *, rester: bool = False
) -> None:
    """Commits `fichiers` on a `ticket-<numero>-x` branch cut from main."""
    await _git(depot, "checkout", "-q", "-b", f"ticket-{numero}-x", "main")
    _ecrire(depot, fichiers)
    await _git(depot, "add", "-A")
    await _git(depot, "commit", "-qm", f"feat: ticket-{numero}")
    if not rester:
        await _git(depot, "checkout", "-q", "main")


def _bloc(lettre: str, lignes: int, largeur: int = 99) -> str:
    return "".join(f"{lettre * largeur}\n" for _ in range(lignes))


@pytest.fixture
async def depot(tmp_path: Path) -> Path:
    racine = tmp_path / "depot"
    racine.mkdir()
    await _git(racine, "init", "-q", "-b", "main")
    await _git(racine, "config", "user.email", "t@t.local")
    await _git(racine, "config", "user.name", "t")
    _ecrire(racine, {"README.md": "doc\n", "backend/app.py": "x = 1\n"})
    await _git(racine, "add", "-A")
    await _git(racine, "commit", "-qm", "init")
    return racine


async def test_ancestor_project_diff_is_taken_from_repository_root(depot: Path) -> None:
    projet = depot / "projects" / "demo"
    await _ticket(depot, "001", {
        "backend/app.py": "x = 2\n",
        "backend/tickets/note.py": "n = 1\n",
        "projects/demo/tickets/ticket-001.md": "statut\n",
        "projects/demo/memory/pipeline-log.md": "log\n",
        "projects/demo/agents.json": "{}\n",
    })

    matiere = await matiere_du_lot(depot, projet, ["ticket-001"])

    diff = matiere.diffs[0].diff
    assert "backend/app.py" in diff
    assert "backend/tickets/note.py" in diff, "a tickets/ elsewhere is code"
    assert "projects/demo/tickets" not in diff
    assert "projects/demo/memory" not in diff
    assert "projects/demo/agents.json" not in diff
    assert "backend/app.py" in matiere.diffs[0].fichiers


async def test_readme_and_docs_are_excluded_from_the_diff(depot: Path) -> None:
    await _ticket(depot, "002", {
        "README.md": "nouvelle doc\n", "docs/guide.md": "g\n", "backend/app.py": "x = 3\n",
    })

    matiere = await matiere_du_lot(depot, depot, ["ticket-002"])

    assert "README.md" not in matiere.diffs[0].diff
    assert "docs/guide.md" not in matiere.diffs[0].diff
    assert matiere.diffs[0].fichiers == ["backend/app.py"]


async def test_lockfile_is_reduced_to_one_line(depot: Path) -> None:
    await _ticket(depot, "003", {
        "uv.lock": "".join(f"paquet-{i}\n" for i in range(200)),
        "backend/app.py": "x = 4\n",
    })

    matiere = await matiere_du_lot(depot, depot, ["ticket-003"])

    diff = matiere.diffs[0].diff
    assert "uv.lock: lockfile modified, 200 lines added, 0 deleted" in diff
    assert "paquet-150" not in diff
    assert "x = 4" in diff


async def test_a_ticket_diff_over_the_bound_is_cut_and_names_the_missing_files(
    depot: Path,
) -> None:
    await _ticket(depot, "004", {
        "a.py": _bloc("a", 70, 99), "b.py": _bloc("b", 70, 99), "c.py": "c = 1\n",
    })

    matiere = await matiere_du_lot(depot, depot, ["ticket-004"])

    diff = matiere.diffs[0]
    assert diff.non_montres == ["b.py"]
    assert "[diff tronqué : 1 fichiers non montrés : b.py]" in diff.diff
    assert "aaaa" in diff.diff and "c = 1" in diff.diff
    assert "bbbb" not in diff.diff


async def test_the_batch_bound_cuts_later_tickets_and_names_their_files(
    depot: Path,
) -> None:
    ids = [f"01{i}" for i in range(6)]
    for numero in ids:
        await _ticket(depot, numero, {f"f{numero}.py": _bloc("z", 100)})

    matiere = await matiere_du_lot(depot, depot, [f"ticket-{n}" for n in ids])

    assert all(d.non_montres == [] for d in matiere.diffs[:5])
    assert matiere.diffs[5].non_montres == ["f015.py"]
    montre = sum(len(d.diff) for d in matiere.diffs[:5])
    assert montre <= 60_000


async def test_modified_and_added_files_are_provided_never_deleted_ones(
    depot: Path,
) -> None:
    _ecrire(depot, {"supprime.py": "a = 1\n", "modifie.py": "m = 1\n"})
    await _git(depot, "add", "-A")
    await _git(depot, "commit", "-qm", "base")
    await _git(depot, "checkout", "-q", "-b", "ticket-020-x")
    (depot / "supprime.py").unlink()
    _ecrire(depot, {"modifie.py": "m = 2\n", "nouveau.py": "n = 1\n"})
    await _git(depot, "add", "-A")
    await _git(depot, "commit", "-qm", "feat: ticket-020")

    matiere = await matiere_du_lot(depot, depot, ["ticket-020"], base="main")

    chemins = [f.chemin for f in matiere.fichiers]
    assert sorted(chemins) == ["modifie.py", "nouveau.py"]
    assert "supprime.py" in matiere.diffs[0].fichiers
    assert next(f for f in matiere.fichiers if f.chemin == "modifie.py").contenu == "m = 2\n"


async def test_files_come_by_decreasing_changed_lines_and_a_long_one_keeps_its_hunks(
    depot: Path,
) -> None:
    await _ticket(depot, "021", {
        "petit.py": "p = 1\n", "moyen.py": _bloc("m", 5), "long.py": _bloc("l", 100),
    }, rester=True)

    matiere = await matiere_du_lot(depot, depot, ["ticket-021"], base="main")

    assert [f.chemin for f in matiere.fichiers] == ["moyen.py", "petit.py"]
    assert matiere.fichiers_non_montres == ["long.py"]
    assert "llll" in matiere.diffs[0].diff, "the long file stays there by its hunks"


async def test_file_contents_stop_at_the_total_bound(depot: Path) -> None:
    fichiers = {f"f{i}.py": _bloc("q", 70) for i in range(6)}
    await _ticket(depot, "022", fichiers, rester=True)

    matiere = await matiere_du_lot(depot, depot, ["ticket-022"], base="main")

    assert sum(len(f.contenu) for f in matiere.fichiers) <= 40_000
    assert len(matiere.fichiers) == 5
    assert matiere.fichiers_non_montres == ["f5.py"]


async def test_tickets_without_a_diff_are_listed_apart(depot: Path) -> None:
    await _ticket(depot, "030", {"docs/seul.md": "d\n", "projects/demo/tickets/t.md": "s\n"})
    await _ticket(depot, "031", {"backend/app.py": "x = 9\n"})

    matiere = await matiere_du_lot(
        depot, depot / "projects" / "demo", ["ticket-030", "ticket-031", "ticket-999"]
    )

    assert isinstance(matiere, MatiereCode)
    assert matiere.sans_diff == ["ticket-030", "ticket-999"]
    assert [d.ticket_id for d in matiere.diffs] == ["ticket-031"]
