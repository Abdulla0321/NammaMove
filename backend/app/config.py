"""Validated environment configuration; secrets are never rendered in errors."""

from pathlib import Path
from urllib.parse import urlsplit

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)
    app_env: str = "development"
    otp_url: str | None = None
    otp_manifest: Path | None = None
    database_url: SecretStr | None = None
    supabase_url: str | None = None
    supabase_jwt_audience: str = "authenticated"
    simulation_enabled: bool | None = None

    @property
    def allow_simulation(self) -> bool:
        return (
            self.simulation_enabled
            if self.simulation_enabled is not None
            else self.app_env != "production"
        )

    @property
    def issuer(self) -> str | None:
        return self.supabase_url.rstrip("/") + "/auth/v1" if self.supabase_url else None

    @model_validator(mode="after")
    def validate_configuration(self) -> "Settings":
        if self.app_env not in {"development", "test", "production"}:
            raise ValueError("APP_ENV must be development, test or production")
        if self.database_url:
            try:
                url = make_url(self.database_url.get_secret_value())
                valid = url.drivername == "postgresql+psycopg" and bool(url.database)
            except Exception:
                valid = False
            if not valid:
                raise ValueError("DATABASE_URL must use postgresql+psycopg and name a database")
        if bool(self.otp_url) != bool(self.otp_manifest):
            raise ValueError("OTP_URL and OTP_MANIFEST must be configured together")
        if self.otp_url:
            parts = urlsplit(self.otp_url)
            if (
                parts.scheme not in {"http", "https"}
                or parts.hostname not in {"127.0.0.1", "localhost"}
                or parts.username
                or parts.password
                or parts.query
                or parts.fragment
                or parts.path not in {"", "/"}
            ):
                raise ValueError("Phase 03 OTP_URL must be a credential-free loopback origin")
        if self.supabase_url:
            url_parts = urlsplit(self.supabase_url)
            local = self.app_env != "production" and url_parts.hostname in {
                "localhost",
                "127.0.0.1",
            }
            if (
                (url_parts.scheme != "https" and not (local and url_parts.scheme == "http"))
                or not url_parts.hostname
                or url_parts.username
                or url_parts.password
                or url_parts.query
                or url_parts.fragment
                or url_parts.path not in {"", "/"}
            ):
                raise ValueError(
                    "SUPABASE_URL must be an HTTPS project origin (HTTP localhost in development only)"
                )
        if self.app_env == "production" and (not self.database_url or not self.supabase_url):
            raise ValueError("Production requires DATABASE_URL and SUPABASE_URL")
        return self
