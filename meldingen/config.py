import logging
from datetime import timedelta
from pathlib import Path

from pydantic import PostgresDsn
from pydantic_media_type import MediaType
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Settings class to manage configuration variables for the application."""

    model_config = SettingsConfigDict(env_prefix="api_", env_nested_delimiter="__")

    # General settings
    debug: bool = False
    log_level: int = logging.WARNING
    project_name: str = "Meldingen Openbare Ruimte"
    url_prefix: str = "/api"
    default_page_size: int = 50

    # Database settings
    database_dsn: PostgresDsn

    # Authentication
    jwks_url: str
    auth_url: str
    token_url: str

    # CORS
    cors_allow_origins: list[str]
    cors_allow_credentials: bool
    cors_allow_methods: list[str]
    cors_allow_headers: list[str]

    # Token
    token_duration: timedelta  # Uses ISO 8601 standard for durations (https://en.wikipedia.org/wiki/ISO_8601)

    # Storage
    attachment_storage_base_directory: Path
    attachment_allow_media_types: list[MediaType]

    # imgproxy
    imgproxy_key: str
    imgproxy_salt: str
    imgproxy_base_url: str


# Create an instance of the Settings model
settings = Settings()
