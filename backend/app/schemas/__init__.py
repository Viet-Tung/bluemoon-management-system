"""Pydantic v2 schemas conforming to OpenAPI specification."""

from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RoleResponse,
    TokenPayload,
    UserResponse,
)
from app.schemas.common import Error, ErrorDetail, PageMeta
from app.schemas.user import (
    TempPassword,
    UserCreate,
    UserPage,
    UserRoleUpdate,
    UserUpdate,
    UserWithTempPassword,
)

__all__ = [
    "TokenPayload",
    "RoleResponse",
    "UserResponse",
    "LoginRequest",
    "LoginResponse",
    "ChangePasswordRequest",
    "Error",
    "ErrorDetail",
    "PageMeta",
    "UserCreate",
    "UserUpdate",
    "UserWithTempPassword",
    "TempPassword",
    "UserPage",
    "UserRoleUpdate",
]
