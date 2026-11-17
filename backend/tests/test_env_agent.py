"""ticket-988: the agent account's own profile, shared by the CLI and the run commands."""
from tessera.services.providers.env_agent import CLES_AUTORISEES, env_du_profil


def test_profile_variables_point_to_the_account_profile() -> None:
    env = env_du_profil("tessera-agent")
    assert env["TEMP"] == r"C:\Users\tessera-agent\AppData\Local\Temp"
    assert env["LOCALAPPDATA"] == r"C:\Users\tessera-agent\AppData\Local"
    assert env["npm_config_cache"] == r"C:\Users\tessera-agent\AppData\Local\npm-cache"


def test_the_cli_keeps_the_npm_cache_of_the_profile() -> None:
    # Le Bash du CLI lance npm : sans cette clé, le npmrc copié de scoop
    # renverrait le cache dans le profil de l'utilisateur.
    assert "npm_config_cache" in CLES_AUTORISEES
