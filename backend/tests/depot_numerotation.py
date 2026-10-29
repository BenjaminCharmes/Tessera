"""A throw-away clone with a bare `origin`, to test numbering against real git — ticket-659."""
import subprocess
from pathlib import Path


def git(cwd: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", "-c", "user.email=test@tessera.local", "-c", "user.name=Tessera test", *args],
        cwd=cwd, capture_output=True, check=False,
    )
    assert proc.returncode == 0, f"git {' '.join(args)} : {proc.stderr.decode()}"
    return proc.stdout.decode().strip()


def ecrire(depot: Path, chemin: str, contenu: str) -> None:
    fichier = depot / chemin
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(contenu, encoding="utf-8", newline="\n")


def commiter(depot: Path, message: str = "work") -> None:
    git(depot, "add", "-A")
    git(depot, "commit", "-q", "-m", message)


def fiche(numero: int, slug: str, dependances: str = "[]") -> str:
    return (
        f"---\nid: ticket-{numero}\ndepends_on: {dependances}\n---\n\n"
        f"# ticket-{numero} — {slug}\n"
    )


def creer_depot(tmp_path: Path) -> Path:
    """A clone on `develop` holding ticket-001, ticket-611, ADR-001, ADR-061 and a note citing ticket-611."""
    amont = tmp_path / "amont"
    amont.mkdir()
    git(amont, "init", "-q", "-b", "develop")
    ecrire(amont, "tickets/done/ticket-001-premier.md", fiche(1, "premier"))
    ecrire(amont, "tickets/todo/ticket-611-deja-la.md", fiche(611, "deja-la"))
    ecrire(amont, "memory/decisions.md", "# Décisions\n\n## ADR-001 — Un\n\n## ADR-061 — Base\n")
    ecrire(amont, "notes.md", "ancien : ticket-611\n")
    commiter(amont, "base")
    git(tmp_path, "clone", "-q", "--bare", str(amont), str(tmp_path / "origin.git"))
    clone = tmp_path / "clone"
    git(tmp_path, "clone", "-q", (tmp_path / "origin.git").as_uri(), str(clone))
    return clone


def pousser_une_branche(tmp_path: Path, branche: str, fichiers: dict[str, str]) -> None:
    """Push `branche` from a second clone: the first one only sees it after a fetch."""
    autre = tmp_path / f"autre-{branche}"
    git(tmp_path, "clone", "-q", (tmp_path / "origin.git").as_uri(), str(autre))
    git(autre, "checkout", "-q", "-b", branche)
    for chemin, contenu in fichiers.items():
        ecrire(autre, chemin, contenu)
    commiter(autre, f"work on {branche}")
    git(autre, "push", "-q", "origin", branche)
