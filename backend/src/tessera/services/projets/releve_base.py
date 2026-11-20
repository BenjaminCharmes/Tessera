"""Reads a project's files from its remote base branch, for the weekly report — ticket-1031.

No fetch, no network: only what the local clone already knows of ``origin/<base>``.
Every function answers ``None`` or an empty list on a git failure, so the caller
falls back on the working tree.
"""

import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from tessera.services.noyau.git_commande import build_command

TITRE_TICKET = re.compile(r"^#\s+ticket-\d+\s*[—-]\s*(?P<titre>.+)$", re.MULTILINE)
_FRONTMATTER = re.compile(r"\A---\r?\n(?P<corps>.*?)\r?\n---", re.DOTALL)
_TITRE_YAML = re.compile(r"^title:\s*(?P<titre>.+?)\s*$", re.MULTILINE)


def _git(projet: Path, *args: str) -> str | None:
    cmd = build_command(("-C", str(projet), *args))
    try:
        res = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=30, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return res.stdout if res.returncode == 0 else None


def reference_distante(projet: Path, base: object) -> str | None:
    """Return ``origin/<base>`` when that reference exists in the project's repository."""
    if not isinstance(base, str) or not base:
        return None
    ref = f"origin/{base}"
    ok = _git(projet, "rev-parse", "--verify", "--quiet", f"refs/remotes/{ref}^{{commit}}")
    return ref if ok is not None else None


def lire_fichier_base(projet: Path, ref: str, chemin: str) -> str | None:
    """Return the content of ``chemin`` (relative to the project) on ``ref``."""
    return _git(projet, "show", f"{ref}:./{chemin}")


def titre_de_fiche(texte: str) -> str | None:
    """Title of a ticket file: its ``# ticket-N — title`` line, else the ``title:`` frontmatter."""
    trouve = TITRE_TICKET.search(texte)
    if trouve:
        return trouve.group("titre").strip()
    front = _FRONTMATTER.match(texte)
    yaml = _TITRE_YAML.search(front.group("corps")) if front else None
    titre = yaml.group("titre").strip().strip("\"'").strip() if yaml else ""
    return titre or None


@dataclass
class FichesBase:
    """Ticket files of one reference, listed once."""

    projet: Path
    ref: str
    chemins: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        sortie = _git(self.projet, "ls-tree", "-r", "--name-only", self.ref, "--", "tickets")
        self.chemins = sorted(sortie.splitlines()) if sortie else []

    def titre(self, numero: str) -> str | None:
        """Title of ticket ``numero`` read on the reference, if its file is there."""
        for chemin in self.chemins:
            if not Path(chemin).name.startswith(f"ticket-{numero}-"):
                continue
            texte = lire_fichier_base(self.projet, self.ref, chemin)
            titre = titre_de_fiche(texte) if texte else None
            if titre:
                return titre
        return None
