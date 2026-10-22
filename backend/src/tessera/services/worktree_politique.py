"""Lecture validée de la clé `worktree` d'`agents.json` — ticket-521, ADR-056.

Chaque règle échoue fermée : une clé mal typée vaut « pas de worktree », et une
entrée de `populate` douteuse est retirée sans emporter les autres. Rien ne
consomme encore cette valeur : elle voyage dans `PolitiqueRun`, lue une fois.
"""
import json
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TypeGuard

from pydantic import ValidationError

from tessera.config import Settings
from tessera.models.worktree_config import ConfigWorktree, EntreePopulate
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

_CLEF = "worktree"


def lire_worktree(
    project_path: Path, racine_depot: Path, artifacts: str
) -> ConfigWorktree | None:
    """La configuration validée, ou `None` : le run reste dans le checkout.

    `racine_depot` est la base des chemins de `populate` (ADR-056, § 2).
    """
    declaration = _declaration(project_path)
    if declaration is None:
        return None
    if artifacts != "tracked":
        # Les artefacts d'un projet `local` ne sont pas dans git : un worktree
        # ne les verrait pas, et les rapatrier reste à concevoir (spec, § fin).
        _logger.warning(
            "worktree_ignore", extra={"raison": "artifacts_local", "projet": str(project_path)}
        )
        return None
    return _valider(declaration, racine_depot)


def _declaration(project_path: Path) -> object | None:
    """La valeur brute de la clé `worktree`, `None` si absente ou illisible."""
    agents_json = project_path / "agents.json"
    if not agents_json.is_file():
        return None
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    return data.get(_CLEF) if isinstance(data, dict) else None


def _valider(declaration: object, racine_depot: Path) -> ConfigWorktree | None:
    if not isinstance(declaration, dict):
        _mal_type("declaration")
        return None
    brutes = declaration.get("populate", [])
    env = declaration.get("env", {})
    commande = declaration.get("test_command")
    if not isinstance(brutes, list) or not _env_valide(env):
        _mal_type("populate_ou_env")
        return None
    if commande is not None and not isinstance(commande, str):
        _mal_type("test_command")
        return None
    preparation = declaration.get("setup")
    if preparation is not None and not isinstance(preparation, str):
        _mal_type("setup")
        return None
    entrees = tuple(e for e in (_entree(b, racine_depot) for b in brutes) if e is not None)
    return ConfigWorktree(
        populate=entrees, env=dict(env), test_command=commande, setup=preparation
    )


def _mal_type(champ: str) -> None:
    _logger.warning("worktree_mal_type", extra={"champ": champ})


def _env_valide(env: object) -> TypeGuard[dict[str, str]]:
    return isinstance(env, dict) and all(
        isinstance(k, str) and isinstance(v, str) for k, v in env.items()
    )


def _entree(brute: object, racine_depot: Path) -> EntreePopulate | None:
    """L'entrée validée, ou `None` — retirée et journalisée avec sa raison."""
    if not isinstance(brute, dict):
        _retirer(brute, "entree_mal_typee")
        return None
    try:
        entree = EntreePopulate.model_validate(brute)
    except ValidationError:
        _retirer(brute, "mode_inconnu_ou_chemin_absent")
        return None
    raison = _raison_de_refus(entree.path, racine_depot)
    if raison:
        _retirer(brute, raison)
        return None
    return entree


def _raison_de_refus(chemin: str, racine_depot: Path) -> str | None:
    if not chemin.strip():
        return "chemin_vide"
    if _est_absolu(chemin):
        return "chemin_absolu"
    if ".." in chemin.replace("\\", "/").split("/"):
        return "chemin_avec_point_point"
    if _resout_au_env_de_tessera(chemin, racine_depot):
        return "env_de_tessera"
    return None


def _est_absolu(chemin: str) -> bool:
    """Absolu sous l'une ou l'autre syntaxe : le chemin se joue sur Windows et ailleurs."""
    return (
        PurePosixPath(chemin).is_absolute()
        or PureWindowsPath(chemin).is_absolute()
        or chemin.startswith(("/", "\\"))
        or PureWindowsPath(chemin).drive != ""
    )


def _resout_au_env_de_tessera(chemin: str, racine_depot: Path) -> bool:
    """ADR-053 : copier ce fichier dans un dossier où l'agent écrit le lui rendrait lisible."""
    try:
        return (racine_depot / chemin).resolve() == Settings.env_file.resolve()
    except OSError:
        # Un chemin qu'on ne sait pas résoudre ne se juge pas : il se refuse.
        return True


def _retirer(brute: object, raison: str) -> None:
    _logger.warning("worktree_populate_retire", extra={"entree": repr(brute), "raison": raison})
