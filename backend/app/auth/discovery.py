import asyncio
import logging
from urllib.parse import urlsplit

import httpx

from app.auth.config import AuthSettings

log = logging.getLogger("app.auth")

REFRESH_INTERVAL = 3600
RETRY_INTERVAL = 30


class DiscoveryError(Exception):
    """The server's metadata cannot be used."""


class DiscoveryUnavailable(DiscoveryError):
    """The server could not be reached (or answered 5xx): worth retrying."""


def candidate_urls(issuer: str) -> list[str]:
    """RFC 8414 puts `/.well-known/…` between the host and the issuer's path;
    OpenID Connect Discovery appends it after the path."""
    parts = urlsplit(issuer)
    origin = f"{parts.scheme}://{parts.netloc}"
    path = parts.path.rstrip("/")
    return [
        f"{origin}/.well-known/oauth-authorization-server{path}",
        f"{issuer.rstrip('/')}/.well-known/openid-configuration",
    ]


def validate(metadata: dict, settings: AuthSettings) -> None:
    """RFC 8414 §3.3 and RFC 9700 checks. Raises DiscoveryError."""
    # Strict string equality: a trailing slash is a different issuer.
    if metadata.get("issuer") != settings.oauth_issuer:
        raise DiscoveryError(
            f"issuer mismatch: metadata says {metadata.get('issuer')!r}, "
            f"OAUTH_ISSUER is {settings.oauth_issuer!r}"
        )
    if "S256" not in metadata.get("code_challenge_methods_supported", []):
        raise DiscoveryError("the server does not advertise PKCE S256")
    for key in ("authorization_endpoint", "token_endpoint"):
        url = metadata.get(key)
        if not url:
            raise DiscoveryError(f"{key} is missing from the metadata")
        if not settings.dev and urlsplit(url).scheme != "https":
            raise DiscoveryError(f"{key} must be https (got {url!r})")
    if not metadata.get("jwks_uri") and not settings.oauth_logout_token_secret:
        raise DiscoveryError(
            "no jwks_uri in the metadata: set OAUTH_LOGOUT_TOKEN_SECRET to verify logout tokens"
        )


class Discovery:
    """Metadata of the OAuth server, cached in memory and refreshed hourly."""

    def __init__(self, settings: AuthSettings, http: httpx.AsyncClient):
        self.settings = settings
        self.http = http
        self.metadata: dict | None = None

    @property
    def ready(self) -> bool:
        return self.metadata is not None

    def get(self, key: str, default=None):
        return (self.metadata or {}).get(key, default)

    async def fetch(self) -> dict:
        last: Exception | None = None
        for url in candidate_urls(self.settings.oauth_issuer):
            try:
                response = await self.http.get(url, auth=None)
            except httpx.HTTPError as exc:
                raise DiscoveryUnavailable(f"{url}: {exc}") from exc
            if response.status_code == 404:
                last = DiscoveryError(f"{url}: 404")
                continue
            if response.status_code >= 500:
                raise DiscoveryUnavailable(f"{url}: HTTP {response.status_code}")
            if response.status_code != 200:
                raise DiscoveryError(f"{url}: HTTP {response.status_code}")
            try:
                metadata = response.json()
            except ValueError as exc:
                raise DiscoveryError(f"{url}: not JSON") from exc
            if not isinstance(metadata, dict):
                raise DiscoveryError(f"{url}: unexpected document")
            return metadata
        raise last or DiscoveryError("no discovery document found")

    async def load(self) -> None:
        metadata = await self.fetch()
        validate(metadata, self.settings)
        self.metadata = metadata

    async def load_with_retry(self, attempts: int = 5, base_delay: float = 1.0) -> None:
        """Backoff on unreachable server only; an invalid document fails at once."""
        for attempt in range(attempts):
            try:
                await self.load()
                return
            except DiscoveryUnavailable as exc:
                if attempt == attempts - 1:
                    raise
                delay = base_delay * 2**attempt
                log.warning("OAuth discovery unavailable (%s), retrying in %.0fs", exc, delay)
                await asyncio.sleep(delay)

    async def keep_fresh(self) -> None:
        """Background task: retries until the first success, then refreshes
        hourly. A failed refresh keeps the previous metadata."""
        while True:
            await asyncio.sleep(REFRESH_INTERVAL if self.ready else RETRY_INTERVAL)
            try:
                await self.load()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                log.warning("OAuth discovery refresh failed, keeping previous metadata: %s", exc)
