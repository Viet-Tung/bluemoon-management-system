"""FastAPI routers package."""

from app.routers.auth import router as auth_router
from app.routers.roles import router as roles_router
from app.routers.users import router as users_router

__all__ = ["auth_router", "roles_router", "users_router"]
