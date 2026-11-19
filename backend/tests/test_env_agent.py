"""ticket-988, ticket-1008: the agent account's shared profile, used by the CLI and the run commands."""
from tessera.services.providers.env_agent import CLES_AUTORISEES, PROFIL_AGENT, env_du_profil


def test_profile_variables_point_to_the_shared_profile() -> None:
    env = env_du_profil("tessera-agent")
    base = r"C:\ProgramData\Tessera\profil-agent"
    assert env["TEMP"] == base + r"\AppData\Local\Temp"
    assert env["LOCALAPPDATA"] == base + r"\AppData\Local"
    assert env["npm_config_cache"] == base + r"\npm-cache"
    assert env["UV_CACHE_DIR"] == base + r"\uv\cache"


def test_no_variable_points_under_the_account_profile() -> None:
    for valeur in env_du_profil("tessera-agent").values():
        assert valeur.startswith(PROFIL_AGENT)
        assert "Users" not in valeur


def test_the_cli_keeps_the_npm_cache_of_the_profile() -> None:
    # Le Bash du CLI lance npm : sans cette clé, le npmrc copié de scoop
    # renverrait le cache dans le profil de l'utilisateur.
    assert "npm_config_cache" in CLES_AUTORISEES
    assert "UV_CACHE_DIR" in CLES_AUTORISEES
