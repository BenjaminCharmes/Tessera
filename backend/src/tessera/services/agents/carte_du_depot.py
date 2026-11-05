"""A map of the repository's tracked files, for the coder's first round — ticket-190.

Le codeur découvrait le dépôt à coups de `Glob` et relisait à chaque run les
mêmes fichiers de configuration. Chaque tour d'outil renvoie tout
l'historique : cette découverte se paie multipliée par le nombre de tours.
Une liste de fichiers, calculée sans LLM, la remplace pour l'essentiel.
"""
import asyncio
import posixpath
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from tessera.utils.logger import get_logger

if TYPE_CHECKING:
    from tessera.services.politique_run import PolitiqueRun

_logger = get_logger(__name__)

#: Au-delà, les dossiers les plus peuplés sont repliés.
MAX_ENTREES = 400
#: Le budget de la carte dans le prompt : elle est une aide, pas un contexte.
MAX_CARACTERES = 6_000


def replier(
    chemins: list[str], max_entrees: int = MAX_ENTREES, max_chars: int = MAX_CARACTERES
) -> str:
    """Renders `chemins` one per line, folding the most populated directories
    into `dossier/ (n fichiers)` until the map fits both bounds.

    Repliement du plus peuplé d'abord, le plus profond en cas d'égalité : un
    dossier de trente fichiers générés disparaît avant `src/`. Un dossier
    replié compte ce que ses sous-dossiers déjà repliés cachaient, sinon la
    carte mentirait sur ce qu'elle tait.
    """
    fichiers = sorted(set(chemins))
    replies: dict[str, int] = {}

    def rendu() -> str:
        lignes = fichiers + [f"{d}/ ({n} fichiers)" for d, n in replies.items()]
        return "\n".join(sorted(lignes))

    while len(fichiers) + len(replies) > max_entrees or len(rendu()) > max_chars:
        score: Counter[str] = Counter()
        for f in fichiers:
            if "/" in f:
                score[posixpath.dirname(f)] += 1
        for d, n in replies.items():
            parent = posixpath.dirname(d)
            if parent:
                score[parent] += n
        if not score:
            break
        cible = max(score, key=lambda d: (score[d], d.count("/")))
        if score[cible] <= 1:
            break
        prefixe = cible + "/"
        total = sum(1 for f in fichiers if posixpath.dirname(f) == cible)
        fichiers = [f for f in fichiers if posixpath.dirname(f) != cible]
        for d in [d for d in replies if d.startswith(prefixe)]:
            total += replies.pop(d)
        replies[cible] = total

    lignes = rendu().splitlines()
    if len(lignes) > max_entrees:
        lignes = lignes[:max_entrees]
    texte = "\n".join(lignes)
    if len(texte) > max_chars:
        texte = texte[:max_chars].rsplit("\n", 1)[0]
    return texte


class CarteDuDepot:
    """Lists the files git tracks under `racine`, relative to it."""

    def __init__(self, racine: Path) -> None:
        self._racine = racine

    @classmethod
    def depuis(cls, project_path: Path, politique: "PolitiqueRun") -> "CarteDuDepot":
        """The map of what the run may write to: the project, or the repository
        that contains it when the project declares `git_root: ancestor`."""
        return cls(politique.racine_ecriture(project_path))

    async def rendre(self) -> str:
        """The folded map, or an empty string when git has nothing to say.

        Un dossier sans dépôt, un git absent : une carte est une aide, pas
        une raison de faire tomber un run.
        """
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "ls-files", "-z",
                cwd=str(self._racine),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await proc.communicate()
        except OSError as exc:
            _logger.warning("carte_du_depot_indisponible", extra={"error": str(exc)})
            return ""
        if proc.returncode != 0:
            return ""
        chemins = [c for c in stdout.decode("utf-8", errors="replace").split("\0") if c]
        return replier(chemins)
