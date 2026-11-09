"""The environment of a CLI that runs under the dedicated agent account (ADR-083)."""
import os

from tessera.config import settings
from tessera.services.providers.env_sdk import env_du_sous_processus
from tessera.services.providers.noms import ProviderIndisponible

#: Où le CLI partagé est copié, hors du profil de l'utilisateur (ticket-894).
CLI_PARTAGE = r"C:\ProgramData\Tessera\bin\claude.exe"

#: Les seules clés que l'environnement de l'agent peut porter. Rien ne se copie
#: de celui du backend : Windows transmet sinon `USERPROFILE` de l'appelant.
CLES_AUTORISEES: frozenset[str] = frozenset({
    "SystemRoot", "PATH", "TEMP", "TMP", "USERPROFILE", "HOME", "APPDATA",
    "LOCALAPPDATA", "CLAUDE_CODE_OAUTH_TOKEN", "GH_CONFIG_DIR",
    "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0",
    "GIT_TERMINAL_PROMPT", "CLAUDE_CODE_GIT_BASH_PATH",
})


def profil_de(compte: str) -> str:
    """Returns the profile folder of ``compte``."""
    return rf"C:\Users\{compte}"


def _de_base(compte: str) -> dict[str, str]:
    """System variables and the agent's own profile, built from nothing."""
    racine = os.environ.get("SystemRoot", r"C:\Windows")
    profil = profil_de(compte)
    return {
        "SystemRoot": racine,
        "PATH": rf"{racine}\System32;{racine}",
        "TEMP": rf"{profil}\AppData\Local\Temp",
        "TMP": rf"{profil}\AppData\Local\Temp",
        "USERPROFILE": profil,
        "HOME": profil,
        "APPDATA": rf"{profil}\AppData\Roaming",
        "LOCALAPPDATA": rf"{profil}\AppData\Local",
    }


def env_de_l_agent(compte: str, git_bash_path: str | None) -> dict[str, str]:
    """Builds the agent's ``env``; raises ``ProviderIndisponible`` without OAuth token.

    Le mot de passe du compte n'y entre jamais : il ne sert qu'au logon.
    """
    jeton = settings.agent_oauth_token.get_secret_value()
    if not jeton:
        raise ProviderIndisponible("AGENT_OAUTH_TOKEN absent : l'agent ne peut pas s'authentifier")
    env = _de_base(compte)
    env.update(env_du_sous_processus(git_bash_path))
    env["CLAUDE_CODE_OAUTH_TOKEN"] = jeton
    # Le filtre retire les noms de secrets vidés par `env_sdk` : ils n'ont rien à y faire.
    return {k: v for k, v in env.items() if k in CLES_AUTORISEES}
