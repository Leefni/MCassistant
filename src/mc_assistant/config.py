"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MC Assistant"
    log_level: str = "INFO"
    minescript_socket: str = "localhost:25575"

    minecraft_adapter: str = "stub"
    locator_backend: str = "stub"
    locator_cubiomes_bin: str | None = None
    locator_minecraft_version: str = "1.20.1"

    seedcracker_log_path: str | None = None

    seedcracker_log_path: str | None = None

    model_config = SettingsConfigDict(env_prefix="MC_ASSISTANT_", env_file=".env", extra="ignore")


settings = Settings()
