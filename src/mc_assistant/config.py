"""Runtime configuration for MC Assistant."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven runtime settings."""

    model_config = SettingsConfigDict(env_prefix="MC_ASSISTANT_", env_file=".env", extra="ignore")

    app_name: str = "mc-assistant"
    log_level: str = "INFO"
    minescript_socket: str = Field(
        default="127.0.0.1:19132",
        description="Address for minescript/game command adapter connection.",
    )
    voice_enabled: bool = True
    telemetry_enabled: bool = True


settings = Settings()
