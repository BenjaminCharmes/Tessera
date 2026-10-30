"""The `captures` section of a project's `agents.json` — ticket-432.

Comme les services (ADR-042), les écrans à capturer se **déclarent** : on ne
devine pas les routes d'une app. Une section absente, mal typée ou sans écran
valide vaut « ce projet ne se capture pas » — l'API répond alors 409 en disant
quoi écrire.
"""
import re
from dataclasses import dataclass
from pathlib import Path

from tessera.services.manifeste import lire_valeur

#: Largeurs en pixels : téléphone puis ordinateur.
LARGEURS: tuple[int, ...] = (390, 1440)
THEMES: tuple[str, ...] = ("clair", "sombre")
#: Bornes d'une largeur déclarée, en pixels.
LARGEUR_MIN = 200
LARGEUR_MAX = 3000

_CARACTERES_INTERDITS = re.compile(r"[^a-z0-9-]+")


@dataclass(frozen=True)
class Ecran:
    """One screen to capture: a name, a path to open and an optional click."""

    nom: str
    chemin: str
    clic: str = ""


@dataclass(frozen=True)
class SessionCaptures:
    """How to open a session before capturing — never holds the token itself.

    `jeton_env` names the variable to read in `fichier_env` (relative to the
    project root) ; the value stays server-side (ticket-437).
    """

    chemin: str
    jeton_env: str
    fichier_env: str = ".env"


@dataclass(frozen=True)
class ConfigCaptures:
    """Where the project's app answers and which screens to capture."""

    url: str
    ecrans: tuple[Ecran, ...]
    session: SessionCaptures | None = None
    largeurs: tuple[int, ...] = LARGEURS
    themes: tuple[str, ...] = THEMES


def _largeurs(brut: object) -> tuple[int, ...]:
    """Read `largeurs` ; anything unusable falls back to the defaults."""
    if not isinstance(brut, list) or not brut:
        return LARGEURS
    # `bool` est un `int` en Python : `true` ne serait pas une largeur.
    if not all(type(v) is int and LARGEUR_MIN <= v <= LARGEUR_MAX for v in brut):
        return LARGEURS
    if len(set(brut)) != len(brut):
        return LARGEURS
    return tuple(brut)


def _themes(brut: object) -> tuple[str, ...]:
    """Read `themes` ; anything unusable falls back to the defaults."""
    if not isinstance(brut, list) or not brut:
        return THEMES
    if not all(isinstance(v, str) and v in THEMES for v in brut):
        return THEMES
    if len(set(brut)) != len(brut):
        return THEMES
    return tuple(brut)


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


def _session(brut: dict[str, object]) -> SessionCaptures | None:
    chemin, jeton_env = brut.get("chemin"), brut.get("jeton_env")
    fichier_env = brut.get("fichier_env", ".env")
    if not isinstance(chemin, str) or not chemin.startswith("/"):
        return None
    if not isinstance(jeton_env, str) or not jeton_env.strip():
        return None
    if not isinstance(fichier_env, str) or not fichier_env.strip():
        return None
    return SessionCaptures(chemin, jeton_env.strip(), fichier_env.strip())


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
    session = None
    if "session" in brut:
        # Une `session` déclarée mais illisible n'est pas ignorée : on
        # capturerait l'écran de connexion en croyant voir l'app.
        brut_session = brut["session"]
        session = _session(brut_session) if isinstance(brut_session, dict) else None
        if session is None:
            return None
    return ConfigCaptures(
        url=url.rstrip("/"),
        ecrans=valides,
        session=session,
        largeurs=_largeurs(brut.get("largeurs")),
        themes=_themes(brut.get("themes")),
    )


def parse_captures_config(brut: object) -> ConfigCaptures | None:
    """Validate a raw `captures` section, or return None when unusable."""
    return _config(brut)


def load_captures_config(project_path: Path) -> ConfigCaptures | None:
    """Read `captures` from `agents.json`, or return None when unusable."""
    return _config(lire_valeur(project_path, "captures"))
