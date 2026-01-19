from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import httpx
from functools import lru_cache
from typing import Optional
from config import get_settings

settings = get_settings()
security = HTTPBearer(auto_error=False)


@lru_cache()
def get_jwks():
    """Fetch Auth0 JWKS (JSON Web Key Set) for token verification."""
    if not settings.auth0_domain:
        return None
    jwks_url = f"https://{settings.auth0_domain}/.well-known/jwks.json"
    response = httpx.get(jwks_url)
    return response.json()


def get_signing_key(token: str):
    """Get the signing key from JWKS that matches the token's kid."""
    jwks = get_jwks()
    if not jwks:
        return None

    unverified_header = jwt.get_unverified_header(token)

    for key in jwks.get("keys", []):
        if key["kid"] == unverified_header["kid"]:
            return {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"],
            }
    return None


class User:
    def __init__(self, user_id: str, email: Optional[str] = None):
        self.user_id = user_id
        self.email = email


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """
    Get current authenticated user from JWT token.
    Returns None if not authenticated (anonymous user).
    """
    if not credentials:
        return None

    if not settings.auth0_domain:
        return None

    token = credentials.credentials

    try:
        signing_key = get_signing_key(token)
        if not signing_key:
            return None

        payload = jwt.decode(
            token,
            signing_key,
            algorithms=settings.auth0_algorithms,
            audience=settings.auth0_audience,
            issuer=f"https://{settings.auth0_domain}/",
        )

        user_id = payload.get("sub")
        email = payload.get("email")

        if not user_id:
            return None

        return User(user_id=user_id, email=email)

    except JWTError:
        return None


async def require_auth(
    user: Optional[User] = Depends(get_current_user),
) -> User:
    """Require authenticated user. Raises 401 if not authenticated."""
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
