from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Optionnel : vide lorsque le provider est `agent_sdk` (auth par abonnement).
    anthropic_api_key: str = ""
    # Provider LLM par défaut : "agent_sdk" (abonnement) ou "anthropic_api" (crédits).
    llm_provider: str = "agent_sdk"
    # Garde-fous ClaudeAgentSDKProvider — bornent une boucle d'agent qui dérape.
    # max_turns borne le nombre d'allers-retours outil ; max_budget_usd borne
    # la dépense réelle d'un seul appel agent (le garde-fou qui protège le
    # quota de l'abonnement). Voir memory/decisions.md pour le choix de 1.0 USD.
    llm_max_turns: int = 30
    llm_max_budget_usd: float = 1.0
    ide_workspace_dir: Path = Path.home() / "vibe-ide-workspace"
    ide_log_level: str = "INFO"
    # Chemin vers agents/prompts/ — à surcharger via IDE_PROMPTS_DIR si le serveur
    # ne tourne pas depuis la racine du repo vibe-ide.
    ide_prompts_dir: Path = Path("agents") / "prompts"
    github_token: str = ""
    github_repo: str = ""  # format "owner/repo"
    # Cible par défaut des PR de ticket. Le flux est
    # ticket-XXX -> develop -> main : une PR de ticket ne vise jamais
    # `main` directement, sinon rien ne teste les tickets fusionnés
    # entre eux avant qu'ils n'atteignent l'état publiable.
    github_base_branch: str = "develop"
    ide_db_path: Path = Path("vibe_ide.db")
    static_token: str = ""  # if set, all API requests require Authorization: Bearer <token>


settings = Settings()
