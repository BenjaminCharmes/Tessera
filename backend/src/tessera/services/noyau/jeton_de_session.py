"""The session token every API request must carry — ticket-878.

`STATIC_TOKEN`, when set, is the token. When it is empty, the backend draws a
random one at startup and keeps it in memory: there is no open mode. A freshly
drawn token is also written to `ide_state_dir / "jeton-de-session"` so that the
interface can read it, and the file goes away at shutdown. A `STATIC_TOKEN`
written by the user is never copied to disk by this module, and starting with
one deletes the file a previous start left behind (a killed process never ran
`arreter()`), so that nothing reads a stale token.
"""
import secrets
from pathlib import Path

from tessera.config import settings
from tessera.utils.secrets import SECRETS

#: Nom du fichier qui porte un jeton généré, sous `ide_state_dir`.
NOM_DU_FICHIER = "jeton-de-session"


class _Etat:
    """The token drawn by this process, if any."""

    genere: str = ""


_ETAT = _Etat()


def chemin_du_fichier() -> Path:
    """Where a generated token is written."""
    return settings.ide_state_dir / NOM_DU_FICHIER


def courant() -> str | None:
    """The token a request must present, or None when none exists yet.

    Lu à chaque appel : `STATIC_TOKEN` l'emporte, et un changement de
    `settings` est vu sans redémarrage. `None` ne laisse rien passer : sans
    jeton, l'API refuse tout (elle échoue fermée).
    """
    return settings.static_token or _ETAT.genere or None


def demarrer() -> None:
    """Fix the effective token: `STATIC_TOKEN` if set, else a fresh random one.

    A fixed token also deletes the file left by an earlier start.
    """
    if settings.static_token:
        _ETAT.genere = ""
        SECRETS.register(settings.static_token)
        # Le fichier d'un démarrage antérieur (processus tué, `arreter()` non
        # exécuté) porte un jeton tiré qui ne vaut plus rien.
        chemin_du_fichier().unlink(missing_ok=True)
        return
    _ETAT.genere = secrets.token_urlsafe(32)
    SECRETS.register(_ETAT.genere)
    fichier = chemin_du_fichier()
    fichier.parent.mkdir(parents=True, exist_ok=True)
    fichier.write_text(_ETAT.genere, encoding="utf-8")
    # Lisible par l'utilisateur seul (sans effet sous Windows, où le dossier
    # d'état est déjà propre à son compte).
    fichier.chmod(0o600)


def arreter() -> None:
    """Forget the generated token and delete its file."""
    _ETAT.genere = ""
    chemin_du_fichier().unlink(missing_ok=True)
