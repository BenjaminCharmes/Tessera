"""The ``settings`` JSON that keeps Tessera's CLAUDE files out of a hosted project."""
import json
from pathlib import Path

from tessera.services.projets.racine_depot import depot_au_dessus
from tessera.services.providers.consignes_ancetres import claude_md_ancetres_a_exclure
from tessera.services.providers.perimetre import racine_autorisee

# backend/src/tessera/services/providers/ → parents[5] = racine du dépôt
_REPO_ROOT: Path = Path(__file__).resolve().parents[5]


def depart_des_consignes(cwd: Path, racine_ecriture: Path) -> Path:
    """The folder from which ancestor CLAUDE files are excluded.

    Le dépôt de l'IDE pour un projet qui y vit. Un worktree de run est hors de
    ce dépôt (ADR-056) : le départ est alors la racine de son propre checkout,
    le premier ancêtre qui porte un ``.git`` (un fichier, pour un worktree lié),
    et à défaut la racine d'écriture reçue, qui n'exclut rien.
    """
    projet = cwd.resolve()
    if projet.is_relative_to(_REPO_ROOT.resolve()):
        return _REPO_ROOT
    depot = depot_au_dessus(projet)
    return depot if depot is not None else racine_ecriture


def reglages_sans_consignes_ancetres(
    cwd: Path | None, racine_ecriture: Path | None
) -> str | None:
    """The ``settings`` JSON excluding Tessera's CLAUDE files, or ``None``.

    Un projet est « ancestor » quand sa racine d'écriture n'est pas son propre
    dossier : on réutilise donc celle que le run a figée (ticket-119).
    """
    if cwd is None:
        return None
    racine = racine_ecriture if racine_ecriture is not None else racine_autorisee(cwd)
    ancestor = racine.resolve() != cwd.resolve()
    exclus = claude_md_ancetres_a_exclure(
        cwd, depart_des_consignes(cwd, racine), ancestor
    )
    if not exclus:
        return None
    return json.dumps({"claudeMdExcludes": exclus})
