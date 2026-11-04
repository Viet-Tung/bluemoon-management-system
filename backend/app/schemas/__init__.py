"""Pydantic v2 schemas conforming to OpenAPI specification."""

from app.schemas.apartment import (
    Apartment,
    ApartmentBase,
    ApartmentCreate,
    ApartmentPage,
    ApartmentUpdate,
)
from app.schemas.audit_log import AuditLogPage, AuditLogResponse
from app.schemas.auth import (
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RoleResponse,
    TokenPayload,
    UserResponse,
)
from app.schemas.common import Error, ErrorDetail, PageMeta
from app.schemas.household import (
    Household,
    HouseholdChangeHead,
    HouseholdCreate,
    HouseholdCreated,
    HouseholdDeactivate,
    HouseholdPage,
    HouseholdUpdate,
    ResidentAccount,
    ResidentCreate,
)
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
    "AuditLogResponse",
    "AuditLogPage",
    "ApartmentBase",
    "ApartmentCreate",
    "ApartmentUpdate",
    "Apartment",
    "ApartmentPage",
    "ResidentAccount",
    "ResidentCreate",
    "HouseholdCreate",
    "HouseholdUpdate",
    "HouseholdDeactivate",
    "HouseholdChangeHead",
    "Household",
    "HouseholdCreated",
    "HouseholdPage",
]
