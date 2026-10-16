"""An agent never reads Tessera's own ``.env`` — ADR-053, ticket-464.

The ``.env`` at the repository root holds the online-service tokens. ADR-031
lets an agent read outside its project, and ``Read``, ``Glob`` and ``Grep`` go
through no other hook: without this one, an agent would read the file.

Same shape as ``perimetre.py``: a ``PreToolUse`` hook, because an
``allowed_tools`` entry auto-approves a tool *before* any permission callback.

**Ceiling.** ``Bash`` is covered by a lexical scan of the paths written in the
command: ``cat ../../.env``, ``type``, ``Get-Content``. It catches a mistake,
not an evasion — ``python -c "open('../../' + '.env')"`` goes through. A token's
real ceiling is its scope and its expiry, not this hook. The refusal message
says so.

Only the ``.env`` of Tessera is refused: a project's own ``.env`` and
``.env.example`` are different files and pass.
"""
import fnmatch
import os
import re
from pathlib import Path
from typing import Any, Awaitable, Callable

from claude_agent_sdk import HookContext, HookInput, HookJSONOutput

from tessera.config import Settings
from tessera.utils.logger import get_logger

_logger = get_logger(__name__)

#: What the agent reads when the path is refused.
ENV_REFUS = (
    "Lecture refusée : ce fichier est le `.env` de Tessera, qui porte les jetons "
    "de mise en ligne. Aucun agent ne les reçoit ni ne les lit (ADR-053). Ce "
    "refus repère les chemins nommés, rien de plus : il attrape une erreur, pas "
    "une évasion, et le vrai plafond d'un jeton est sa portée et son expiration. "
    "Un refus de hook est définitif ; si le ticket demande une valeur de ce "
    "fichier, dis-le dans ton rapport, c'est une action de l'utilisateur."
)

_GIT_BASH = re.compile(r"^/([a-zA-Z])/(.*)$")
_SEPARATEURS = re.compile(r"[\s;|&<>()=,`]+")
_JOKERS = "*?[{"


def _resoudre(brut: str, base: Path) -> Path | None:
    """Resolve a raw path against ``base``; ``None`` when it cannot be read."""
    texte = brut.strip().strip("'\"").replace("\\", "/")
    if os.name == "nt":
        # Git Bash écrit `/c/Users/...` : le même fichier que `C:/Users/...`.
        correspondance = _GIT_BASH.match(texte)
        if correspondance:
            texte = f"{correspondance[1].upper()}:/{correspondance[2]}"
    try:
        chemin = Path(texte)
        if not chemin.is_absolute():
            chemin = base / chemin
        return chemin.resolve()
    except (OSError, ValueError):
        return None


def vise_le_env(brut: str, base: Path, env_file: Path) -> bool:
    """True if the path ``brut`` (absolute, relative or with ``..``) is the file."""
    chemin = _resoudre(brut, base)
    return chemin is not None and chemin == env_file


def motif_vise_le_env(motif: str, base: Path, env_file: Path) -> bool:
    """True if a glob ``motif`` names the file explicitly and can reach it.

    The last segment must start with a literal character: ``*`` alone does not
    name a dotfile, and refusing it would forbid listing any folder.
    """
    segments = motif.replace("\\", "/").split("/")
    dernier = segments[-1]
    if not dernier or dernier[0] in _JOKERS:
        return False
    if not fnmatch.fnmatch(env_file.name.lower(), dernier.lower()):
        return False
    fixes: list[str] = []
    for segment in segments[:-1]:
        if any(joker in segment for joker in _JOKERS):
            break
        fixes.append(segment)
    prefixe = "/".join(fixes) or ("/" if motif.startswith(("/", "\\")) else ".")
    racine = _resoudre(prefixe, base)
    return racine is not None and env_file.is_relative_to(racine)


def _commande_vise_le_env(commande: str, base: Path, env_file: Path) -> bool:
    """Lexical scan of a ``Bash`` command for a path to the file."""
    for jeton in _SEPARATEURS.split(commande):
        nu = jeton.strip("'\"").replace("\\", "/")
        if nu.rsplit("/", 1)[-1].lower() == env_file.name.lower():
            if vise_le_env(nu, base, env_file):
                return True
    return False


def _outil_vise_le_env(
    outil: object, entrees: dict[str, Any], base: Path, env_file: Path
) -> bool:
    if outil == "Read":
        return vise_le_env(str(entrees.get("file_path", "")), base, env_file)
    if outil == "Bash":
        return _commande_vise_le_env(str(entrees.get("command", "")), base, env_file)
    if outil not in ("Glob", "Grep"):
        return False
    dossier = _resoudre(str(entrees.get("path") or "."), base) or base
    if outil == "Grep" and entrees.get("path") and vise_le_env(
        str(entrees["path"]), base, env_file
    ):
        return True
    motif = entrees.get("pattern" if outil == "Glob" else "glob")
    return bool(motif) and motif_vise_le_env(str(motif), dossier, env_file)


def hook_refus_env_tessera(
    cwd: Path | None, env_file: Path | None = None
) -> Callable[[HookInput, str | None, HookContext], Awaitable[HookJSONOutput]]:
    """Build the ``PreToolUse`` hook refusing reads of Tessera's ``.env``.

    Relative paths resolve against ``cwd``, the run's working folder; without
    one, against the process's. ``env_file`` defaults to ``Settings.env_file``
    and is resolved once, here.
    """
    base = (cwd if cwd is not None else Path.cwd()).resolve()
    cible = (env_file if env_file is not None else Settings.env_file).resolve()

    async def hook(
        entree: HookInput, tool_use_id: str | None, contexte: HookContext
    ) -> HookJSONOutput:
        donnees: dict[str, Any] = dict(entree)
        entrees: dict[str, Any] = donnees.get("tool_input", {})
        outil = donnees.get("tool_name")
        if not _outil_vise_le_env(outil, entrees, base, cible):
            return {}
        # Ni la valeur ni le contenu de la commande : le nom de l'outil suffit.
        _logger.warning("lecture_env_tessera_refusee", extra={"outil": str(outil)})
        return {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": ENV_REFUS,
            }
        }

    return hook
