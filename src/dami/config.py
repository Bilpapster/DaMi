"""All of DaMi's settings in one place.

Settings come from environment variables. The easiest way to set them is the
`.env` file in the root of the repository (copy `.env.example` to `.env`).
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import dotenv_values

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = Path(__file__).resolve().parent

_SHELL_ENV = set(os.environ)  # variables set in the shell win over .env


def load_env() -> None:
    """(Re)read .env, so that a running program (e.g. the web app) sees changes to the file."""
    for key, value in dotenv_values(REPO_ROOT / ".env").items():
        if key not in _SHELL_ENV and value is not None:
            os.environ[key] = value


load_env()


def _bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _int(name: str) -> int | None:
    value = os.getenv(name)
    return int(value) if value else None


@dataclass(frozen=True)
class Settings:
    # --- The brain (Ollama on Kaggle, reached through ngrok) ---
    ollama_host: str | None = field(default_factory=lambda: os.getenv("OLLAMA_HOST"))
    model_id: str = field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "qwen3.5:9b"))
    temperature: float = field(default_factory=lambda: float(os.getenv("DAMI_TEMPERATURE", "0.7")))
    think: bool = field(default_factory=lambda: _bool("DAMI_THINK", True))
    context_length: int | None = field(default_factory=lambda: _int("DAMI_CONTEXT_LENGTH"))
    keep_alive: str = field(default_factory=lambda: os.getenv("DAMI_KEEP_ALIVE", "30m"))
    request_timeout_s: float = field(default_factory=lambda: float(os.getenv("DAMI_TIMEOUT_S", "300")))

    # --- Files ---
    data_dir: Path = field(default_factory=lambda: Path(os.getenv("DAMI_DATA_DIR", REPO_ROOT / "data")))
    workspace_dir: Path = field(default_factory=lambda: Path(os.getenv("DAMI_WORKSPACE", REPO_ROOT / "workspace")))
    runs_dir: Path = field(default_factory=lambda: Path(os.getenv("DAMI_RUNS_DIR", REPO_ROOT / "runs")))
    prompt_file: Path = field(default_factory=lambda: Path(os.getenv("DAMI_PROMPT_FILE", PACKAGE_DIR / "prompts" / "system.md")))

    # --- Observability (optional: start the stack with `dami obs up`) ---
    victoriametrics_url: str = field(default_factory=lambda: os.getenv("DAMI_VICTORIAMETRICS_URL", "http://127.0.0.1:8428"))
    langfuse_host: str = field(default_factory=lambda: os.getenv("LANGFUSE_HOST", "http://127.0.0.1:3000"))
    langfuse_public_key: str | None = field(default_factory=lambda: os.getenv("LANGFUSE_INIT_PROJECT_PUBLIC_KEY"))
    langfuse_secret_key: str | None = field(default_factory=lambda: os.getenv("LANGFUSE_INIT_PROJECT_SECRET_KEY"))

    # --- Kaggle ---
    kaggle_notebook: str | None = field(default_factory=lambda: os.getenv("KAGGLE_NOTEBOOK"))

    # --- Step 5: the second brain (your partner's Kaggle notebook) ---
    ollama_host_b: str | None = field(default_factory=lambda: os.getenv("OLLAMA_HOST_B"))
    model_id_b: str | None = field(default_factory=lambda: os.getenv("OLLAMA_MODEL_B"))
    partner_notebook: str | None = field(default_factory=lambda: os.getenv("PARTNER_NOTEBOOK"))

    @property
    def plots_dir(self) -> Path:
        return self.workspace_dir / "plots"

    @property
    def results_dir(self) -> Path:
        return self.workspace_dir / "results"


def get_settings() -> Settings:
    load_env()
    return Settings()
