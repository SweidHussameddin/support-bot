from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """All runtime configuration. Values come from the environment or a .env file."""

    model_config = SettingsConfigDict(env_file=ROOT / ".env", extra="ignore")

    # Model provider. OpenRouter speaks the OpenAI API, so any OpenAI-compatible endpoint works.
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Comma-separated list, tried in order when a model is rate-limited or down.
    openrouter_model: str = (
        "nvidia/nemotron-3-super-120b-a12b:free,google/gemma-4-31b-it:free,google/gemma-4-26b-a4b-it:free"
    )
    llm_temperature: float = 0.1
    llm_max_tokens: int = 600

    # Retrieval
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    chunk_size: int = 900
    chunk_overlap: int = 150
    top_k: int = 5
    min_score: float = 0.015  # fused retrieval score below which we do not even ask the model

    # Paths
    docs_dir: Path = ROOT / "data" / "docs"
    index_dir: Path = ROOT / "data" / "index"
    inbox_file: Path = ROOT / "data" / "inbox" / "handovers.jsonl"

    # Behaviour
    company_name: str = "Nordlicht Haustechnik"
    handover_webhook_url: str = ""
    history_turns: int = 6  # user+assistant messages kept per session
    app_title: str = "support-bot demo"


    @property
    def models(self) -> list[str]:
        return [m.strip() for m in self.openrouter_model.split(",") if m.strip()]


settings = Settings()
