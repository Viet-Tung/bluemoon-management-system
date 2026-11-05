from typing import Any, Dict
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.rbac_middleware import AppAPIException
from app.routers import (
    apartments_router,
    audit_logs_router,
    auth_router,
    fee_types_router,
    households_router,
    roles_router,
    system_router,
    users_router,
)
from app.schemas.common import Error, ErrorDetail

app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =====================================================================
# GLOBAL EXCEPTION HANDLERS (Standardized Error Envelope)
# =====================================================================

@app.exception_handler(AppAPIException)
async def app_api_exception_handler(request: Request, exc: AppAPIException):
    """Handle custom application exceptions conforming to docs/API_CONTRACT.md."""
    error_payload = Error(
        code=exc.code,
        message=exc.message,
        details=[ErrorDetail(**d) if isinstance(d, dict) else d for d in exc.details]
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump()
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Transform Pydantic validation errors into compliant VALIDATION_ERROR response."""
    details = []
    for err in exc.errors():
        field_path = " -> ".join(str(loc) for loc in err.get("loc", []))
        details.append(
            ErrorDetail(
                field=field_path,
                message=err.get("msg", "Dữ liệu không hợp lệ")
            )
        )
    error_payload = Error(
        code="VALIDATION_ERROR",
        message="Dữ liệu đầu vào không hợp lệ.",
        details=details
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content=error_payload.model_dump()
    )


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle standard Starlette / FastAPI HTTPExceptions."""
    code = "HTTP_ERROR"
    if exc.status_code == status.HTTP_401_UNAUTHORIZED:
        code = "UNAUTHENTICATED"
    elif exc.status_code == status.HTTP_403_FORBIDDEN:
        code = "FORBIDDEN"
    elif exc.status_code == status.HTTP_404_NOT_FOUND:
        code = "NOT_FOUND"

    error_payload = Error(
        code=code,
        message=str(exc.detail) if exc.detail else "Lỗi HTTP.",
        details=[]
    )
    return JSONResponse(
        status_code=exc.status_code,
        content=error_payload.model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Catch unhandled errors and prevent leaking internal stacktraces."""
    error_payload = Error(
        code="INTERNAL_SERVER_ERROR",
        message="Đã xảy ra lỗi hệ thống nội bộ.",
        details=[]
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_payload.model_dump()
    )


# =====================================================================
# API ROUTERS
# =====================================================================

app.include_router(auth_router, prefix=f"{settings.API_V1_STR}/auth")
app.include_router(roles_router, prefix=f"{settings.API_V1_STR}/roles")
app.include_router(users_router, prefix=f"{settings.API_V1_STR}/users")
app.include_router(audit_logs_router, prefix=f"{settings.API_V1_STR}/audit-logs")
app.include_router(apartments_router, prefix=f"{settings.API_V1_STR}/apartments")
app.include_router(households_router, prefix=f"{settings.API_V1_STR}/households")
app.include_router(fee_types_router, prefix=f"{settings.API_V1_STR}/fee-types")
app.include_router(fee_types_router, prefix="/fee-types", include_in_schema=False)
app.include_router(system_router, prefix=f"{settings.API_V1_STR}/system")
app.include_router(system_router, prefix="/system", include_in_schema=False)


# =====================================================================
# SPRINT 1 FOUNDATION & HEALTH ROUTES
# =====================================================================

@app.get(f"{settings.API_V1_STR}/health", tags=["System"])
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for container orchestrators and baseline monitoring."""
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": "1.0.0"
    }


# Verification Routes for US-44 Acceptance Criteria (RBAC & IDOR)
from fastapi import Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.rbac_middleware import get_current_user, require_roles, check_household_access
from app.models.user import User

@app.get(f"{settings.API_V1_STR}/test/admin-only", tags=["Test"])
async def test_admin_only_route(current_user: User = Depends(require_roles("ADMIN"))) -> Dict[str, Any]:
    """Test route verifying RBAC Guard functionality."""
    return {
        "message": "Welcome Admin",
        "user_id": current_user.id,
        "role": current_user.role.code
    }

@app.get(f"{settings.API_V1_STR}/test/households/{{household_id}}", tags=["Test"])
async def test_household_idor_route(
    household_id: int,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Test route verifying IDOR prevention (AC-44.2)."""
    check_household_access(household_id=household_id, current_user=current_user, db=db, request=request)
    return {
        "message": "Access granted",
        "household_id": household_id,
        "requested_by": current_user.username
    }
