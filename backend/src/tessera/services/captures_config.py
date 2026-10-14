"""The `captures` section of a project's `agents.json` — ticket-432.

Comme les services (ADR-042), les écrans à capturer se **déclarent** : on ne
devine pas les routes d'une app. Une section absente, mal typée ou sans écran
valide vaut « ce projet ne se capture pas » — l'API répond alors 409 en disant
quoi écrire.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path

#: Largeurs en pixels : téléphone puis ordinateur.
LARGEURS: tuple[int, ...] = (390, 1440)
THEMES: tuple[str, ...] = ("clair", "sombre")

_CARACTERES_INTERDITS = re.compile(r"[^a-z0-9-]+")


@dataclass(frozen=True)
class Ecran:
    """One screen to capture: a name, a path to open and an optional click."""

    nom: str
    chemin: str
    clic: str = ""


@dataclass(frozen=True)
class ConfigCaptures:
    """Where the project's app answers and which screens to capture."""

    url: str
    ecrans: tuple[Ecran, ...]


def nom_de_fichier(nom: str) -> str:
    """Reduce a screen name to `[a-z0-9-]` so it is safe as a file name."""
    return _CARACTERES_INTERDITS.sub("-", nom.strip().lower()).strip("-")


def _ecran(brut: object) -> Ecran | None:
    if not isinstance(brut, dict):
        return None
    nom = nom_de_fichier(str(brut.get("nom") or ""))
    chemin = brut.get("chemin")
    if not nom or not isinstance(chemin, str) or not chemin.startswith("/"):
        return None
    clic = brut.get("clic")
    return Ecran(nom=nom, chemin=chemin, clic=clic if isinstance(clic, str) else "")


def _config(brut: object) -> ConfigCaptures | None:
    if not isinstance(brut, dict):
        return None
    url, ecrans = brut.get("url"), brut.get("ecrans")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return None
    if not isinstance(ecrans, list):
        return None
    valides = tuple(e for e in map(_ecran, ecrans) if e is not None)
    if not valides:
        return None
    return ConfigCaptures(url=url.rstrip("/"), ecrans=valides)


def load_captures_config(project_path: Path) -> ConfigCaptures | None:
    """Read `captures` from `agents.json`, or return None when unusable."""
    agents_json = project_path / "agents.json"
    if not agents_json.exists():
        return None
    try:
        data = json.loads(agents_json.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    return _config(data.get("captures"))
