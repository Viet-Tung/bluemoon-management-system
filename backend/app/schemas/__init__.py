"""Pydantic v2 schemas conforming to OpenAPI specification."""

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RoleResponse,
    TokenPayload,
    UserResponse,
)
from app.schemas.common import Error, ErrorDetail, PageMeta

__all__ = [
    "TokenPayload",
    "RoleResponse",
    "UserResponse",
    "LoginRequest",
    "LoginResponse",
    "Error",
    "ErrorDetail",
    "PageMeta",
]
