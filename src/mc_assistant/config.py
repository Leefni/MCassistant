"""Application settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "MC Assistant"
    log_level: str = "INFO"

    minecraft_adapter: str = "echo"  # echo|minescript
    minescript_command_prefix: str = "/"

    locator_backend: str = "stub"  # stub|demo|cubiomes
    locator_cubiomes_bin: str | None = None
    locator_minecraft_version: str = "1.20.1"

    seedcracker_log_path: str | None = None
    seedcracker_start_command: str = "seedcracker finder"
    minescript_socket: str = "localhost:25575"

    model_config = SettingsConfigDict(env_prefix="MC_ASSISTANT_", env_file=".env", extra="ignore")


settings = Settings()
