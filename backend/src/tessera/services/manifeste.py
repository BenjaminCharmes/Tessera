"""The single reader and writer of a project's `agents.json` manifest — ticket-675.

Thirty `json.loads` calls used to read this file, each with its own `try/except`
and its own idea of what a missing or broken manifest means. Here a manifest
that is absent, unreadable, invalid JSON or not a JSON object reads as the same
thing for every caller: no keys at all. A key that is missing, or of the wrong
type, then gives the default documented on its accessor.

An unreadable manifest is logged once per file and per reason, not once per
reader: a run reads the manifest dozens of times.
"""
import json
import os
import threading
from pathlib import Path

from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: Name of the manifest at the root of a project.
NOM_MANIFESTE = "agents.json"

#: Files already reported as unreadable, with the reason. Cleared for a file as
#: soon as it reads fine again, so a second breakage is reported too.
_journalises: set[tuple[str, str]] = set()

#: Serialises the read-modify-write of `ecrire_clef` inside this process.
_verrou_ecriture = threading.Lock()


def chemin_manifeste(project_path: Path) -> Path:
    """The manifest file of a project."""
    return project_path / NOM_MANIFESTE


def _signaler(chemin: Path, raison: str) -> None:
    cle = (str(chemin), raison)
    if cle in _journalises:
        return
    _journalises.add(cle)
    _logger.warning("agents_json_illisible", extra={"path": str(chemin), "raison": raison})


def _oublier(chemin: Path) -> None:
    for cle in [c for c in _journalises if c[0] == str(chemin)]:
        _journalises.discard(cle)


def lire_fichier(chemin: Path) -> dict[str, object]:
    """The top-level members of a manifest file; `{}` when there is nothing usable.

    A missing file is silent (a project without a manifest is normal); one that
    exists but cannot be used is logged once.
    """
    if not chemin.is_file():
        return {}
    try:
        data = json.loads(chemin.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        _signaler(chemin, type(exc).__name__)
        return {}
    if not isinstance(data, dict):
        _signaler(chemin, "not_an_object")
        return {}
    _oublier(chemin)
    return data


def lire_manifeste(project_path: Path) -> dict[str, object]:
    """The top-level members of a project's manifest, `{}` when unusable."""
    return lire_fichier(chemin_manifeste(project_path))


def lire_valeur(project_path: Path, clef: str) -> object | None:
    """The raw value of a key, `None` when absent or when the manifest is unusable."""
    return lire_manifeste(project_path).get(clef)


def lire_chaine(project_path: Path, clef: str) -> str | None:
    """A string key; `None` when absent, mistyped or when the manifest is unusable."""
    valeur = lire_valeur(project_path, clef)
    return valeur if isinstance(valeur, str) else None


def lire_booleen(project_path: Path, clef: str) -> bool:
    """A boolean key; only a real `true` reads as `True`, everything else is `False`."""
    return lire_valeur(project_path, clef) is True


def lire_objet(project_path: Path, clef: str) -> dict[str, object] | None:
    """A JSON-object key; `None` when absent, mistyped or when the manifest is unusable."""
    valeur = lire_valeur(project_path, clef)
    return valeur if isinstance(valeur, dict) else None


def lire_liste(project_path: Path, clef: str) -> list[object] | None:
    """A JSON-array key; `None` when absent, mistyped or when the manifest is unusable."""
    valeur = lire_valeur(project_path, clef)
    return valeur if isinstance(valeur, list) else None


def lire_label_map(project_path: Path) -> dict[str, str]:
    """`github_sync.label_map`; `{}` when absent, mistyped or unusable.

    Only string-to-string entries are kept: the map is read as GitHub label names.
    """
    sync = lire_objet(project_path, "github_sync")
    brute = sync.get("label_map") if sync is not None else None
    if not isinstance(brute, dict):
        return {}
    return {k: v for k, v in brute.items() if isinstance(k, str) and isinstance(v, str)}


def lire_pour_modifier(project_path: Path) -> dict[str, object]:
    """The whole manifest, for a caller that will rewrite it.

    Unlike the other readers it refuses to guess: a missing file raises
    `FileNotFoundError`, invalid JSON or a non-object raises `ValueError`.
    Rewriting from `{}` after a failed read would erase the manifest.
    """
    chemin = chemin_manifeste(project_path)
    data = json.loads(chemin.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{chemin.name} is not a JSON object")
    return data


def _remplacer(chemin: Path, data: dict[str, object]) -> None:
    texte = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    temporaire = chemin.with_name(f"{chemin.name}.{os.getpid()}.tmp")
    temporaire.write_text(texte, encoding="utf-8")
    os.replace(temporaire, chemin)


def ecrire_manifeste(project_path: Path, data: dict[str, object]) -> None:
    """Rewrite the whole manifest with `data`, atomically, under the process lock."""
    chemin = chemin_manifeste(project_path)
    with _verrou_ecriture:
        _remplacer(chemin, data)
    _oublier(chemin)


def ecrire_clef(
    project_path: Path, clef: str, valeur: object, *, retirer: tuple[str, ...] = ()
) -> None:
    """Set one key and keep every other member of the manifest as it was.

    `retirer` names obsolete keys to drop in the same write. Read-modify-write
    under a process lock, replaced atomically so that a concurrent reader never
    sees a half-written file. A manifest that cannot be read starts again from
    an empty one (and is logged), as before.
    """
    chemin = chemin_manifeste(project_path)
    with _verrou_ecriture:
        data = lire_fichier(chemin)
        for ancienne in retirer:
            data.pop(ancienne, None)
        data[clef] = valeur
        _remplacer(chemin, data)
    _oublier(chemin)
