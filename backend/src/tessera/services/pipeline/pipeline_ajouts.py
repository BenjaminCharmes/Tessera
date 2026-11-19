"""Protected files added during an agent call — ticket-1021 (ADR-088).

L'empreinte de `pipeline_empreinte` ne hache que les fichiers protégés qui
existent déjà : un `CLAUDE.md` ou un `.mcp.json` créé dans un sous-dossier n'a
pas d'empreinte avant. Ce module liste les fichiers ajoutés (non suivis, dépliés,
ou indexés en ajout) et garde ceux que `motif_de_protection` désigne ; ils
entrent dans l'empreinte, donc un fichier apparu entre deux empreintes est une
différence. Un fichier suivi et inchangé n'est jamais listé.
"""
import hashlib
from pathlib import Path

from tessera.services.git_workspace.git_runner import git
from tessera.services.providers.chemins_proteges import motif_de_protection


def _chemins_ajoutes(sortie: str) -> list[str]:
    """Paths of untracked or newly added entries in `git status --porcelain -z`."""
    morceaux = sortie.split("\0")
    ajoutes: list[str] = []
    i = 0
    while i < len(morceaux):
        entree = morceaux[i]
        i += 1
        if len(entree) < 4:
            continue
        etat, chemin = entree[:2], entree[3:]
        if "R" in etat or "C" in etat:
            i += 1  # le chemin d'origine suit, il n'est pas ajouté
        if etat == "??" or "A" in etat or "R" in etat or "C" in etat:
            ajoutes.append(chemin)
    return ajoutes


def _condenser(chemin: Path) -> str | None:
    try:
        return hashlib.sha256(chemin.read_bytes()).hexdigest()
    except OSError:
        return None


async def ajouts_proteges(
    projet: Path, racine: Path, script: Path | None
) -> dict[str, str | None]:
    """Name → hash of each added file that is protected; empty outside a repository."""
    res = await git(racine, "status", "--porcelain", "-z", "--untracked-files=all")
    if res.code != 0:
        return {}
    trouves: dict[str, str | None] = {}
    for chemin in _chemins_ajoutes(res.out):
        cible = racine / chemin
        if motif_de_protection(str(cible), projet, racine, script) is not None:
            trouves[chemin] = _condenser(cible)
    return trouves
