"""The environment of a CLI that runs under the dedicated agent account (ADR-083)."""
import os

from tessera.config import settings
from tessera.services.providers.env_sdk import env_du_sous_processus
from tessera.services.providers.noms import ProviderIndisponible
from tessera.services.providers.path_compte import path_du_compte

#: Où le CLI partagé est copié, hors du profil de l'utilisateur (ticket-894).
CLI_PARTAGE = r"C:\ProgramData\Tessera\bin\claude.exe"

#: Les seules clés que l'environnement de l'agent peut porter. Rien ne se copie
#: de celui du backend : Windows transmet sinon `USERPROFILE` de l'appelant.
CLES_AUTORISEES: frozenset[str] = frozenset({
    "SystemRoot", "PATH", "TEMP", "TMP", "USERPROFILE", "HOME", "APPDATA",
    "LOCALAPPDATA", "CLAUDE_CODE_OAUTH_TOKEN", "GH_CONFIG_DIR",
    "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0",
    "GIT_TERMINAL_PROMPT", "CLAUDE_CODE_GIT_BASH_PATH", "PYTHONDONTWRITEBYTECODE",
    "npm_config_cache",
})


def profil_de(compte: str) -> str:
    """Returns the profile folder of ``compte``."""
    return rf"C:\Users\{compte}"


def env_du_profil(compte: str) -> dict[str, str]:
    """The variables that send temporary files and caches to the agent's own profile.

    Partagées par le CLI et les commandes du run (ticket-988) : celles du
    backend visent le profil de l'utilisateur, où le compte ne crée rien.
    `npm_config_cache` passe devant le `npmrc` copié de scoop avec la chaîne
    d'outils, qui vise lui aussi ce profil.
    """
    profil = profil_de(compte)
    local = rf"{profil}\AppData\Local"
    return {
        "TEMP": rf"{local}\Temp",
        "TMP": rf"{local}\Temp",
        "USERPROFILE": profil,
        "HOME": profil,
        "APPDATA": rf"{profil}\AppData\Roaming",
        "LOCALAPPDATA": local,
        "npm_config_cache": rf"{local}\npm-cache",
    }


def _de_base(compte: str) -> dict[str, str]:
    """System variables and the agent's own profile, built from nothing."""
    return {"SystemRoot": os.environ.get("SystemRoot", r"C:\Windows"), **env_du_profil(compte)}


def env_de_l_agent(compte: str, git_bash_path: str | None) -> dict[str, str]:
    """Builds the agent's ``env``; raises ``ProviderIndisponible`` without OAuth token.

    Le mot de passe du compte n'y entre jamais : il ne sert qu'au logon.
    """
    jeton = settings.agent_oauth_token.get_secret_value()
    if not jeton:
        raise ProviderIndisponible("AGENT_OAUTH_TOKEN absent : l'agent ne peut pas s'authentifier")
    env = _de_base(compte)
    env.update(env_du_sous_processus(git_bash_path))
    env["PATH"] = path_du_compte()
    env["CLAUDE_CODE_OAUTH_TOKEN"] = jeton
    # Le filtre retire les noms de secrets vidés par `env_sdk` : ils n'ont rien à y faire.
    return {k: v for k, v in env.items() if k in CLES_AUTORISEES}
