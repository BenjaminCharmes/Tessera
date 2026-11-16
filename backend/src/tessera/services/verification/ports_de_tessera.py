"""Les ports que Tessera occupe, et ce qu'un service de projet en vise — ticket-967.

Un service de projet sur l'origine du frontend de Tessera recevrait les
identifiants que le navigateur y enregistre pour le jeton de session.
"""
import json
import re
from pathlib import Path

#: Backend de Tessera, puis Vite de l'IDE et ses variantes d'origine admises
#: par `auth.py` (5173-5176).
PORTS_DE_TESSERA: frozenset[int] = frozenset({8100, *range(5173, 5177)})

#: Port de Vite quand la commande n'en dit rien.
PORT_PAR_DEFAUT_DE_VITE = 5173

_PORT_EXPLICITE = re.compile(
    r"(?:^|\s)(?:--port|-p)(?:=|\s+)(\d{2,5})\b|(?:^|\s)PORT=(\d{2,5})\b"
)
_LANCE_VITE = re.compile(r"\bvite\b|\bnpm\s+run\s+dev\b|\b(?:pnpm|yarn)\s+dev\b")


_LANCE_VITE_DIRECTEMENT = re.compile(r"\bvite\b")
_COMMANDE_DE_SCRIPT = re.compile(r"\bnpm\s+run\s+dev\b|\b(?:pnpm|yarn)\s+dev\b")
_BLOC_SERVER = re.compile(r"\bserver\s*:\s*\{")
_PORT_DE_CONFIG = re.compile(r"\bport\s*:\s*(\d{2,5})\b")
_CONFIGS_VITE = ("vite.config.ts", "vite.config.mts", "vite.config.js", "vite.config.mjs")


def _port_explicite(texte: str) -> int | None:
    trouves = _PORT_EXPLICITE.findall(texte)
    if not trouves:
        return None
    return int(trouves[0][0] or trouves[0][1])


def _script_dev(dossier: Path) -> str | None:
    """Return the `dev` script of the folder's package.json, None if unreadable."""
    try:
        donnees = json.loads((dossier / "package.json").read_text(encoding="utf-8"))
        script = donnees["scripts"]["dev"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return script if isinstance(script, str) else None


def _bloc_server(texte: str) -> str | None:
    """Return the text of the first `server: { ... }` block, braces balanced."""
    debut = _BLOC_SERVER.search(texte)
    if debut is None:
        return None
    profondeur = 1
    for i in range(debut.end(), len(texte)):
        profondeur += {"{": 1, "}": -1}.get(texte[i], 0)
        if profondeur == 0:
            return texte[debut.end():i]
    return None


def _port_de_config_vite(dossier: Path) -> int | None:
    """Read `server.port` from the folder's vite config without running it."""
    for nom in _CONFIGS_VITE:
        try:
            texte = (dossier / nom).read_text(encoding="utf-8")
        except OSError:
            continue
        bloc = _bloc_server(texte)
        trouve = _PORT_DE_CONFIG.search(bloc) if bloc is not None else None
        return int(trouve.group(1)) if trouve else None
    return None


def _port_d_un_script(dossier: Path) -> int | None:
    """Port of an `npm run dev`-style command: the script, then vite's config."""
    script = _script_dev(dossier)
    if script is None:
        return PORT_PAR_DEFAUT_DE_VITE
    explicite = _port_explicite(script)
    if explicite is not None:
        return explicite
    if not _LANCE_VITE_DIRECTEMENT.search(script):
        return None
    return _port_de_config_vite(dossier) or PORT_PAR_DEFAUT_DE_VITE


def port_vise(commande: str, dossier: Path | None = None) -> int | None:
    """Return the port a service command targets, or None when unknown.

    An explicit `--port N`, `-p N` or `PORT=N` wins; a bare `vite` or
    `npm run dev` counts as Vite's default port, unless `dossier` (the
    service's working folder) says otherwise in its package.json or
    vite config.
    """
    explicite = _port_explicite(commande)
    if explicite is not None:
        return explicite
    if not _LANCE_VITE.search(commande):
        return None
    if dossier is None:
        return PORT_PAR_DEFAUT_DE_VITE
    if _LANCE_VITE_DIRECTEMENT.search(commande):
        return _port_de_config_vite(dossier) or PORT_PAR_DEFAUT_DE_VITE
    return _port_d_un_script(dossier)


def conflit_avec_tessera(commande: str, dossier: Path | None = None) -> int | None:
    """Return the Tessera port a command would occupy, or None."""
    port = port_vise(commande, dossier)
    return port if port in PORTS_DE_TESSERA else None
