"""Authentication utilities for MCP Hub dashboard and API key management."""
import os
import jwt
import secrets
from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, Request

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE = timedelta(hours=24)


def get_jwt_secret() -> str:
    return os.environ["JWT_SECRET"]


def create_access_token(email: str) -> str:
    payload = {
        "sub": email,
        "exp": datetime.now(timezone.utc) + ACCESS_TOKEN_EXPIRE,
        "type": "access",
    }
    return jwt.encode(payload, get_jwt_secret(), algorithm=JWT_ALGORITHM)


def verify_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, get_jwt_secret(), algorithms=[JWT_ALGORITHM])
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_token_from_request(request: Request) -> str:
    """Extract JWT from cookie or Authorization header."""
    token = request.cookies.get("access_token")
    if token:
        return token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return ""


async def require_admin(request: Request):
    """Dependency: require valid JWT for dashboard routes."""
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return verify_access_token(token)


def get_api_key_from_request(request: Request) -> str:
    """Extract API key from header or query param."""
    key = request.headers.get("X-API-Key", "")
    if key:
        return key
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return request.query_params.get("api_key", "")


def generate_api_key() -> str:
    """Generate a random API key."""
    return f"mcp_{secrets.token_hex(24)}"
