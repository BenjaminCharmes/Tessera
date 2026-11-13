"""Les ports que Tessera occupe, et ce qu'un service de projet en vise — ticket-967.

Un service de projet sur l'origine du frontend de Tessera recevrait les
identifiants que le navigateur y enregistre pour le jeton de session.
"""
import re

#: Backend de Tessera, puis Vite de l'IDE et ses variantes d'origine admises
#: par `auth.py` (5173-5176).
PORTS_DE_TESSERA: frozenset[int] = frozenset({8100, *range(5173, 5177)})

#: Port de Vite quand la commande n'en dit rien.
PORT_PAR_DEFAUT_DE_VITE = 5173

_PORT_EXPLICITE = re.compile(
    r"(?:^|\s)(?:--port|-p)(?:=|\s+)(\d{2,5})\b|(?:^|\s)PORT=(\d{2,5})\b"
)
_LANCE_VITE = re.compile(r"\bvite\b|\bnpm\s+run\s+dev\b|\b(?:pnpm|yarn)\s+dev\b")


def port_vise(commande: str) -> int | None:
    """Return the port a service command targets, or None when unknown.

    An explicit `--port N`, `-p N` or `PORT=N` wins; a bare `vite` or
    `npm run dev` counts as Vite's default port.
    """
    trouves = _PORT_EXPLICITE.findall(commande)
    if trouves:
        premier = trouves[0]
        return int(premier[0] or premier[1])
    if _LANCE_VITE.search(commande):
        return PORT_PAR_DEFAUT_DE_VITE
    return None


def conflit_avec_tessera(commande: str) -> int | None:
    """Return the Tessera port a command would occupy, or None."""
    port = port_vise(commande)
    return port if port in PORTS_DE_TESSERA else None
