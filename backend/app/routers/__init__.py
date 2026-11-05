"""FastAPI routers package."""

from app.routers.apartments import router as apartments_router
from app.routers.audit_logs import router as audit_logs_router
from app.routers.auth import router as auth_router
from app.routers.fee_types import router as fee_types_router
from app.routers.households import router as households_router
from app.routers.roles import router as roles_router
from app.routers.system import router as system_router
from app.routers.users import router as users_router

__all__ = [
    "auth_router",
    "roles_router",
    "users_router",
    "audit_logs_router",
    "apartments_router",
    "households_router",
    "fee_types_router",
    "system_router",
]
