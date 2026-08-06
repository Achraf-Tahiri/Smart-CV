"""Configuration de l'application, chargée depuis l'environnement (.env)."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Paramètres de l'application.

    Les valeurs proviennent des variables d'environnement (ou d'un fichier .env).
    Toutes ont une valeur par défaut, pour que l'API démarre sans configuration
    en développement. Les variables inconnues du .env sont ignorées.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- Application ---
    app_name: str = "New Smart CV"
    app_env: str = "local"  # local | staging | production
    log_level: str = "INFO"  # DEBUG | INFO | WARNING | ERROR
    api_port: int = 8000
    version: str = "0.1.0"

    # --- Base de données (PostgreSQL + asyncpg) ---
    database_url: str = "postgresql+asyncpg://nscv:change-me@localhost:5432/nscv"

    @property
    def is_local(self) -> bool:
        """Vrai en environnement de développement local."""
        return self.app_env.lower() == "local"


# Instance unique, importée partout : `from app.core.config import settings`
settings = Settings()
