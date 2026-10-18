"""Pending pipeline-log lines carried across a branch switch (ticket-331).

Les lignes que l'orchestrateur journalise après le push d'une livraison
(rebase, PR ouverte, confiée au CIWatcher) restent non commitées. Les
commiter avant de changer de branche les posait sur la branche du ticket
livré, déjà poussée et souvent déjà mergée : elles n'arrivaient jamais sur la
base. On les met de côté avant le changement, puis on les réécrit dans le
journal de la nouvelle branche, qui les commitera avec sa propre tenue de
livres.
"""
import asyncio
from pathlib import Path

_JOURNAL = Path("memory") / "pipeline-log.md"


async def _git(racine: Path, *args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=str(racine),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return proc.returncode or 0, stdout.decode("utf-8", errors="replace")


async def mettre_de_cote(racine: Path) -> list[str]:
    """Return the log lines added since HEAD, and restore the log to HEAD.

    Returns an empty list — and touches nothing — when the log is absent,
    untracked (local artifacts, ADR-021: git carries it across the switch on
    its own), unchanged, or when git cannot answer.
    """
    if not (racine / _JOURNAL).is_file():
        return []
    chemin = _JOURNAL.as_posix()
    code, diff = await _git(racine, "diff", "--no-color", "-U0", "HEAD", "--", chemin)
    if code != 0 or not diff.strip():
        return []
    lignes = [
        ligne[1:]
        for ligne in diff.splitlines()
        if ligne.startswith("+") and not ligne.startswith("+++")
    ]
    # Sans restauration réussie, on ne prétend rien avoir mis de côté : le
    # commit de tenue de livres emportera les lignes, comme avant.
    code, _ = await _git(racine, "checkout", "HEAD", "--", chemin)
    return lignes if code == 0 else []


async def journal_non_suivi(racine: Path) -> bool:
    """True when the log exists, is neither tracked nor ignored by git."""
    if not (racine / _JOURNAL).is_file():
        return False
    chemin = _JOURNAL.as_posix()
    code, _ = await _git(racine, "ls-files", "--error-unmatch", "--", chemin)
    if code == 0:
        return False
    # Ignoré (mode `local`, ADR-021) : git l'écrase sans refuser, rien à faire.
    code, _ = await _git(racine, "check-ignore", "-q", "--", chemin)
    return code != 0


async def mettre_de_cote_non_suivi(racine: Path, ref_distante: str) -> list[str]:
    """Return the lines of an untracked log that ``ref_distante`` also tracks, and delete it.

    The merge brings its own copy of the log, and git refuses to overwrite an
    untracked file (ticket-480). Nothing is touched — an empty list comes back
    — unless the log is untracked, not ignored, and present on the remote ref.
    ``ref_distante`` is relative to the project folder (``<ref>:./path``), so
    ``git_root: ancestor`` works too.
    """
    if not await journal_non_suivi(racine):
        return []
    chemin = _JOURNAL.as_posix()
    code, _ = await _git(racine, "cat-file", "-e", f"{ref_distante}:./{chemin}")
    if code != 0:
        return []
    journal = racine / _JOURNAL
    lignes = [
        ligne
        for ligne in journal.read_text(encoding="utf-8", errors="replace").splitlines()
        if ligne.strip()
    ]
    journal.unlink()
    return lignes


def reecrire(racine: Path, lignes: list[str]) -> None:
    """Append ``lignes`` to the log, skipping any line it already holds."""
    if not lignes:
        return
    journal = racine / _JOURNAL
    existant = journal.read_text(encoding="utf-8") if journal.exists() else ""
    deja = set(existant.splitlines())
    nouvelles = [ligne for ligne in lignes if ligne not in deja]
    if not nouvelles:
        return
    journal.parent.mkdir(parents=True, exist_ok=True)
    with journal.open("a", encoding="utf-8") as f:
        if existant and not existant.endswith("\n"):
            f.write("\n")
        f.write("".join(f"{ligne}\n" for ligne in nouvelles))
