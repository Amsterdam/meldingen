import logging

from pydantic import HttpUrl, PostgresDsn
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
    cors_allow_origins: list[HttpUrl]
    cors_allow_credentials: bool
    cors_allow_methods: list[str]
    cors_allow_headers: list[str]


# Create an instance of the Settings model
settings = Settings()
