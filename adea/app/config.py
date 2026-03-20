"""Application configuration placeholders."""

import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")


class Settings(BaseSettings):
    """Runtime configuration for the ADEA application."""

    app_name: str = "ADEA"
    environment: str = "development"
    debug: bool = False
    database_url: str = Field(default="duckdb:///adea.db")
    groq_api_key: str | None = Field(default=GROQ_API_KEY)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("debug", mode="before")
    @classmethod
    def coerce_debug_flag(cls, value: object) -> object:
        """Normalize loose environment values for the debug flag."""

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "no"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "yes"}:
                return True

        return value


settings = Settings()
