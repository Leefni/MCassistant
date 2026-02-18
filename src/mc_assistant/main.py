"""CLI startup entrypoint for MC Assistant."""

import typer
from rich import print

from mc_assistant.config import settings

app = typer.Typer(help="MC Assistant service entrypoint")


@app.command()
def start() -> None:
    """Start the assistant runtime."""
    print(f"[green]{settings.app_name}[/green] starting with log level {settings.log_level}")
    print(f"Minescript adapter endpoint: {settings.minescript_socket}")


if __name__ == "__main__":
    app()
