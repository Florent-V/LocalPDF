from typing import Literal
from urllib.parse import urlsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AuthSettings(BaseSettings):
    """OAuth client configuration. The OAuth server is described by the issuer
    alone: every endpoint is read from its discovery document."""

    model_config = SettingsConfigDict(extra="ignore")

    oauth_issuer: str
    oauth_client_id: str
    oauth_client_secret: str
    oauth_scopes: str = "profile email"
    public_origin: str
    session_db_path: str = "/data/sessions.db"
    session_idle_ttl: int = 8 * 3600
    session_absolute_ttl: int = 7 * 86400
    session_revalidate_interval: int = 15 * 60
    cookie_secure: bool = True
    # Plain-HTTP dev only: browsers share cookies across localhost ports, so each app needs its own name.
    session_cookie_name: str = ""
    app_env: Literal["prod", "dev"] = "prod"
    # Only for a server that signs its logout tokens in HS256 and publishes no jwks_uri.
    oauth_logout_token_secret: str = ""

    @model_validator(mode="after")
    def _check(self):
        for name in ("oauth_issuer", "oauth_client_id", "oauth_client_secret", "public_origin"):
            if not getattr(self, name).strip():
                raise ValueError(f"{name.upper()} is required")
        if self.cookie_secure is False and self.app_env == "prod":
            raise ValueError("COOKIE_SECURE=false is only allowed with APP_ENV=dev")
        parts = urlsplit(self.public_origin)
        if parts.scheme not in ("http", "https") or not parts.netloc or parts.path.strip("/"):
            raise ValueError("PUBLIC_ORIGIN must be an origin such as https://pdf.example.com")
        self.public_origin = f"{parts.scheme}://{parts.netloc}"
        return self

    @property
    def dev(self) -> bool:
        return self.app_env == "dev"

    @property
    def redirect_uri(self) -> str:
        return f"{self.public_origin}/auth/callback"

    @property
    def cookie_name(self) -> str:
        # The __Host- prefix makes browsers refuse a cookie that is not Secure,
        # host-only and Path=/, which also blocks a sibling subdomain from setting it.
        return "__Host-session" if self.cookie_secure else (self.session_cookie_name or "session")
