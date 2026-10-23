"""A code material source for documentation tests that run outside a git repository."""
from pathlib import Path

from tessera.services.documentation_code import (
    DiffDeTicket,
    FichierLivre,
    FournisseurMatiere,
    MatiereCode,
)


def matiere_factice(sans_diff: tuple[str, ...] = ()) -> FournisseurMatiere:
    """One diff and one file per ticket, except the tickets named in `sans_diff`."""

    async def matiere(
        racine: Path, projet: Path, tickets: list[str], base: str | None
    ) -> MatiereCode:
        retenus = [t for t in tickets if t not in sans_diff]
        return MatiereCode(
            diffs=[
                DiffDeTicket(
                    t, f"diff --git a/src/{t}.py b/src/{t}.py\n+code de {t}\n", [f"src/{t}.py"]
                )
                for t in retenus
            ],
            fichiers=[FichierLivre(f"src/{t}.py", f"contenu de {t}\n") for t in retenus],
            sans_diff=[t for t in tickets if t in sans_diff],
        )

    return matiere
