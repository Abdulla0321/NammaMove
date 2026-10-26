"""Explicitly configured provider downloads; no scraping or built-in live source."""

from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

from .validation import MAX_ZIP_BYTES


class ProviderUnavailable(ValueError):
    pass


@dataclass(frozen=True)
class ProviderAdapter:
    provider: str
    url: str | None = None

    def fetch(self, client: httpx.Client) -> bytes:
        if self.provider not in {"bmtc", "bmrcl"} or self.url is None:
            raise ProviderUnavailable("provider_not_configured")
        parts = urlsplit(self.url)
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.query
            or parts.fragment
        ):
            raise ProviderUnavailable("invalid_public_provider_url")
        try:
            with client.stream("GET", self.url, follow_redirects=False, timeout=30) as response:
                if response.status_code != 200:
                    raise ProviderUnavailable("provider_http_failure")
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > MAX_ZIP_BYTES:
                        raise ProviderUnavailable("provider_payload_too_large")
                return bytes(data)
        except httpx.HTTPError:
            raise ProviderUnavailable("provider_unavailable") from None
