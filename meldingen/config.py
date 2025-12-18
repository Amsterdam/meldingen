import logging
import os
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
    content_size_limit: int = 1024 * 1024 * 20  # 20MB

    # Database settings
    database_dsn: PostgresDsn
    test_database_dsn: PostgresDsn = PostgresDsn("postgresql+asyncpg://meldingen:postgres@database:5432/meldingen-test")

    # Authentication
    jwks_url: str
    auth_url: str
    token_url: str
    issuer_url: str
    auth_audience: str
    auth_scopes: list[str]
    auth_client_id: str
    auth_identifier_field: str

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

    # azure storage blobs
    azure_storage_container: str
    azure_storage_connection_string: str
    azure_malware_scanner_tries: int = 5
    azure_malware_scanner_sleep_time: float = 1.0
    azure_malware_scanner_enabled: bool = False

    # thumbnail (default for meldingen-frontend)
    thumbnail_width: int = 544
    thumbnail_height: int = 306

    # Phone number format
    phone_number_format: str = "E164"  # International ITU standard
    phone_number_default_region_code: str = "NL"

    # OpenTelemetry
    opentelemetry_service_name: str = "meldingen"

    # Address API
    address_api_resolver_retries: int = 5

    # Mail
    mail_service_api_base_url: str = "http://mail-service:8003"
    mail_default_sender: str = "meldingen@example.com"
    mail_melding_confirmation_title: str = "Uw melding"
    mail_melding_confirmation_preview_text: str = "Uw melding: {}"
    mail_melding_confirmation_body_text: str = """U heeft ons het volgende laten weten:

*{}*

### Wat doen we met uw melding?
Wij gaan aan het werk met uw melding. U hoort zo snel mogelijk wat wij hebben gedaan. Als de situatie gevaarlijk is
gaan wij direct aan het werk.

### Meer weten?
Heeft u nog een vraag over uw melding? Bel met het telefoonnummer [14 020](tel:14020), maandag tot en met vrijdag
van 08.00 tot 18.00. Geef dan ook het nummer van uw melding door: {}.

Met vriendelijke groet,

Gemeente Amsterdam

*Dit bericht is automatisch gemaakt met de informatie uit uw melding.*"""
    mail_melding_confirmation_subject: str = "Uw melding {}: melding ontvangen"

    mail_melding_completed_title: str = "Uw melding {}: melding afgehandeld"
    mail_melding_completed_preview_text: str = "Uw melding: {}"
    mail_melding_completed_subject: str = "Uw melding: {} afgehandeld"

    # LLM
    llm_enabled: bool = False  # If True enables the OpenAIClassifierAdapter instead of the DummyClassifierAdapter
    llm_base_url: str = os.getenv(
        "LLM_URL", ""
    )  # LLM_URL is injected by docker compose and specifies the OpenAI compatible API endpoint base URL
    llm_model_identifier: str = os.getenv(
        "LLM_MODEL", ""
    )  # LLM is injected by docker compose and specifies the model identifier


# Create an instance of the Settings model
settings = Settings()
