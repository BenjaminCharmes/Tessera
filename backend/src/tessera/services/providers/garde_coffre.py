"""An agent never runs the system vault — ADR-073, design §7.

The vault is not a file: ``Read``, ``Glob`` and ``Grep`` cannot reach it, only
``Bash`` can run it. The ``.env`` hook of ADR-053 (``garde_jetons.py``) calls
this lexical check on every ``Bash`` command.

**Ceiling.** It recognises named commands and texts, nothing more:
``__import__('key' + 'ring')`` or a script written then run go through. It
catches a mistake, not an evasion; a token's real ceiling is its scope and its
expiry. The refusal message says so.
"""
import re

#: What the agent reads when the command is refused.
COFFRE_REFUS = (
    "Exécution refusée : cette commande lit le coffre du système, qui porte les "
    "secrets de Tessera. Aucun agent ne le lit (ADR-073). Ce contrôle est lexical : "
    "il repère des commandes nommées, il attrape une erreur, pas une évasion, et le "
    "vrai plafond d'un jeton est sa portée et son expiration. Un refus de hook est "
    "définitif ; si le ticket demande un secret, dis-le dans ton rapport, c'est une "
    "action de l'utilisateur."
)

# Même découpage en segments que `_COMMANDES` de `garde_jetons.py`.
_COMMANDES = re.compile(r"[;|&\n]+")
_EXECUTABLES = frozenset({"cmdkey", "vaultcmd", "keyring", "secret-tool"})
_AFFECTATION = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")
# Une recherche textuelle cite le mot sans exécuter le coffre.
_RECHERCHES = frozenset(
    {"grep", "egrep", "fgrep", "rg", "ag", "ack", "findstr", "select-string", "sls"}
)
_TEXTES = re.compile(
    r"-m\s*['\"]?(?:keyring|tessera\.coffre_cli)\b"
    r"|\bimport\s+keyring\b|\bfrom\s+keyring\b"
    r"|get-storedcredential|credread|passwordvault",
    re.IGNORECASE,
)


def _nom(jeton: str) -> str:
    """Return a command word without quotes, folder or ``.exe``, in lower case."""
    nu = jeton.strip("'\"").replace("\\", "/").rsplit("/", 1)[-1].lower()
    return nu.removesuffix(".exe")


def _segment_execute_le_coffre(segment: str) -> bool:
    mots = [m for m in segment.split() if m]
    while mots and _AFFECTATION.match(mots[0]):
        mots.pop(0)
    if not mots:
        return False
    premier = _nom(mots[0])
    if premier in _EXECUTABLES:
        return True
    if premier == "security" and len(mots) > 1:
        sous_commande = mots[1].lower()
        if sous_commande.endswith(("-generic-password", "-internet-password")):
            return True
    if premier in _RECHERCHES:
        return False
    return _TEXTES.search(segment) is not None


def commande_execute_le_coffre(commande: str) -> bool:
    """True if a ``Bash`` command runs the vault (lexical, see the module doc)."""
    return any(_segment_execute_le_coffre(s) for s in _COMMANDES.split(commande))
