"""Configuration management for the Medical Document Verification API."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_title: str = Field(
        default="Medical Document Verification API",
        description="API title displayed in OpenAPI docs"
    )
    api_version: str = Field(default="1.0.0", description="API version")
    api_description: str = Field(
        default="Classification service for medical registration documents",
        description="API description"
    )

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server bind address")
    port: int = Field(default=8000, description="Server port")
    debug: bool = Field(default=False, description="Debug mode")
    reload: bool = Field(default=False, description="Auto-reload on code changes")

    # Upload Limits
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum upload size in megabytes",
        ge=1,
        le=100
    )
    max_image_width: int = Field(
        default=4096,
        description="Maximum image width in pixels",
        ge=100,
        le=10000
    )
    max_image_height: int = Field(
        default=4096,
        description="Maximum image height in pixels",
        ge=100,
        le=10000
    )
    max_image_pixels: int = Field(
        default=16777216,
        description="Maximum total pixels (width * height)",
        ge=10000,
        le=100000000
    )

    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8080",
        description="Comma-separated list of allowed CORS origins"
    )
    cors_credentials: bool = Field(
        default=False,
        description="Allow credentials in CORS requests"
    )

    # Logging
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    log_format: Literal["json", "text"] = Field(
        default="json",
        description="Log output format"
    )

    # Model Configuration
    model_path: str = Field(
        default="models/classifier.pkl",
        description="Path to the trained classifier model"
    )
    model_version: str = Field(
        default="baseline-v1",
        description="Model version identifier"
    )
    confidence_threshold: float = Field(
        default=0.7,
        description="Minimum confidence for classification",
        ge=0.0,
        le=1.0
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @property
    def max_file_size_bytes(self) -> int:
        """Convert max file size from MB to bytes."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins from comma-separated string."""
        return [origin.strip() for origin in self.cors_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance. Called once per application lifecycle."""
    return Settings()
