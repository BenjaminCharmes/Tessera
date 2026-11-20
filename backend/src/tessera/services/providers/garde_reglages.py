"""An agent never changes the global settings over the network — ADR-075, ticket-809.

The `Origin` required by `PUT /api/v1/reglages` (ticket-808) stops a page and a
bare `curl`; this lexical check stops the agent that tries. The `.env` hook of
ADR-053 (`garde_jetons.py`) calls it on every `Bash` command.

**Ceiling.** It recognises a network command that names the route, nothing
more: `cur""l`, a script written then run, a hand-made HTTP client with a forged
`Origin` go through. It catches a mistake, not an evasion; the bounds of the
registry stay the real ceiling. The refusal message says so.
"""
import re

#: What the agent reads when the command is refused.
REGLAGES_REFUS = (
    "Exécution refusée : la route des réglages (`/api/v1/reglages`) est réservée à "
    "l'interface (ADR-075). Ce contrôle est lexical : il repère une commande réseau "
    "qui nomme la route, il attrape une erreur, pas une évasion ; le vrai plafond "
    "reste les bornes du registre. Un refus de hook est définitif ; si le ticket "
    "demande un autre plafond, dis-le dans ton rapport, c'est une action de "
    "l'utilisateur."
)

_ROUTE = "/api/v1/reglages"
# Même découpage en segments que `_COMMANDES` de `garde_jetons.py`.
_COMMANDES = re.compile(r"[;|&\n]+")
_AFFECTATION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
_CLIENTS_RESEAU = frozenset(
    {
        "curl", "wget", "http", "https",
        "invoke-webrequest", "iwr", "invoke-restmethod", "irm",
    }
)
_PYTHON = re.compile(r"^python[0-9.]*$")


def _nom(jeton: str) -> str:
    """Return a command word without quotes, folder or ``.exe``, in lower case."""
    nu = jeton.strip("'\"").replace("\\", "/").rsplit("/", 1)[-1].lower()
    return nu.removesuffix(".exe")


def _mots_de_commande(segment: str) -> list[str]:
    """The words of a segment, without leading assignments nor ``uv run``."""
    mots = [m for m in segment.split() if m]
    while mots and _AFFECTATION.match(mots[0]):
        mots.pop(0)
    if len(mots) > 2 and _nom(mots[0]) == "uv" and mots[1].lower() == "run":
        mots = mots[2:]
    return mots


def commande_vise_les_reglages(commande: str) -> bool:
    """True if a ``Bash`` command is a network call naming the settings route."""
    debut = 0
    for morceau in _COMMANDES.split(commande):
        position = commande.find(morceau, debut)
        debut = position + len(morceau)
        mots = _mots_de_commande(morceau)
        if not mots:
            continue
        premier = _nom(mots[0])
        if premier in _CLIENTS_RESEAU:
            if _ROUTE in morceau.lower():
                return True
        elif _PYTHON.match(premier) and "-c" in mots[1:]:
            # Le code d'un `-c` contient souvent des `;` : on lit jusqu'au bout.
            if _ROUTE in commande[position:].lower():
                return True
    return False
