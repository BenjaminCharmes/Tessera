"""Pending pipeline-log lines carried across a branch switch (ticket-331).

Les lignes que l'orchestrateur journalise après le push d'une livraison
(rebase, PR ouverte, confiée au CIWatcher) restent non commitées. Les
commiter avant de changer de branche les posait sur la branche du ticket
livré, déjà poussée et souvent déjà mergée : elles n'arrivaient jamais sur la
base. On les met de côté avant le changement, puis on les réécrit dans le
journal de la nouvelle branche, qui les commitera avec sa propre tenue de
livres.
"""
from pathlib import Path

from tessera.services.git_runner import git

_JOURNAL = Path("memory") / "pipeline-log.md"


async def mettre_de_cote(racine: Path) -> list[str]:
    """Return the log lines added since HEAD, and restore the log to HEAD.

    Returns an empty list — and touches nothing — when the log is absent,
    untracked (local artifacts, ADR-021: git carries it across the switch on
    its own), unchanged, or when git cannot answer.
    """
    if not (racine / _JOURNAL).is_file():
        return []
    chemin = _JOURNAL.as_posix()
    diff = await git(racine, "diff", "--no-color", "-U0", "HEAD", "--", chemin)
    if not diff.ok or not diff.out.strip():
        return []
    lignes = [
        ligne[1:]
        for ligne in diff.out.splitlines()
        if ligne.startswith("+") and not ligne.startswith("+++")
    ]
    # Sans restauration réussie, on ne prétend rien avoir mis de côté : le
    # commit de tenue de livres emportera les lignes, comme avant.
    restauration = await git(racine, "checkout", "HEAD", "--", chemin)
    return lignes if restauration.ok else []


async def seul_le_journal_est_modifie(racine: Path) -> bool:
    """True when the log is the only tracked file with local changes in the repository.

    The whole repository is looked at, not only the project folder: under
    ``git_root: ancestor`` the work lives above it. False — and the caller
    keeps its current behaviour — on any other change, or when git cannot answer.
    """
    prefixe = await git(racine, "rev-parse", "--show-prefix")
    if not prefixe.ok:
        return False
    statut = await git(racine, "status", "--porcelain", "--untracked-files=no")
    if not statut.ok:
        return False
    attendu = prefixe.out.strip() + _JOURNAL.as_posix()
    chemins = [
        ligne[3:].strip() for ligne in statut.out.splitlines() if len(ligne) >= 3
    ]
    return bool(chemins) and all(chemin == attendu for chemin in chemins)


async def journal_non_suivi(racine: Path) -> bool:
    """True when the log exists, is neither tracked nor ignored by git."""
    if not (racine / _JOURNAL).is_file():
        return False
    chemin = _JOURNAL.as_posix()
    if (await git(racine, "ls-files", "--error-unmatch", "--", chemin)).ok:
        return False
    # Ignoré (mode `local`, ADR-021) : git l'écrase sans refuser, rien à faire.
    return not (await git(racine, "check-ignore", "-q", "--", chemin)).ok


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
    if not (await git(racine, "cat-file", "-e", f"{ref_distante}:./{chemin}")).ok:
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
