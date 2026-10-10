from pathlib import Path
from typing import Literal, Optional
import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseModel):
    name: str = "legacy-to-lakehouse-copilot"
    max_retries: int = 3
    epsilon_tolerance: float = 1e-6


class SecurityConfig(BaseModel):
    pii_hash_salt: str = "pepper_sec_v1_demo"


class DatabaseConfig(BaseModel):
    legacy_path: str = "data/legacy/legacy_warehouse.duckdb"
    target_path: str = "data/medallion/lakehouse_medallion.duckdb"
    checkpoint_path: str = "checkpoints.db"


class LLMConfig(BaseModel):
    provider: Literal["mock", "gemini", "openai", "ollama"] = "mock"
    model_name: str = "mock"
    temperature: float = 0.1
    api_key: Optional[str] = None
    ollama_base_url: str = "http://localhost:11434"


class Settings(BaseSettings):
    app: AppConfig = Field(default_factory=AppConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    @classmethod
    def load(cls, config_path: str = "configs/settings.yaml") -> "Settings":
        import os
        from dotenv import load_dotenv

        load_dotenv(override=True)
        cfg_file = Path(config_path)
        data = {}
        if cfg_file.exists():
            with open(cfg_file, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}

        # Allow .env overrides
        if "llm" not in data:
            data["llm"] = {}
        if "database" not in data:
            data["database"] = {}
        if "security" not in data:
            data["security"] = {}

        if os.getenv("LLM_PROVIDER"):
            data["llm"]["provider"] = os.getenv("LLM_PROVIDER")
        if os.getenv("OLLAMA_MODEL"):
            data["llm"]["model_name"] = os.getenv("OLLAMA_MODEL")
        if os.getenv("OLLAMA_BASE_URL"):
            data["llm"]["ollama_base_url"] = os.getenv("OLLAMA_BASE_URL")

        if os.getenv("PII_HASH_SALT"):
            data["security"]["pii_hash_salt"] = os.getenv("PII_HASH_SALT")

        if os.getenv("LEGACY_DB_PATH"):
            data["database"]["legacy_path"] = os.getenv("LEGACY_DB_PATH")
        if os.getenv("TARGET_DB_PATH"):
            data["database"]["target_path"] = os.getenv("TARGET_DB_PATH")
        if os.getenv("CHECKPOINT_DB_PATH"):
            data["database"]["checkpoint_path"] = os.getenv("CHECKPOINT_DB_PATH")

        return cls(**data)


settings = Settings.load()
