from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str
    ide_workspace_dir: Path = Path.home() / "vibe-ide-workspace"
    ide_log_level: str = "INFO"
    # Chemin vers agents/prompts/ — à surcharger via IDE_PROMPTS_DIR si le serveur
    # ne tourne pas depuis la racine du repo vibe-ide.
    ide_prompts_dir: Path = Path("agents") / "prompts"


settings = Settings()  # type: ignore[call-arg]
