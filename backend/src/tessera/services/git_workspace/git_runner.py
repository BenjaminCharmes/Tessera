"""The one git command runner of the backend services — ticket-677.

Sept modules lançaient chacun leur `git`, avec trois types de retour et, pour
quatre d'entre eux, sans neutraliser les hooks : un `pre-commit` ou un
`post-checkout` déposé dans `.git/hooks/` pendant un run s'exécutait alors sous
l'identité du backend (ADR-027). Un seul exécuteur, un seul résultat.

Les hooks sont neutralisés pour toute commande qui n'est pas une lecture connue
(`-c core.hooksPath=<dossier vide>`, qui prime sur `.git/config`). Le choix se
fait sur une liste blanche de lectures : une sous-commande inconnue est traitée
comme une écriture. Les lectures ne paient donc pas la création du dossier vide.
"""
import asyncio
from dataclasses import dataclass
from pathlib import Path

from tessera.services.noyau.git_commande import _dossier_sans_hooks, build_command, writes  # noqa: F401 — réexport


@dataclass(frozen=True)
class GitResult:
    """What a git command returned: exit code, decoded stdout, decoded stderr."""

    code: int
    out: str
    err: str
    command: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.code == 0


async def git(cwd: Path, *args: str) -> GitResult:
    """Run git in `cwd`; never raises on a non-zero exit, the caller reads `code`."""
    command = build_command(args)
    proc = await asyncio.create_subprocess_exec(
        *command,
        cwd=str(cwd),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, err = await proc.communicate()
    return GitResult(
        code=proc.returncode or 0,
        out=out.decode("utf-8", errors="replace"),
        err=err.decode("utf-8", errors="replace"),
        command=tuple(command),
    )

