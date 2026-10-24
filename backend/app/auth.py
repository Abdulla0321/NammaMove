"""Supabase asymmetric JWT validation. User-editable metadata never grants roles."""

from dataclasses import dataclass
from typing import Annotated, Literal, cast
from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError

from .config import Settings

Role = Literal["commuter", "moderator", "admin"]
bearer = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class Principal:
    id: UUID
    role: Role


class TokenVerifier:
    def __init__(self, settings: Settings) -> None:
        self.issuer = settings.issuer
        self.audience = settings.supabase_jwt_audience
        self.jwks = (
            PyJWKClient(
                self.issuer + "/.well-known/jwks.json", cache_keys=False, lifespan=60, timeout=5
            )
            if self.issuer
            else None
        )

    def verify(self, token: str) -> Principal:
        if not self.jwks:
            raise HTTPException(503, "Authentication is not configured")
        try:
            header = jwt.get_unverified_header(token)
            if header.get("alg") not in {"RS256", "ES256"} or not isinstance(
                header.get("kid"), str
            ):
                raise ValueError("Unsupported signing header")
            key = self.jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256", "ES256"],
                issuer=self.issuer,
                audience=self.audience,
                options={"require": ["exp", "iat", "sub", "iss", "aud", "role"]},
            )
            if claims["role"] != "authenticated" or claims.get("is_anonymous", False):
                raise ValueError("Only authenticated user access tokens accepted")
            metadata = claims.get("app_metadata", {})
            role = (
                metadata.get("nammamove_role", "commuter")
                if isinstance(metadata, dict)
                else "commuter"
            )
            if role not in {"commuter", "moderator", "admin"}:
                raise ValueError("Invalid application role")
            return Principal(UUID(claims["sub"]), cast(Role, role))
        except PyJWKClientConnectionError:
            raise HTTPException(503, "Authentication provider unavailable") from None
        except (jwt.PyJWTError, ValueError, TypeError, KeyError):
            raise HTTPException(
                401, "Invalid or expired access token", headers={"WWW-Authenticate": "Bearer"}
            ) from None


def current_principal(
    request: Request, credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)]
) -> Principal:
    if credentials is None or len(credentials.credentials) > 8192:
        raise HTTPException(
            401, "Bearer access token required", headers={"WWW-Authenticate": "Bearer"}
        )
    verifier: TokenVerifier = request.app.state.verifier
    return verifier.verify(credentials.credentials)


Identity = Annotated[Principal, Depends(current_principal)]


def moderator(principal: Identity) -> Principal:
    if principal.role not in {"moderator", "admin"}:
        raise HTTPException(403, "Moderator role required")
    return principal


def admin(principal: Identity) -> Principal:
    if principal.role != "admin":
        raise HTTPException(403, "Admin role required")
    return principal
