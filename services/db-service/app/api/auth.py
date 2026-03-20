import hmac

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import settings


api_key_header = APIKeyHeader(name=settings.api_key_header_name, auto_error=False)


def require_api_key(provided_api_key: str | None = Security(api_key_header)) -> None:
    """Validates API key passed in request headers."""
    if not provided_api_key:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key")

    if not hmac.compare_digest(provided_api_key, settings.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
